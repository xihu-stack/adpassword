-- AD 密码管理系统数据库初始化脚本
-- PostgreSQL

-- 连接到数据库 ad（如果不存在，请先创建）
-- 创建数据库命令：CREATE DATABASE ad OWNER postgres;
\c ad;

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    phone VARCHAR(20),
    role VARCHAR(20) DEFAULT 'user',
    domain_id INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    ad_dn VARCHAR(255),
    ad_email VARCHAR(120),
    ad_display_name VARCHAR(120),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);

-- 域配置表
CREATE TABLE IF NOT EXISTS domains (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    ldap_host VARCHAR(200) NOT NULL,
    ldap_port INTEGER DEFAULT 389,
    ldaps_port INTEGER DEFAULT 636,
    base_dn VARCHAR(255) NOT NULL,
    admin_dn VARCHAR(255) NOT NULL,
    admin_password VARCHAR(255) NOT NULL,
    use_ssl BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 短信配置表
CREATE TABLE IF NOT EXISTS sms_configs (
    id SERIAL PRIMARY KEY,
    access_key VARCHAR(100) NOT NULL,
    access_secret VARCHAR(100) NOT NULL,
    sign_name VARCHAR(50) NOT NULL,
    template_code VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 管理日志表
CREATE TABLE IF NOT EXISTS admin_logs (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    target_user VARCHAR(100),
    details TEXT,
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_admin_logs_created_at ON admin_logs(created_at);

-- 短信验证码表（code 存 bcrypt 哈希，需 VARCHAR(255)）
CREATE TABLE IF NOT EXISTS sms_verification_codes (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20) NOT NULL,
    code VARCHAR(255) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    is_used BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP NOT NULL,
    fail_count INTEGER DEFAULT 0,
    purpose VARCHAR(30) DEFAULT 'reset',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sms_verification_phone ON sms_verification_codes(phone);
CREATE INDEX idx_sms_verification_used ON sms_verification_codes(is_used);

-- 短信发送限流表
CREATE TABLE IF NOT EXISTS sms_rate_limits (
    id SERIAL PRIMARY KEY,
    key_type VARCHAR(20) NOT NULL,        -- phone|email|ip
    key_value VARCHAR(200) NOT NULL,
    sent_count INTEGER DEFAULT 0,
    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_sms_rate_key UNIQUE (key_type, key_value)
);

-- 系统设置表（保护名单等）
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type VARCHAR(20) DEFAULT 'string',
    description VARCHAR(500),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(setting_key);

-- 保护名单默认（admin / Administrator）
INSERT INTO system_settings (setting_key, setting_value, setting_type, description)
VALUES ('reset_protected_accounts', '["admin", "Administrator"]', 'json', '禁止自助重置的账号')
ON CONFLICT (setting_key) DO NOTHING;

-- 插入默认管理员账号（密码：admin）
-- 注意：实际密码会在应用启动时使用 bcrypt 加密
INSERT INTO users (username, password_hash, role, is_active)
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS3MebAJu', 'admin', TRUE)
ON CONFLICT (username) DO NOTHING;

-- 添加外键约束
ALTER TABLE users ADD CONSTRAINT fk_users_domain 
    FOREIGN KEY (domain_id) REFERENCES domains(id) ON DELETE SET NULL;

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为各表添加更新时间触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_domains_updated_at BEFORE UPDATE ON domains
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sms_configs_updated_at BEFORE UPDATE ON sms_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE users IS '用户信息表';
COMMENT ON TABLE domains IS 'AD 域配置表';
COMMENT ON TABLE sms_configs IS '短信服务配置表';
COMMENT ON TABLE admin_logs IS '管理员操作日志';
COMMENT ON TABLE sms_verification_codes IS '短信验证码记录';
