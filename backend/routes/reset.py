from flask import Blueprint, request, session, jsonify, render_template, current_app
from datetime import datetime, timedelta
from services.reset_service import ResetService, RESET_SESSION_MINUTES

reset_bp = Blueprint('reset', __name__)


def _reset_expired():
    started = session.get('reset_started_at')
    if not started:
        return True
    try:
        return datetime.now() - datetime.fromisoformat(started) > timedelta(minutes=RESET_SESSION_MINUTES)
    except (ValueError, TypeError):
        return True


def _clear_reset():
    for k in ('reset_user_dn', 'reset_phone', 'reset_email', 'reset_started_at', 'reset_authorized'):
        session.pop(k, None)


def _ok(message, step=None, demo_code=None):
    payload = {'success': True, 'message': message, 'step': step}
    if demo_code is not None:
        payload['demo_code'] = demo_code
    return jsonify(payload)


def _fail(message, step=1):
    return jsonify({'success': False, 'message': message, 'step': step})


def _audit(action, target_user=None, details=None):
    """审计日志（失败/成功均记），失败不影响主流程。IP 由 log_operation 自动取。"""
    try:
        from utils.logger import log_operation
        log_operation(action, target_user=target_user, details=details)
    except Exception:
        pass


@reset_bp.route('/reset')
def reset_page():
    return render_template('reset.html')


@reset_bp.route('/reset/verify-identity', methods=['POST'])
def verify_identity():
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    phone = data.get('phone')
    _clear_reset()
    if not email or not phone:
        return _fail('请输入邮箱和手机号', 1), 400

    svc = ResetService()

    # IP 锁定检查（防枚举：同一 IP 连续失败超限则锁 30 分钟）
    allowed, lock_msg = svc.check_ip_locked(request.remote_addr)
    if not allowed:
        return _fail(lock_msg or '尝试次数过多，请稍后再试', 1), 429

    matched, info = svc.find_user_by_email_phone(email, phone)
    if matched:
        session['reset_user_dn'] = info['user_dn']
        session['reset_phone'] = info.get('mobile', phone)
        session['reset_email'] = info.get('mail', email)
        session['reset_started_at'] = datetime.now().isoformat()
        session.pop('reset_authorized', None)
        svc.reset_ip_fails(request.remote_addr)
        ok, _ = svc.issue_sms_code(info['user_dn'], info.get('mobile', phone),
                                   email=session.get('reset_email'), ip=request.remote_addr)
        if not ok:
            _audit('sms_send_failed', target_user=session.get('reset_email'), details='验证码发送失败')
            return _fail('验证码发送失败，请稍后重试', 1), 400
        _audit('reset_identity_ok', target_user=session.get('reset_email'), details='身份校验通过，已发码')
        demo_code = None
        if current_app.config.get('DEMO_MODE'):
            from services.reset_service import _DEMO_CODES
            demo_code = _DEMO_CODES.get(session.get('reset_phone'))
        return _ok('验证码已发送至您预留的手机', 3, demo_code=demo_code)
    # 不匹配：记录失败 + 明确拒绝，不进入下一步
    svc.record_identity_fail(request.remote_addr)
    _audit('reset_identity_mismatch', target_user=email, details='邮箱+手机校验未通过')
    return _fail('邮箱或手机号与域控登记信息不匹配，请检查后重试', 1), 400


@reset_bp.route('/reset/send-code', methods=['POST'])
def send_code():
    if 'reset_user_dn' not in session or _reset_expired():
        _clear_reset()
        return _fail('会话已过期，请重新开始', 1), 400
    svc = ResetService()
    ok, msg = svc.issue_sms_code(session['reset_user_dn'], session.get('reset_phone'),
                                 email=session.get('reset_email'), ip=request.remote_addr)
    if not ok:
        return _fail(msg or '请稍候再试', 3), 429
    return _ok('验证码已重新发送', 3)


@reset_bp.route('/reset/verify-code', methods=['POST'])
def verify_code():
    if 'reset_user_dn' not in session or _reset_expired():
        _clear_reset()
        return _fail('会话已过期，请重新开始', 1), 400
    data = request.get_json(silent=True) or {}
    code = data.get('code')
    if not code:
        return _fail('请输入验证码', 3), 400
    svc = ResetService()
    ok, msg = svc.verify_sms_code(session.get('reset_phone'), code)
    if not ok:
        _audit('reset_code_failed', target_user=session.get('reset_email'), details=msg)
        return _fail(msg, 3), 400
    session['reset_authorized'] = True
    return _ok('验证通过', 4)


@reset_bp.route('/reset/do-reset', methods=['POST'])
def do_reset():
    if not session.get('reset_authorized') or _reset_expired():
        _clear_reset()
        return _fail('请先完成身份验证', 1), 400
    data = request.get_json(silent=True) or {}
    new_password = data.get('new_password')
    confirm = data.get('confirm_password')
    if new_password != confirm:
        return _fail('两次输入的新密码不一致', 4), 400

    svc = ResetService()
    ok, msg = svc.perform_reset(session['reset_user_dn'], new_password)
    if not ok:
        _audit('password_reset_failed', target_user=session.get('reset_email'), details=msg or '重置失败')
        return _fail(msg or '重置失败，请联系管理员', 4), 400

    # 审计 + 通知短信（失败不影响主流程）
    try:
        from utils.logger import log_operation
        phone = session.get('reset_phone', '')
        masked = phone[:3] + '****' + phone[-4:] if len(phone) >= 7 else phone
        log_operation('password_reset',
                      target_user=session.get('reset_email'),
                      details='自助重置成功，手机 %s' % masked)
    except Exception:
        pass
    try:
        from models.models import SmsConfig
        if SmsConfig.query.filter_by(is_active=True).first():
            svc.sms.send_verification_code(session.get('reset_phone'),
                                           '您的域控密码已重置，若非本人操作请立即联系管理员')
    except Exception:
        pass

    _clear_reset()
    return _ok('密码重置成功', 5)
