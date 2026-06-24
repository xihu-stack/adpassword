from flask import Blueprint, request, redirect, session, url_for, current_app, render_template_string
from models.models import db, User, Domain
try:
    from services.ldap_service import LdapService
except ImportError:
    from services.ldap_service_mock import LdapService
import bcrypt

ldap_auth_bp = Blueprint('ldap_auth', __name__)


@ldap_auth_bp.route('/login-test')
def login_test():
    """登录测试页面"""
    return render_template_string(open('templates/login_test.html', 'r', encoding='utf-8').read())


@ldap_auth_bp.route('/login')
def login():
    """LDAP 登录页面"""
    if 'user_id' in session:
        return redirect(url_for('admin.dashboard' if session.get('user_role') == 'admin' else 'reset.reset_page'))
    
    # 模拟默认域配置
    domain_hint = '默认域'
    
    login_html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>华深智药 - LDAP 登录</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                background: linear-gradient(135deg, #15376b 0%, #1f5fa8 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 20px;
            }
            .login-container {
                position: relative;
                z-index: 1;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
                width: 100%;
                max-width: 450px;
            }
            .login-header {
                background: linear-gradient(135deg, #15376b 0%, #1f5fa8 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .login-header h1 {
                font-size: 28px;
                margin-bottom: 10px;
            }
            .login-header p {
                font-size: 14px;
                opacity: 0.9;
            }
            .login-body {
                padding: 40px 30px;
            }
            .form-group {
                margin-bottom: 25px;
            }
            .form-group label {
                display: block;
                color: #333;
                font-weight: bold;
                margin-bottom: 8px;
                font-size: 14px;
            }
            .form-group input {
                width: 100%;
                padding: 12px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                transition: border-color 0.3s;
            }
            .form-group input:focus {
                outline: none;
                border-color: #15376b;
            }
            .btn-login {
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #15376b 0%, #1f5fa8 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                transition: transform 0.2s;
            }
            .btn-login:hover {
                transform: translateY(-2px);
            }
            .btn-login:active {
                transform: translateY(0);
            }
            .domain-info {
                background: #f0f9eb;
                border-left: 4px solid #67C23A;
                padding: 15px;
                margin-top: 20px;
                border-radius: 4px;
            }
            .domain-info p {
                color: #67C23A;
                font-size: 13px;
                margin: 5px 0;
            }
            .error-message {
                background: #fef0f0;
                border: 1px solid #fde2e2;
                color: #f56c6c;
                padding: 12px;
                border-radius: 4px;
                margin-bottom: 20px;
                font-size: 14px;
            }
            .loading {
                display: none;
                text-align: center;
                color: #15376b;
                margin-top: 10px;
            }
        </style>
    </head>
    <body>
        <div id="bg-host"></div>
<script>const CSRF_TOKEN="{{ csrf_token() }}";(function(){var f=window.fetch;window.fetch=function(u,o){o=o||{};o.headers=o.headers||{};if(!o.headers['X-CSRFToken']){o.headers['X-CSRFToken']=CSRF_TOKEN;}return f(u,o);};})();</script>
        <div class="login-container">
            <div class="login-header">
                <img src="{{ url_for('static', filename='logo.png') }}" alt="华深智药" style="height:46px;margin-bottom:10px;filter:drop-shadow(0 2px 8px rgba(0,0,0,.3));">
                <h1>华深智药</h1>
                <p>管理员登录</p>
            </div>
            <div class="login-body">
                {% if error %}
                <div class="error-message">{{ error }}</div>
                {% endif %}
                
                <form method="POST" action="{{ url_for('ldap_auth.authenticate') }}" id="loginForm">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <div class="form-group">
                        <label for="username">用户名 / Username</label>
                        <input type="text" id="username" name="username" required 
                               placeholder="请输入 AD 用户名 (如：zhangsan 或 zhangsan@domain.com)" value="{{ username or '' }}">
                    </div>
                    
                    <div class="form-group">
                        <label for="password">密码 / Password</label>
                        <input type="password" id="password" name="password" required 
                               placeholder="请输入 AD 密码">
                    </div>
                    
                    <button type="submit" class="btn-login">
                        登录
                    </button>
                    
                    <div class="loading" id="loading">
                        正在验证...
                    </div>
                </form>
                
                <div class="domain-info">
                    <p><strong>当前域:</strong> {{ domain_hint }}</p>
                    <p><strong>提示:</strong> 请使用 AD 域账号和密码登录</p>
                </div>
            </div>
        </div>
        
        <script>
            document.getElementById('loginForm').addEventListener('submit', function() {
                document.getElementById('loading').style.display = 'block';
            });
        </script>
        <script src="{{ url_for('static', filename='p5.min.js') }}?v=1"></script>
        <script src="{{ url_for('static', filename='bg.js') }}?v=4"></script>
    </body>
    </html>
    '''
    
    return render_template_string(login_html, 
                                domain_hint=domain_hint,
                                error=request.args.get('error'),
                                username=request.args.get('username', ''))


@ldap_auth_bp.route('/authenticate', methods=['POST'])
def authenticate():
    """LDAP 认证处理 - 使用 userPrincipalName 登录 (admin 使用本地认证)"""
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return redirect(url_for('ldap_auth.login', error='请输入用户名和密码', username=username))
    
    # 特殊处理：admin 账户使用本地密码认证 (不通过 LDAP)
    if username == 'admin':
        # 检查数据库中是否存在 admin 用户
        admin_user = User.query.filter_by(username='admin').first()
        
        if admin_user:
            # 检查 password_hash 是否存在，如果不存在或为 None，初始化为 'admin'
            if not admin_user.password_hash:
                # 首次使用，设置默认密码为 admin (bcrypt 加密)
                import bcrypt
                admin_user.password_hash = bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                db.session.commit()
                print(f'[本地认证] ✅ 已为 admin 账户设置默认密码 (bcrypt 加密)')
            
            # 验证密码 (使用 bcrypt)
            import bcrypt
            try:
                if bcrypt.checkpw(password.encode('utf-8'), admin_user.password_hash.encode('utf-8')):
                    # 认证成功
                    print(f'[本地认证] ✅ admin 账户认证成功')
                    
                    # 设置会话
                    session['user_id'] = admin_user.id
                    session['username'] = 'admin'
                    session['user_role'] = 'admin'

                    # 记录登录日志
                    from utils.logger import log_operation
                    log_operation(
                        'login',
                        target_user='admin',
                        details=f'管理员 admin 登录成功'
                    )
                    
                    return redirect(url_for('admin.dashboard'))
                else:
                    # 密码错误
                    return redirect(url_for('ldap_auth.login', error='管理员账户或密码错误', username=username))
            except Exception as e:
                print(f'[本地认证] ❌ 密码验证异常：{str(e)}')
                return redirect(url_for('ldap_auth.login', error='认证异常，请稍后重试', username=username))
        else:
            # admin 账户不存在
            return redirect(url_for('ldap_auth.login', error='管理员账户不存在', username=username))

    # 非 admin 不再支持登录（系统已改为公开"忘记密码"自助重置）
    return redirect(url_for('ldap_auth.login', error='普通用户请使用"忘记密码"自助重置', username=username))


@ldap_auth_bp.route('/logout')
def logout():
    """登出"""
    session.clear()
    return redirect(url_for('ldap_auth.login'))

