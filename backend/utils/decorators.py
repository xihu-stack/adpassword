from functools import wraps
from flask import session, redirect, url_for, jsonify, request, current_app
from ipaddress import ip_address, ip_network


def _effective_allowed_ips():
    """生效的管理员 IP 白名单 = .env 静态基线 + 后台【访问控制】页动态配置（并集）。
    动态配置存 SystemSetting(admin_allowed_ips)，保存后即时生效、无需重启。"""
    allowed = list(current_app.config.get('ADMIN_ALLOWED_IPS', []))
    try:
        from models.models import SystemSetting
        st = SystemSetting.query.filter_by(setting_key='admin_allowed_ips').first()
        if st and st.setting_value:
            allowed += [s.strip() for s in st.setting_value.split(',') if s.strip()]
    except Exception:
        pass  # 数据库异常时退回 .env 基线
    return allowed


def _ip_in_lists(client, cidrs):
    """判断 IP 是否落在任一 网段/单IP 条目内。"""
    try:
        client_ip = ip_address(client)
    except ValueError:
        return False
    for cidr in cidrs:
        entry = cidr if '/' in cidr else cidr + ('/128' if ':' in cidr else '/32')
        try:
            if client_ip in ip_network(entry, strict=False):
                return True
        except ValueError:
            continue
    return False


def _ip_allowed():
    """检查当前请求 IP 是否在管理员白名单内。留空=不限制。"""
    allowed = _effective_allowed_ips()
    if not allowed:
        return True  # 未配置白名单 = 不限制
    return _ip_in_lists(request.remote_addr or '', allowed)


def internal_only(f):
    """限制只有内网白名单 IP 可访问（用于 /login 和 /admin/*）。"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not _ip_allowed():
            if request.is_json:
                return jsonify({'success': False, 'message': '管理后台仅限内网访问'}), 403
            return '管理后台仅限内网访问', 403
        return f(*args, **kwargs)
    return decorated_function


def login_required(f):
    """要求用户登录的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'success': False, 'message': '请先登录'}), 401
            return redirect(url_for('ldap_auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """要求管理员权限的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not _ip_allowed():
            if request.is_json:
                return jsonify({'success': False, 'message': '管理后台仅限内网访问'}), 403
            return '管理后台仅限内网访问', 403
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'success': False, 'message': '请先登录'}), 401
            return redirect(url_for('ldap_auth.login'))

        if session.get('user_role') != 'admin':
            if request.is_json:
                return jsonify({'success': False, 'message': '权限不足'}), 403
            return redirect(url_for('reset.reset_page'))

        return f(*args, **kwargs)
    return decorated_function
