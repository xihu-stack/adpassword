from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from services import secret_crypto

db = SQLAlchemy()

class Domain(db.Model):
    __tablename__ = 'domains'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ldap_hosts = db.Column(db.String(500), nullable=False)  # 支持多个主机，逗号分隔
    ldap_host = db.Column(db.String(200), nullable=True)  # 保留字段以兼容旧数据
    ldap_port = db.Column(db.Integer, default=389)
    ldaps_port = db.Column(db.Integer, default=636)
    base_dn = db.Column(db.String(255), nullable=False)
    admin_dn = db.Column(db.String(255), nullable=False)
    admin_password = db.Column(db.String(255), nullable=False)  # 本地管理员密码（bcrypt 加密）
    ldap_password = db.Column(db.String(255))  # LDAP 连接明文密码
    use_ssl = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_connected = db.Column(db.Boolean, default=False)  # 连接状态
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'ldap_hosts': self.ldap_hosts,
            'ldap_host': self.ldap_host,  # 兼容旧字段
            'ldap_port': self.ldap_port,
            'ldaps_port': self.ldaps_port,
            'base_dn': self.base_dn,
            'admin_dn': self.admin_dn,
            'use_ssl': self.use_ssl,
            'is_active': self.is_active,
        }

    def set_admin_password(self, plain):
        self.admin_password = secret_crypto.encrypt_value(plain)

    @property
    def admin_password_plain(self):
        return secret_crypto.decrypt_value(self.admin_password)

    def set_ldap_password(self, plain):
        self.ldap_password = secret_crypto.encrypt_value(plain)

    @property
    def ldap_password_plain(self):
        return secret_crypto.decrypt_value(self.ldap_password) if self.ldap_password else None


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255))  # 本地密码哈希（管理员重置时使用）
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='user')  # 'admin' or 'user'
    domain_id = db.Column(db.Integer, db.ForeignKey('domains.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # AD 用户信息
    ad_dn = db.Column(db.String(255))  # AD 区分名
    ad_email = db.Column(db.String(120))
    ad_display_name = db.Column(db.String(120))
    
    domain = db.relationship('Domain', backref=db.backref('users', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'phone': self.phone,
            'role': self.role,
            'email': self.ad_email,
            'display_name': self.ad_display_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SmsConfig(db.Model):
    __tablename__ = 'sms_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    access_key = db.Column(db.String(100), nullable=False)
    access_secret = db.Column(db.String(100), nullable=False)
    sign_name = db.Column(db.String(50), nullable=False)
    template_code = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'access_key': self.access_key,
            'sign_name': self.sign_name,
            'template_code': self.template_code,
            'is_active': self.is_active,
        }

    def set_access_secret(self, plain):
        self.access_secret = secret_crypto.encrypt_value(plain)

    @property
    def access_secret_plain(self):
        return secret_crypto.decrypt_value(self.access_secret)


class AdminLog(db.Model):
    __tablename__ = 'admin_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    target_user = db.Column(db.String(100))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    admin = db.relationship('User', backref=db.backref('logs', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'admin_id': self.admin_id,
            'action': self.action,
            'target_user': self.target_user,
            'details': self.details,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SmsVerificationCode(db.Model):
    __tablename__ = 'sms_verification_codes'

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), nullable=False, index=True)
    code = db.Column(db.String(255), nullable=False)  # bcrypt 哈希
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    fail_count = db.Column(db.Integer, default=0)
    purpose = db.Column(db.String(30), default='reset')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    setting_value = db.Column(db.Text)
    setting_type = db.Column(db.String(20), default='string')  # string, boolean, integer, json
    description = db.Column(db.String(500))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'setting_key': self.setting_key,
            'setting_value': self.setting_value,
            'setting_type': self.setting_type,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SmsRateLimit(db.Model):
    __tablename__ = 'sms_rate_limits'

    id = db.Column(db.Integer, primary_key=True)
    key_type = db.Column(db.String(20), nullable=False)   # phone|email|ip
    key_value = db.Column(db.String(200), nullable=False)
    sent_count = db.Column(db.Integer, default=0)
    window_start = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('key_type', 'key_value', name='uq_sms_rate_key'),
    )
