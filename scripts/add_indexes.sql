-- =============================================
-- 数据库索引优化脚本
-- 用于生产环境性能优化
-- =============================================

-- 1. 用户表索引
PRINT '创建用户表索引...';

CREATE INDEX IF NOT EXISTS idx_user_username 
ON users(username);

CREATE INDEX IF NOT EXISTS idx_user_mfa_enabled 
ON users(mfa_enabled);

CREATE INDEX IF NOT EXISTS idx_user_created_at 
ON users(created_at);

CREATE INDEX IF NOT EXISTS idx_user_updated_at 
ON users(updated_at);

-- 2. 日志表索引
PRINT '创建日志表索引...';

CREATE INDEX IF NOT EXISTS idx_log_timestamp 
ON operation_logs(timestamp);

CREATE INDEX IF NOT EXISTS idx_log_operation 
ON operation_logs(operation_type);

CREATE INDEX IF NOT EXISTS idx_log_user 
ON operation_logs(target_user);

CREATE INDEX IF NOT EXISTS idx_log_details 
ON operation_logs(details);

-- 3. 域配置表索引
PRINT '创建域配置表索引...';

CREATE INDEX IF NOT EXISTS idx_domain_active 
ON domains(is_active);

CREATE INDEX IF NOT EXISTS idx_domain_name 
ON domains(name);

-- 4. 显示索引统计
PRINT '索引创建完成！';

SELECT 
    '用户表索引' AS table_name,
    COUNT(*) AS index_count
FROM sys.indexes i
JOIN sys.tables t ON i.object_id = t.object_id
WHERE t.name = 'users'
UNION ALL
SELECT 
    '日志表索引' AS table_name,
    COUNT(*) AS index_count
FROM sys.indexes i
JOIN sys.tables t ON i.object_id = t.object_id
WHERE t.name = 'operation_logs'
UNION ALL
SELECT 
    '域配置表索引' AS table_name,
    COUNT(*) AS index_count
FROM sys.indexes i
JOIN sys.tables t ON i.object_id = t.object_id
WHERE t.name = 'domains';
