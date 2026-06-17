"""
执行数据库迁移：添加 ldap_hosts 字段
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from models.models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print('=' * 60)
    print('执行数据库迁移：添加 ldap_hosts 字段')
    print('=' * 60)
    
    try:
        # 执行 SQL 迁移
        with db.engine.connect() as conn:
            # 1. 添加字段
            print('\n1️⃣ 添加 ldap_hosts 字段...')
            conn.execute(text('ALTER TABLE domains ADD COLUMN IF NOT EXISTS ldap_hosts VARCHAR(500)'))
            print('   ✅ ldap_hosts 字段已添加')
            
            # 2. 同步数据
            print('\n2️⃣ 同步现有数据到 ldap_hosts...')
            conn.execute(text('UPDATE domains SET ldap_hosts = ldap_host WHERE ldap_hosts IS NULL AND ldap_host IS NOT NULL'))
            print('   ✅ 数据已同步')
            
            # 3. 提交事务
            conn.commit()
            print('\n3️⃣ 提交事务...')
            print('   ✅ 事务已提交')
            
            # 4. 验证结果
            print('\n4️⃣ 验证迁移结果...')
            result = conn.execute(text('SELECT name, ldap_host, ldap_hosts FROM domains'))
            rows = result.fetchall()
            
            if rows:
                print(f'\n📊 找到 {len(rows)} 个域配置:')
                for row in rows:
                    print(f'  - {row.name}:')
                    print(f'    ldap_host: {row.ldap_host}')
                    print(f'    ldap_hosts: {row.ldap_hosts}')
            else:
                print('  ⚠️  数据库中暂无域配置')
            
            print('\n' + '=' * 60)
            print('✅ 迁移完成!')
            print('=' * 60)
            
    except Exception as e:
        print(f'\n❌ 迁移失败：{str(e)}')
        import traceback
        traceback.print_exc()
