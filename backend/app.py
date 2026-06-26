from flask import Flask, redirect, url_for, session, request, jsonify, make_response
from flask_cors import CORS
from flask_wtf import CSRFProtect
from config import Config
from models.models import db, User
import os
import bcrypt
import secrets
import logging


def create_app(testing=False):
    app = Flask(__name__)

    if testing:
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'testing-secret-key-do-not-use-in-prod')
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('TEST_DATABASE_URL', 'sqlite:///:memory:')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['CORS_ORIGINS'] = []
        app.config['PASSWORD_MIN_LENGTH'] = 8
        app.config['PASSWORD_REQUIRE_UPPERCASE'] = True
        app.config['PASSWORD_REQUIRE_LOWERCASE'] = True
        app.config['PASSWORD_REQUIRE_NUMBER'] = True
        app.config['PASSWORD_REQUIRE_SPECIAL'] = True
        app.config['DEMO_MODE'] = False
        # Keys consumed by Config.init_app (called later in create_app)
        app.config['SQLALCHEMY_ECHO'] = False
        app.config['LOG_LEVEL'] = 'WARNING'
        app.config['LOG_FILE'] = 'logs/test-app.log'
        app.config['LOG_MAX_BYTES'] = 10485760
        app.config['LOG_BACKUP_COUNT'] = 5
        # SQLite in-memory needs StaticPool to share the connection
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            from sqlalchemy.pool import StaticPool
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'connect_args': {'check_same_thread': False},
                'poolclass': StaticPool,
            }
    else:
        app.config.from_object(Config)

    # 自定义错误处理 - 不暴露敏感信息
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'message': '资源不存在'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        # 记录详细错误日志
        app.logger.error(f'服务器内部错误：{str(error)}', exc_info=True)
        return jsonify({
            'success': False,
            'message': '服务器内部错误'
        }), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'success': False,
            'message': '禁止访问'
        }), 403
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'success': False,
            'message': '未授权访问'
        }), 401
    
    @app.errorhandler(429)
    def ratelimit_handler(error):
        return jsonify({
            'success': False,
            'message': '请求过于频繁，请稍后再试'
        }), 429
    
    # 安全响应头配置
    @app.after_request
    def security_headers(response):
        # 隐藏服务器信息
        response.headers['Server'] = 'Web Server'
        response.headers.pop('X-Powered-By', None)
        
        # 安全响应头
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31540000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:;"
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # 添加请求 ID 便于追踪
        response.headers['X-Request-ID'] = secrets.token_hex(16)
        
        return response
    
    # 请求日志和安全检查
    @app.before_request
    def before_request():
        # 记录请求日志
        app.logger.info(f'{request.method} {request.path} - IP: {request.remote_addr}')
        
        # 检查请求方法
        if request.method not in ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']:
            return jsonify({
                'success': False,
                'message': '不支持的请求方法'
            }), 405
        
        # 检查 Content-Type（非 GET/OPTIONS 请求）
        if request.method not in ['GET', 'OPTIONS'] and request.content_type:
            if 'application/json' not in request.content_type:
                app.logger.warning(f'非法的 Content-Type: {request.content_type}')
    
    # 初始化扩展
    CORS(app, 
         origins=app.config['CORS_ORIGINS'],
         supports_credentials=app.config.get('CORS_SUPPORTS_CREDENTIALS', True),
         expose_headers=app.config.get('CORS_EXPOSE_HEADERS', []))

    # 反向代理（nginx/gunicorn）后取真实客户端 IP 用于限流。
    # 仅信任 1 层代理设置的 X-Forwarded-For；若多层代理请调大 x_for。
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # 注册蓝图
    from routes.ldap_auth import ldap_auth_bp
    from routes.admin import admin_bp
    from routes.reset import reset_bp

    app.register_blueprint(ldap_auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(reset_bp)
    
    # 根路由 - 重定向到登录页
    @app.route('/')
    def index():
        if 'user_id' in session and session.get('user_role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('reset.reset_page'))
    
    # 健康检查接口（用于负载均衡器）
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'service': 'AD Password Management System'
        }), 200
    
    # 启用 CSRF 保护（在测试模式下通过 WTF_CSRF_ENABLED=False 关闭）
    csrf = CSRFProtect(app)

    # 初始化数据库
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        
        # 创建默认管理员账号（仅当数据库为空时）
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count == 0:
            # 检查是否通过环境变量设置了管理员密码
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin')
            if admin_password == 'admin':
                app.logger.warning('⚠️  使用默认管理员密码，请在生产环境中修改！')
            
            hashed = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            admin = User(
                username='admin',
                password_hash=hashed,
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            app.logger.info('✓ 已创建默认管理员账号：admin')

        # 演示模式：自动种入一个激活域，使公开重置流程可体验（不连真实 AD）
        if app.config.get('DEMO_MODE') and not testing:
            from models.models import Domain
            if Domain.query.filter_by(is_active=True).count() == 0:
                demo_domain = Domain(
                    name='演示域 (DEMO)', ldap_hosts='demo-dc', ldap_port=389,
                    ldaps_port=636, base_dn='DC=demo,DC=com',
                    admin_dn='CN=Admin,DC=demo,DC=com',
                    use_ssl=False, is_active=True)
                demo_domain.set_admin_password('demo')  # 加密存储（即使是演示值）
                db.session.add(demo_domain)
                db.session.commit()
                app.logger.info('✓ [DEMO_MODE] 已种入演示域配置')

        # 初始化配置
        Config.init_app(app)
    
    return app


# 在模块级别创建 app 实例，供 Gunicorn 使用
app = create_app()


if __name__ == '__main__':
    # Windows 控制台默认 GBK 编码无法输出 emoji，强制 UTF-8 避免启动横幅崩溃
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    app = create_app()

    # 从系统设置中读取端口和主机配置
    try:
        with app.app_context():
            from models.models import SystemSetting
            port_setting = SystemSetting.query.filter_by(setting_key='system_port').first()
            host_setting = SystemSetting.query.filter_by(setting_key='system_host').first()
            
            port = int(port_setting.setting_value) if port_setting else 5000
            host = host_setting.setting_value if host_setting else '0.0.0.0'
    except Exception as e:
        print(f"⚠️ 无法从数据库读取端口配置，使用默认值：{e}")
        port = 5000
        host = '0.0.0.0'
    
    # 检测操作系统，选择合适的 WSGI 服务器
    import sys
    import platform
    
    system = platform.system().lower()
    
    print(f"\n🚀 AD 密码管理系统")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ 系统环境：{system} ({platform.release()})")
    print(f"✅ Python 版本：{sys.version.split()[0]}")
    print(f"✅ 监听地址：http://{host}:{port}")
    print(f"✅ 访问方式:")
    print(f"   - 本地访问：http://127.0.0.1:{port}")
    print(f"   - 局域网访问：http://{host}:{port}")
    print(f"\n👤 默认账号：admin")
    print(f"🔑 默认密码：admin")
    print(f"\n⚠️  首次登录后请立即修改密码！")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    # 生产环境使用 Gunicorn (Linux) 或 Waitress (Windows)
    if system == 'linux':
        try:
            from gunicorn.app.wsgiapp import run
            print("🔧 使用 Gunicorn 生产级服务器\n")
            # 使用 Gunicorn 启动
            import os
            os.argv = ['gunicorn', '-b', f'{host}:{port}', '-w', '4', 'app:app']
            run()
        except ImportError:
            print("⚠️  Gunicorn 未安装，使用 Flask 开发服务器")
            print("💡 建议安装：pip install gunicorn\n")
            app.run(host=host, port=port, debug=False)
    elif system == 'windows':
        try:
            from waitress import serve
            print("🔧 使用 Waitress 生产级服务器\n")
            # 使用 Waitress 启动
            serve(app, host=host, port=port)
        except ImportError:
            print("⚠️  Waitress 未安装，使用 Flask 开发服务器")
            print("💡 建议安装：pip install waitress\n")
            app.run(host=host, port=port, debug=False)
    else:
        print(f"⚠️  未知操作系统：{system}，使用 Flask 开发服务器\n")
        app.run(host=host, port=port, debug=False)
