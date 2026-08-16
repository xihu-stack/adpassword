-- ============================================================
-- 2026-08-16 迁移：加宽凭据/审计字段长度
-- ------------------------------------------------------------
-- 背景：Fernet 加密 token 约 140+ 字符（随明文长度增长）。
--   sms_configs.access_secret VARCHAR(100)  → 阿里云 Secret（约30字符）
--   加密后约 140 字符，在 PostgreSQL 下保存必报错、MySQL 非严格模式截断。
--   admin_logs.target_user VARCHAR(100)     → 公开重置页提交的邮箱长度
--   不可控，超长会导致审计写入失败且被静默吞掉。
--
-- 适用：PostgreSQL / MySQL。SQLite（默认部署）不校验长度，无需执行，
--   但 SQLAlchemy 模型已同步加宽，新库自动是宽列。
-- 执行前请先备份数据库。
-- ============================================================

-- PostgreSQL
ALTER TABLE sms_configs ALTER COLUMN access_secret TYPE VARCHAR(500);
ALTER TABLE domains      ALTER COLUMN admin_password TYPE VARCHAR(500);
ALTER TABLE domains      ALTER COLUMN ldap_password  TYPE VARCHAR(500);
ALTER TABLE admin_logs   ALTER COLUMN target_user    TYPE VARCHAR(255);

-- MySQL 版本（如使用 MySQL 请注释掉上面 PostgreSQL 段，改用下面）：
-- ALTER TABLE sms_configs MODIFY access_secret VARCHAR(500) NOT NULL;
-- ALTER TABLE domains      MODIFY admin_password VARCHAR(500) NOT NULL;
-- ALTER TABLE domains      MODIFY ldap_password  VARCHAR(500);
-- ALTER TABLE admin_logs   MODIFY target_user    VARCHAR(255);
