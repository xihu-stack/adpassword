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
        return redirect(url_for('admin.dashboard' if session.get('user_role') == 'admin' else 'user.index'))
    
    # 模拟默认域配置
    domain_hint = '默认域'
    
    login_html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AD 密码管理系统 - LDAP 登录</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 20px;
            }
            .login-container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
                width: 100%;
                max-width: 450px;
            }
            .login-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
                border-color: #667eea;
            }
            .btn-login {
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
                color: #667eea;
                margin-top: 10px;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-header">
                <h1>AD 密码管理系统</h1>
                <p>Active Directory 身份认证</p>
            </div>
            <div class="login-body">
                {% if error %}
                <div class="error-message">{{ error }}</div>
                {% endif %}
                
                <form method="POST" action="{{ url_for('ldap_auth.authenticate') }}" id="loginForm">
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
                    session['mfa_enabled'] = admin_user.mfa_enabled if hasattr(admin_user, 'mfa_enabled') else False
                    
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
    
    # 其他用户使用 LDAP 认证
    # 获取域配置
    domain = Domain.query.filter_by(is_active=True).first()
    if not domain:
        return redirect(url_for('ldap_auth.login', error='未配置域信息', username=username))
    
    try:
        # 尝试使用 LDAP 服务进行认证
        from ldap3 import Server, Connection, ALL, SIMPLE, SUBTREE
        from services.ldap_service import LdapService
        
        # 判断是否使用 SSL
        use_ssl = domain.use_ssl or (domain.ldap_port == 636)
        protocol = 'ldaps' if use_ssl else 'ldap'
        port = domain.ldaps_port if use_ssl else domain.ldap_port
        
        server_url = f"{protocol}://{domain.ldap_host}:{port}"
        print(f'[LDAP 认证] 连接服务器：{server_url}')
        
        # 创建服务器对象
        if use_ssl:
            from ldap3 import Tls
            import ssl
            tls_context = Tls(
                validate=ssl.CERT_NONE,
                version=ssl.PROTOCOL_TLS_CLIENT,
                ciphers='ALL:@SECLEVEL=0'
            )
            server = Server(server_url, get_info=ALL, tls=tls_context, connect_timeout=10)
        else:
            server = Server(server_url, get_info=ALL, connect_timeout=10)
        
        # 尝试 1: 直接使用输入的 username 作为 UPN 进行认证
        # 用户可能输入的是 UPN (如 zhangsan@domain.com) 或纯用户名 (如 zhangsan)
        upn_to_try = username
        
        # 如果用户名不包含 @，自动添加域名构成 UPN
        if '@' not in username:
            # 从 base_dn 提取域名
            dc_parts = [part.replace('DC=', '').strip() for part in domain.base_dn.split(',') if 'DC=' in part]
            if dc_parts:
                domain_name = '.'.join(dc_parts)
                upn_to_try = f"{username}@{domain_name}"
                print(f'[LDAP 认证] 自动构造 UPN: {upn_to_try}')
        
        # 使用 UPN 进行 LDAP 绑定
        conn = None
        try:
            conn = Connection(
                server,
                user=upn_to_try,
                password=password,
                authentication=SIMPLE,
                auto_bind=True,
                receive_timeout=30
            )
            print(f'[LDAP 认证] ✅ 认证成功，UPN: {upn_to_try}')
        except Exception as bind_error:
            print(f'[LDAP 认证] ❌ UPN 认证失败：{str(bind_error)[:200]}')
            # 如果 UPN 认证失败，尝试使用 DN 认证
            # 先搜索用户的 DN
            search_filter = f'(|(userPrincipalName={username})(sAMAccountName={username}))'
            result = conn.search(
                search_base=domain.base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=['distinguishedName', 'userPrincipalName', 'mail', 'displayName', 'telephoneNumber', 'mobile']
            ) if conn else False
            
            if result and len(conn.entries) > 0:
                entry = conn.entries[0]
                user_dn = str(entry.distinguishedName.value)
                print(f'[LDAP 认证] 找到用户 DN: {user_dn}')
                
                # 使用 DN 重新认证
                try:
                    conn = Connection(
                        server,
                        user=user_dn,
                        password=password,
                        authentication=SIMPLE,
                        auto_bind=True,
                        receive_timeout=30
                    )
                    print(f'[LDAP 认证] ✅ DN 认证成功')
                except Exception as dn_error:
                    print(f'[LDAP 认证] ❌ DN 认证也失败：{str(dn_error)[:200]}')
                    raise Exception('LDAP 认证失败')
            else:
                raise Exception('LDAP 认证失败')
        
        # 认证成功后，获取用户信息
        # 使用绑定的连接搜索用户详细信息
        search_filter = f'(|(userPrincipalName={upn_to_try})(sAMAccountName={username.split("@")[0] if "@" in upn_to_try else username}))'
        result = conn.search(
            search_base=domain.base_dn,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=['distinguishedName', 'userPrincipalName', 'mail', 'displayName', 'telephoneNumber', 'mobile', 'sAMAccountName']
        )
        
        if result and len(conn.entries) > 0:
            entry = conn.entries[0]
            user_info = {
                'dn': str(entry.distinguishedName.value),
                'email': str(entry.mail.value) if hasattr(entry, 'mail') and entry.mail.value else '',
                'display_name': str(entry.displayName.value) if hasattr(entry, 'displayName') and entry.displayName.value else username,
                'phone': str(entry.telephoneNumber.value) if hasattr(entry, 'telephoneNumber') and entry.telephoneNumber.value else '',
                'mobile': str(entry.mobile.value) if hasattr(entry, 'mobile') and entry.mobile.value else '',
                'upn': str(entry.userPrincipalName.value) if hasattr(entry, 'userPrincipalName') and entry.userPrincipalName.value else upn_to_try,
            }
            print(f'[LDAP 认证] 获取到用户信息：{user_info}')
        else:
            # 如果搜索失败，使用基本信息
            user_info = {
                'dn': '',
                'email': '',
                'display_name': username,
                'phone': '',
                'mobile': '',
                'upn': upn_to_try
            }
        
        success = True
        message = '认证成功'
        
    except Exception as e:
        print(f'[LDAP 认证] 认证异常：{str(e)}')
        success = False
        message = str(e)
        user_info = None
    
    if not success:
        return redirect(url_for('ldap_auth.login', error=f'认证失败：{message}', username=username))
    
    # 查询或创建本地用户
    # 优先使用 UPN 查询，如果没有 UPN 则使用 username
    user = User.query.filter_by(username=user_info.get('upn', username)).first()
    if not user:
        user = User.query.filter_by(username=username).first()
    
    if not user:
        # 如果是 AD 同步过来的用户，应该在 sync 时已经创建
        # 这里是首次登录的 AD 用户，自动创建本地账号
        try:
            # 使用 UPN 作为用户名，如果没有 UPN 则使用原始 username
            login_username = user_info.get('upn', username)
            
            user = User(
                username=login_username,
                ad_email=user_info.get('email', ''),
                phone=user_info.get('mobile', ''),
                display_name=user_info.get('display_name', username),
                ad_dn=user_info.get('dn', ''),
                # 不存储密码，使用 LDAP 认证
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            print(f'[LDAP 登录] 创建新用户：{login_username}, ID={user.id}')
        except Exception as e:
            print(f'[LDAP 登录] 创建用户失败：{str(e)}')
            db.session.rollback()
            return redirect(url_for('ldap_auth.login', error='无法创建本地用户', username=username))
    else:
        print(f'[LDAP 登录] 用户已存在：{user.username}, ID={user.id}')
    
    # 设置会话 - 使用数据库中的用户 ID
    session['user_id'] = user.id
    session['username'] = user.username
    session['user_role'] = 'admin' if user.username == 'admin' else 'user'
    session['mfa_enabled'] = user.mfa_enabled if hasattr(user, 'mfa_enabled') else False
    
    # 记录登录日志
    from utils.logger import log_operation
    log_operation(
        'login',
        target_user=user.username,
        details=f'用户 {user.username} 登录成功'
    )
    
    # 重定向
    if session['user_role'] == 'admin':
        return redirect(url_for('admin.dashboard'))
    else:
        return redirect(url_for('user.index'))


@ldap_auth_bp.route('/logout')
def logout():
    """登出"""
    session.clear()
    return redirect(url_for('ldap_auth.login'))
