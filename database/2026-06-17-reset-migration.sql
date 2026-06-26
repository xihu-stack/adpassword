-- 域控密码自助重置系统迁移
BEGIN;

-- 1. SmsVerificationCode 增字段 + 哈希加长
ALTER TABLE sms_verification_codes
    ADD COLUMN IF NOT EXISTS fail_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS purpose VARCHAR(30) DEFAULT 'reset';
ALTER TABLE sms_verification_codes ALTER COLUMN code TYPE VARCHAR(255);
ALTER TABLE sms_verification_codes ALTER COLUMN user_id DROP NOT NULL;

-- 2. AdminLog.admin_id 可空
ALTER TABLE admin_logs ALTER COLUMN admin_id DROP NOT NULL;

-- 3. 限流表
CREATE TABLE IF NOT EXISTS sms_rate_limits (
    id SERIAL PRIMARY KEY,
    key_type VARCHAR(20) NOT NULL,
    key_value VARCHAR(200) NOT NULL,
    sent_count INTEGER DEFAULT 0,
    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_sms_rate_key UNIQUE (key_type, key_value)
);

-- 4. 移除 MFA 列
ALTER TABLE users DROP COLUMN IF EXISTS mfa_secret;
ALTER TABLE users DROP COLUMN IF EXISTS mfa_enabled;
ALTER TABLE users DROP COLUMN IF EXISTS mfa_bound_at;

-- 5. 保护名单默认（admin / Administrator）
INSERT INTO system_settings (setting_key, setting_value, setting_type, description)
VALUES ('reset_protected_accounts', '["admin", "Administrator"]', 'json', '禁止自助重置的账号')
ON CONFLICT (setting_key) DO NOTHING;

COMMIT;
