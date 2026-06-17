-- 数据库迁移脚本：添加 ldap_hosts 字段支持多主机配置
-- 执行方式：psql -U postgres -d ad_password_manager -f add_ldap_hosts_column.sql

-- 添加 ldap_hosts 字段
ALTER TABLE domains ADD COLUMN IF NOT EXISTS ldap_hosts VARCHAR(500);

-- 将现有的 ldap_host 数据复制到 ldap_hosts
UPDATE domains SET ldap_hosts = ldap_host WHERE ldap_hosts IS NULL AND ldap_host IS NOT NULL;

-- 输出迁移结果
SELECT name, ldap_host, ldap_hosts FROM domains;

-- 提示
SELECT '✅ 迁移完成！ldap_hosts 字段已添加，数据已同步' AS migration_status;
