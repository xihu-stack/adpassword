from flask import Blueprint, request, redirect, session, url_for, current_app
from models.models import db, User
import bcrypt

mock_cas_bp = Blueprint('mock_cas', __name__)


@mock_cas_bp.route('/mock-cas/login')
def mock_login():
    """模拟 CAS 登录页面"""
    # 获取 service 参数
    service = request.args.get('service', '')
    
    # 返回简单的登录表单
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>CAS 登录（模拟）</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .login-box {{
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                width: 400px;
            }}
            h1 {{
                color: #333;
                text-align: center;
                margin-bottom: 30px;
            }}
            .form-group {{
                margin-bottom: 20px;
            }}
            label {{
                display: block;
                margin-bottom: 8px;
                color: #555;
                font-weight: bold;
            }}
            input[type="text"],
            input[type="password"] {{
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
                box-sizing: border-box;
            }}
            input[type="submit"] {{
                width: 100%;
                padding: 12px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
                font-weight: bold;
            }}
            input[type="submit"]:hover {{
                opacity: 0.9;
            }}
            .info {{
                background: #f0f9eb;
                border-left: 4px solid #67C23A;
                padding: 15px;
                margin-top: 20px;
                border-radius: 3px;
            }}
            .info p {{
                margin: 5px 0;
                color: #67C23A;
                font-size: 13px;
            }}
        </style>
    </head>
    <body>
        <div class="login-box">
            <h1>🔐 CAS 登录</h1>
            <form method="POST" action="{url_for('mock_cas.mock_validate', _external=True)}">
                <input type="hidden" name="service" value="{service}">
                <div class="form-group">
                    <label for="username">用户名</label>
                    <input type="text" id="username" name="username" required 
                           placeholder="请输入用户名" value="admin">
                </div>
                <div class="form-group">
                    <label for="password">密码</label>
                    <input type="password" id="password" name="password" required 
                           placeholder="请输入密码" value="admin">
                </div>
                <div class="form-group">
                    <input type="submit" value="登录">
                </div>
            </form>
            <div class="info">
                <p><strong>💡 提示：</strong></p>
                <p>这是模拟 CAS 登录页面</p>
                <p>默认账号：<code>admin / admin</code></p>
                <p>您可以输入任何用户名和密码进行登录</p>
            </div>
        </div>
    </body>
    </html>
    '''


@mock_cas_bp.route('/mock-cas/validate', methods=['POST'])
def mock_validate():
    """模拟 CAS 验证"""
    username = request.form.get('username')
    password = request.form.get('password')
    service = request.form.get('service')
    
    # 简单验证（实际应该验证 LDAP）
    if username and password:
        # 在数据库中查找或创建用户
        user = User.query.filter_by(username=username).first()
        
        if not user:
            # 创建新用户
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            user = User(
                username=username,
                password_hash=hashed,
                role='user' if username != 'admin' else 'admin'
            )
            db.session.add(user)
            db.session.commit()
        
        # 设置会话
        session['user_id'] = user.id
        session['username'] = user.username
        session['user_role'] = user.role
        session['mfa_enabled'] = user.mfa_enabled
        
        # 重定向到 service URL
        if service:
            return redirect(service)
        else:
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('user.index'))
    
    return redirect(url_for('mock_cas.mock_login'))


@mock_cas_bp.route('/logout')
def logout():
    """登出"""
    session.clear()
    return redirect(url_for('mock_cas.mock_login'))
