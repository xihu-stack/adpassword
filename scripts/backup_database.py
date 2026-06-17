#!/usr/bin/env python3
"""
数据库备份脚本
用于生产环境迁移前备份数据
"""

import os
import sys
from datetime import datetime

# 配置
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
DB_TYPE = 'sqlite'  # 支持：sqlite, postgresql, mysql
DB_PATH = 'backend/instance/ad_password.db'  # SQLite 数据库路径

# PostgreSQL 配置（如果使用）
# DB_TYPE = 'postgresql'
# DB_HOST = 'localhost'
# DB_PORT = '5432'
# DB_NAME = 'ad_password_db'
# DB_USER = 'postgres'
# DB_PASSWORD = 'your_password'

def create_backup_dir():
    """创建备份目录"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"✓ 创建备份目录：{BACKUP_DIR}")

def backup_sqlite():
    """备份 SQLite 数据库"""
    import shutil
    
    if not os.path.exists(DB_PATH):
        print(f"❌ 数据库文件不存在：{DB_PATH}")
        return None
    
    # 生成备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'ad_password_backup_{timestamp}.db'
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    # 复制文件
    shutil.copy2(DB_PATH, backup_path)
    
    print(f"✓ SQLite 数据库已备份")
    print(f"  源文件：{DB_PATH}")
    print(f"  备份文件：{backup_path}")
    
    return backup_path

def backup_postgresql():
    """备份 PostgreSQL 数据库"""
    import subprocess
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'ad_password_backup_{timestamp}.sql'
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    # 设置环境变量
    env = os.environ.copy()
    env['PGPASSWORD'] = DB_PASSWORD
    
    # 执行 pg_dump
    cmd = [
        'pg_dump',
        '-h', DB_HOST,
        '-p', DB_PORT,
        '-U', DB_USER,
        '-d', DB_NAME,
        '-f', backup_path
    ]
    
    try:
        subprocess.run(cmd, env=env, check=True)
        print(f"✓ PostgreSQL 数据库已备份")
        print(f"  备份文件：{backup_path}")
        return backup_path
    except subprocess.CalledProcessError as e:
        print(f"❌ 备份失败：{e}")
        return None

def main():
    print("="*60)
    print("  数据库备份脚本")
    print("="*60)
    print()
    
    # 创建备份目录
    create_backup_dir()
    
    # 根据数据库类型执行备份
    if DB_TYPE == 'sqlite':
        backup_path = backup_sqlite()
    elif DB_TYPE == 'postgresql':
        backup_path = backup_postgresql()
    else:
        print(f"❌ 不支持的数据库类型：{DB_TYPE}")
        return 1
    
    if backup_path:
        print()
        print("="*60)
        print("✅ 备份完成！")
        print("="*60)
        print()
        print("📦 备份文件信息:")
        print(f"   文件路径：{backup_path}")
        print(f"   文件大小：{os.path.getsize(backup_path) / 1024:.2f} KB")
        print()
        print("⚠️  建议:")
        print("   1. 将备份文件复制到安全位置")
        print("   2. 定期清理旧备份文件")
        print("   3. 测试备份恢复流程")
        print()
        return 0
    else:
        print()
        print("="*60)
        print("❌ 备份失败！")
        print("="*60)
        return 1

if __name__ == '__main__':
    sys.exit(main())
