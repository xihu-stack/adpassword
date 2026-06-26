"""忘记密码自助重置核心服务。通过注入 ldap/sms 适配器实现可测试性。"""
from datetime import datetime, timedelta
import bcrypt
import secrets
import re

from flask import current_app

from models.models import db, SmsVerificationCode, SmsRateLimit, SystemSetting, Domain
from services import secret_crypto

# 限流参数
PHONE_COOLDOWN_SECONDS = 60
HOURLY_LIMIT_PHONE = 5
HOURLY_LIMIT_EMAIL = 5
HOURLY_LIMIT_IP = 20
CODE_TTL_MINUTES = 5
MAX_FAIL_COUNT = 5
RESET_SESSION_MINUTES = 10
IDENTITY_FAIL_LIMIT = 10       # 同一 IP 身份校验连续失败上限
IDENTITY_LOCK_MINUTES = 30     # 超限后锁定时长（分钟）

# 仅 DEMO_MODE 使用：缓存最近一次"发送"的验证码，供演示页面回显（生产不触发）
_DEMO_CODES = {}


class _DefaultLdapAdapter:
    def lookup_user_by_email(self, domain, email):
        if current_app.config.get('DEMO_MODE'):
            # 演示模式：返回一个固定手机号 13800000000 的假用户（不连真实 AD）
            return {
                'user_dn': 'CN=DemoUser,DC=demo,DC=com',
                'mail': (email or '').strip().lower(),
                'mobile': '13800000000',
                'sam_account_name': 'demouser',
                'member_of': [],
                'disabled': False,
            }
        from services.ldap_service import LdapService
        return LdapService.lookup_user_by_email(domain, email)

    def admin_set_password_by_dn(self, domain, user_dn, new_password):
        if current_app.config.get('DEMO_MODE'):
            return True, 'OK (demo)'
        from services.ldap_service import LdapService
        return LdapService.admin_set_password_by_dn(domain, user_dn, new_password)


class _DefaultSmsAdapter:
    def send_verification_code(self, phone, code):
        if current_app.config.get('DEMO_MODE'):
            # 演示模式：不调用阿里云，把验证码打到服务端控制台并缓存供页面回显
            _DEMO_CODES[phone] = code
            print('\n>>> [DEMO] 验证码已"发送"至 %s：%s <<<\n' % (phone, code))
            return True, 'OK (demo)'
        from services.sms_service import SmsService
        from models.models import SmsConfig
        cfg = SmsConfig.query.filter_by(is_active=True).first()
        if not cfg:
            return False, '短信服务未配置'
        return SmsService(cfg).send_verification_code(phone, code)


