from functools import wraps
from flask import session, redirect, url_for, jsonify, request


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
