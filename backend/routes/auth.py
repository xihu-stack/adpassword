# CAS 相关路由已暂时禁用
# from flask import Blueprint, request, redirect, session, url_for, current_app, render_template
# from models.models import db, User, Domain
# try:
#     from services.ldap_service import LdapService
# except ImportError:
#     from services.ldap_service_mock import LdapService
# from services.cas_service import CasService

# auth_bp = Blueprint('auth', __name__)


# @auth_bp.route('/login')
# def login():
#     """跳转到 CAS 登录"""
#     if 'user_id' in session:
#         return redirect(url_for('admin.dashboard' if session.get('user_role') == 'admin' else 'user.index'))
    
#     service_url = current_app.config['CAS_AFTER_LOGIN_URL']
#     cas_url = CasService.get_login_url(service_url)
#     return redirect(cas_url)


# @auth_bp.route('/cas/callback')
# def cas_callback():
#     """CAS 登录回调"""
#     ticket = request.args.get('ticket')
#     if not ticket:
#         return redirect(url_for('auth.login'))
    
#     service_url = current_app.config['CAS_AFTER_LOGIN_URL']
#     success, result = CasService.validate_ticket(ticket, service_url)
    
#     if not success:
#         return f"CAS 认证失败：{result}", 401
    
#     username = result
    
#     # 在数据库中查找或创建用户
#     user = User.query.filter_by(username=username).first()
    
#     if not user:
#         # 从 AD 同步用户信息
#         domain = Domain.query.filter_by(is_active=True).first()
#         if domain:
#             user_info = LdapService.sync_user_info(domain, username)
#             if user_info:
#                 user = User(
#                     username=username,
#                     ad_dn=user_info['dn'],
#                     ad_email=user_info['email'],
#                     ad_display_name=user_info['display_name'],
#                     phone=user_info.get('mobile', ''),
#                     domain_id=domain.id
#                 )
#                 db.session.add(user)
#                 db.session.commit()
#         else:
#             # 如果没有配置域，创建基本用户
#             user = User(username=username)
#             db.session.add(user)
#             db.session.commit()
    
#     # 设置会话
#     session['user_id'] = user.id
#     session['username'] = user.username
#     session['user_role'] = user.role
#     session['mfa_enabled'] = user.mfa_enabled
    
#     # 检查是否需要绑定 MFA
#     if user.mfa_enabled:
#         return redirect(url_for('auth.verify_mfa'))
    
#     if user.role == 'admin':
#         return redirect(url_for('admin.dashboard'))
#     else:
#         return redirect(url_for('user.index'))


# @auth_bp.route('/verify-mfa', methods=['GET', 'POST'])
# def verify_mfa():
#     """验证 MFA 页面"""
#     if request.method == 'POST':
#         from services.totp_service import TotpService
        
#         code = request.form.get('code')
#         user = User.query.get(session['user_id'])
        
#         if not user or not user.mfa_secret:
#             return redirect(url_for('auth.logout'))
        
#         if TotpService.verify_code(user.mfa_secret, code):
#             session['mfa_verified'] = True
#             if user.role == 'admin':
#                 return redirect(url_for('admin.dashboard'))
#             else:
#                 return redirect(url_for('user.index'))
#         else:
#             return render_template('verify_mfa.html', error='验证码错误')
    
#     return render_template('verify_mfa.html')


# @auth_bp.route('/logout')
# def logout():
#     """登出"""
#     session.clear()
#     cas_logout_url = CasService.logout(request.url_root)
#     return redirect(cas_logout_url)

# 临时禁用的蓝图
auth_bp = None
