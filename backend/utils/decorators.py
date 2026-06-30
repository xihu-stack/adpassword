from functools import wraps
from flask import session, redirect, url_for, jsonify, request, current_app
from ipaddress import ip_address, ip_network


def _ip_allowed():
    """检查当前请求 IP 是否在管理员白名单内。留空=不限制。"""
    allowed = current_app.config.get('ADMIN_ALLOWED_IPS', [])
    if not allowed:
        return True  # 未配置白名单 = 不限制
    client = request.remote_addr or ''
    try:
        client_ip = ip_address(client)
        for cidr in allowed:
            if '/' not in cidr:
                cidr = cidr + '/32'
            if client_ip in ip_network(cidr, strict=False):
                return True
    except Exception:
        pass
    return False


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