class ResetService:
    def __init__(self, ldap_adapter=None, sms_adapter=None):
        self.ldap = ldap_adapter or _DefaultLdapAdapter()
        self.sms = sms_adapter or _DefaultSmsAdapter()

    # ---------- 限流（并发安全） ----------
    def _check_cooldown(self, phone):
        """60s 手机号冷却：只读，按 purpose=reset 查最近一条验证码。"""
        now = datetime.utcnow()
        latest = SmsVerificationCode.query.filter_by(phone=phone, purpose='reset').order_by(
            SmsVerificationCode.created_at.desc()).first()
        if latest and latest.created_at and now - latest.created_at < timedelta(seconds=PHONE_COOLDOWN_SECONDS):
            return False, '请稍候再试'
        return True, None

    def _reserve_quota(self, phone, email, ip):
        """原子预留发送额度：PG 行锁(with_for_update)下检查+累加，全成功或全回滚。
        SQLite 测试环境为单线程，with_for_update 被忽略，功能等价。"""
        now = datetime.utcnow()
        keys = (('phone', phone, HOURLY_LIMIT_PHONE),
                ('email', email, HOURLY_LIMIT_EMAIL),
                ('ip', ip, HOURLY_LIMIT_IP))
        for key_type, key_value, cap in keys:
            if not key_value:
                continue
            rl = SmsRateLimit.query.filter_by(
                key_type=key_type, key_value=key_value).with_for_update().first()
            if rl is None:
                rl = SmsRateLimit(key_type=key_type, key_value=key_value,
                                  sent_count=0, window_start=now)
                db.session.add(rl)
                db.session.flush()  # 占行（首次写入；并发下唯一约束兜底）
            if now - rl.window_start > timedelta(hours=1):
                rl.sent_count = 0
                rl.window_start = now
            if rl.sent_count >= cap:
                db.session.rollback()  # 释放行锁，且不留半预留
                return False, '请求过于频繁'
            rl.sent_count += 1
        db.session.commit()
        return True, None

    def _refund_quota(self, phone, email, ip):
        """发送失败时退还额度（与 _reserve_quota 对称）。"""
        now = datetime.utcnow()
        for key_type, key_value in (('phone', phone), ('email', email), ('ip', ip)):
            if not key_value:
                continue
            rl = SmsRateLimit.query.filter_by(
                key_type=key_type, key_value=key_value).with_for_update().first()
            if rl and rl.sent_count > 0:
                rl.sent_count -= 1
        db.session.commit()

    # 兼容旧调用（仅读冷却+额度，不预留）
    def check_rate_limits(self, phone, email, ip):
        ok, reason = self._check_cooldown(phone)
        if not ok:
            return False, reason
        now = datetime.utcnow()
        for key_type, key_value, cap in (('phone', phone, HOURLY_LIMIT_PHONE),
                                         ('email', email, HOURLY_LIMIT_EMAIL),
                                         ('ip', ip, HOURLY_LIMIT_IP)):
            if not key_value:
                continue
            rl = SmsRateLimit.query.filter_by(key_type=key_type, key_value=key_value).first()
            if rl:
                if now - rl.window_start > timedelta(hours=1):
                    rl.sent_count = 0
                    rl.window_start = now
                if rl.sent_count >= cap:
                    return False, '请求过于频繁'
        return True, None

    # ---------- 身份匹配 ----------
    def _protected_list(self):
        import json
        st = SystemSetting.query.filter_by(setting_key='reset_protected_accounts').first()
        if not st or not st.setting_value:
            return []
        try:
            return [str(x).strip().lower() for x in json.loads(st.setting_value) if x]
        except Exception:
            return []

    def find_user_by_email_phone(self, email, phone):
        """返回 (matched: bool, info|None)。"""
        email = normalize_email(email)
        phone = normalize_phone(phone)
        if not email or not phone:
            return False, None

        domain = Domain.query.filter_by(is_active=True).order_by(Domain.id).first()
        if not domain:
            return False, None

        info = self.ldap.lookup_user_by_email(domain, email)
        if not info:
            return False, None
        if info.get('disabled'):
            return False, None
        if normalize_phone(info.get('mobile', '')) != phone:
            return False, None

        # 保护名单：DN / sAMAccountName / memberOf 任一命中
        protected = self._protected_list()
        candidates = {
            (info.get('user_dn') or '').lower(),
            (info.get('sam_account_name') or '').lower(),
        }
        candidates.update(m.lower() for m in info.get('member_of', []))
        if any(p in candidates for p in protected):
            return False, None

        return True, info

    # ---------- 发码与校验 ----------
    def issue_sms_code(self, user_dn, phone, email=None, ip=None):
        """发码：冷却检查 + 原子预留额度 + 作废旧码 + 建码；
        生产环境【异步】发送短信(响应即返回，抹平匹配/不匹配时序差)；
        演示模式同步发送(便于回显验证码)。发送失败退还额度、删码、不触发冷却。"""
        phone = normalize_phone(phone)
        ok, reason = self._check_cooldown(phone)
        if not ok:
            return False, reason
        ok, reason = self._reserve_quota(phone, email, ip)
        if not ok:
            return False, reason or '请求过于频繁'
        # 作废该手机所有未用旧码
        SmsVerificationCode.query.filter_by(phone=phone, is_used=False, purpose='reset').update(
            {'is_used': True})
        code = '%06d' % secrets.randbelow(1000000)
        hashed = bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        rec = SmsVerificationCode(
            phone=phone, code=hashed, purpose='reset', fail_count=0,
            expires_at=datetime.utcnow() + timedelta(minutes=CODE_TTL_MINUTES))
        db.session.add(rec)
        db.session.commit()

        if current_app.config.get('DEMO_MODE') or not current_app.config.get('SMS_ASYNC_SEND', True):
            # 演示或测试：同步发送（即时，便于页面回显验证码 / 测试断言）
            ok, msg = self.sms.send_verification_code(phone, code)
            if not ok:
                self._refund_quota(phone, email, ip)
                SmsVerificationCode.query.filter_by(id=rec.id).delete()
                db.session.commit()
                return False, '验证码发送失败，请稍后重试'
            return True, 'OK'

        # 生产：异步发送，立即返回（抹平匹配/不匹配时序差）
        self._send_async(phone, code, email, ip, rec.id)
        return True, 'OK'

    def _send_async(self, phone, code, email, ip, rec_id):
        """后台线程发送短信；失败则删码+退还额度（不触发冷却、不消耗额度）。"""
        import threading
        app = current_app._get_current_object()
        sms = self.sms

        def worker():
            try:
                with app.app_context():
                    ok, msg = sms.send_verification_code(phone, code)
                    if ok:
                        return  # 额度已预留，码已建，完成
                    # 失败：删码 + 退还额度（冷却因此不触发）
                    SmsVerificationCode.query.filter_by(id=rec_id).delete()
                    self._refund_quota(phone, email, ip)
                    db.session.commit()
                    app.logger.warning('短信发送失败(%s): %s', phone, msg)
            except Exception as e:
                try:
                    app.logger.error('异步发码异常: %s', e)
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def verify_sms_code(self, phone, code):
        phone = normalize_phone(phone)
        # 行锁：并发下串行化验证码消费，避免重复消费/计数错乱
        rec = (SmsVerificationCode.query
               .filter_by(phone=phone, is_used=False, purpose='reset')
               .order_by(SmsVerificationCode.created_at.desc())
               .with_for_update()
               .first())
        if not rec:
            return False, '请先获取验证码'
        if datetime.utcnow() > rec.expires_at:
            rec.is_used = True
            db.session.commit()
            return False, '验证码已失效，请重新获取'
        if rec.fail_count >= MAX_FAIL_COUNT:
            rec.is_used = True
            db.session.commit()
            return False, '错误次数过多，请重新获取验证码'
        if not bcrypt.checkpw((code or '').encode('utf-8'), rec.code.encode('utf-8')):
            rec.fail_count += 1
            db.session.commit()
            remaining = MAX_FAIL_COUNT - rec.fail_count
            if remaining <= 0:
                rec.is_used = True
                db.session.commit()
                return False, '错误次数过多，请重新获取验证码'
            return False, '验证码错误，还剩 %d 次' % remaining
        rec.is_used = True
        db.session.commit()
        return True, 'OK'

    # ---------- 重置 ----------
    def perform_reset(self, user_dn, new_password, config=None):
        cfg = config or current_app.config
        ok, msg = validate_password(new_password, cfg)
        if not ok:
            return False, msg
        domain = Domain.query.filter_by(is_active=True).order_by(Domain.id).first()
        if not domain:
            return False, '服务暂不可用，请联系管理员'
        ok, msg = self.ldap.admin_set_password_by_dn(domain, user_dn, new_password)
        if not ok:
            current_app.logger.error('AD 改密失败 user_dn=%s: %s', user_dn, msg)
            return False, '重置失败，请联系管理员'
        return True, 'OK'


def normalize_email(email):
    return (email or '').strip().lower()


def normalize_phone(phone):
    digits = re.sub(r'\D', '', phone or '')
    if len(digits) == 13 and digits.startswith('86'):
        digits = digits[2:]
    return digits


def validate_password(pw, config):
    if not pw:
        return False, '请输入新密码'
    if len(pw) < int(config.get('PASSWORD_MIN_LENGTH', 8)):
        return False, '新密码长度至少 %d 位' % config.get('PASSWORD_MIN_LENGTH', 8)
    if config.get('PASSWORD_REQUIRE_LOWERCASE') and not re.search(r'[a-z]', pw):
        return False, '密码必须包含小写字母'
    if config.get('PASSWORD_REQUIRE_UPPERCASE') and not re.search(r'[A-Z]', pw):
        return False, '密码必须包含大写字母'
    if config.get('PASSWORD_REQUIRE_NUMBER') and not re.search(r'\d', pw):
        return False, '密码必须包含数字'
    if config.get('PASSWORD_REQUIRE_SPECIAL') and not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", pw):
        return False, '密码必须包含特殊字符'
    return True, None
