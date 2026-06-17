import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask 配置
    SECRET_KEY = os.getenv('SECRET_KEY')  # 生产环境必须设置
    if not SECRET_KEY:
        raise ValueError("⚠️  生产环境必须设置 SECRET_KEY 环境变量！")
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("⚠️  生产环境必须设置 DATABASE_URL 环境变量！")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # 生产环境不打印 SQL
    
    # CAS 配置（已禁用）
    # CAS_SERVER_LOGIN_URL = os.getenv('CAS_SERVER_LOGIN_URL', 'https://cas.example.com/login')
    # CAS_SERVER_LOGOUT_URL = os.getenv('CAS_SERVER_LOGOUT_URL', 'https://cas.example.com/logout')
    # CAS_SERVER_VALIDATE_URL = os.getenv('CAS_SERVER_VALIDATE_URL', 'https://cas.example.com/p3/serviceValidate')
    # CAS_AFTER_LOGIN_URL = os.getenv('CAS_AFTER_LOGIN_URL', 'http://localhost:5000/cas/callback')
    
    # 会话配置 - 生产环境使用更安全的设置
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.getenv('SESSION_TIMEOUT', '8')))
    SESSION_COOKIE_SECURE = os.getenv('HTTPS_ENABLED', 'false').lower() == 'true'  # 根据环境变量决定是否仅 HTTPS
    SESSION_COOKIE_HTTPONLY = True  # 禁止 JavaScript 访问
    SESSION_COOKIE_SAMESITE = 'Lax'  # 防止 CSRF
    SESSION_COOKIE_NAME = 'ad_session'  # 自定义 session 名称
    
    # 上传配置
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_UPLOAD_SIZE', '16')) * 1024 * 1024  # 默认 16MB
    
    # CORS 配置 - 生产环境限制为实际域名
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',')
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_EXPOSE_HEADERS = ['Content-Type', 'X-Request-ID']
    
    # 安全配置
    SEND_FILE_MAX_AGE_DEFAULT = 3600
    DEBUG = False  # 生产环境必须关闭 debug
    
    # 密码策略配置
    PASSWORD_MIN_LENGTH = int(os.getenv('PASSWORD_MIN_LENGTH', '8'))
    PASSWORD_REQUIRE_UPPERCASE = os.getenv('PASSWORD_REQUIRE_UPPERCASE', 'true').lower() == 'true'
    PASSWORD_REQUIRE_LOWERCASE = os.getenv('PASSWORD_REQUIRE_LOWERCASE', 'true').lower() == 'true'
    PASSWORD_REQUIRE_NUMBER = os.getenv('PASSWORD_REQUIRE_NUMBER', 'true').lower() == 'true'
    PASSWORD_REQUIRE_SPECIAL = os.getenv('PASSWORD_REQUIRE_SPECIAL', 'true').lower() == 'true'
    
    # 安全增强配置
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # CSRF token 有效期
    WTF_CSRF_SSL_STRICT = True
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    @classmethod
    def init_app(cls, app):
        """生产环境初始化"""
        # 生产环境配置
        if not app.debug:
            app.config['SQLALCHEMY_ECHO'] = False
            
            # 配置日志
            import logging
            from logging.handlers import RotatingFileHandler
            import os
            
            # 确保日志目录存在
            log_dir = os.path.dirname(app.config['LOG_FILE'])
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 配置文件日志处理器
            file_handler = RotatingFileHandler(
                app.config['LOG_FILE'],
                maxBytes=app.config['LOG_MAX_BYTES'],
                backupCount=app.config['LOG_BACKUP_COUNT']
            )
            file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
            
            # 配置日志格式
            formatter = logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            )
            file_handler.setFormatter(formatter)
            
            # 添加日志处理器
            app.logger.addHandler(file_handler)
            app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))
            app.logger.info('AD 密码管理系统启动')
