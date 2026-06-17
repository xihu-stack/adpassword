"""
数据库迁移脚本：添加 ldap_hosts 字段支持多主机配置
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from models.models import db, Domain

def migrate_add_ldap_hosts_field():
    """添加 ldap_hosts 字段"""
    
    # 在应用上下文中执行
    app = create_app()
    with app.app_context():
        print('=' * 60)
        print('数据库迁移：添加 ldap_hosts 字段')
        print('=' * 60)
        
        try:
            # 检查字段是否已存在
            domain = Domain.query.first()
            if not domain:
                print('✅ 数据库为空，无需迁移，新配置已包含 ldap_hosts 字段')
                return
            
            if hasattr(domain, 'ldap_hosts'):
                print('✅ ldap_hosts 字段已存在，无需迁移')
                return
            
            print('📋 开始迁移...')
            
            # 获取所有域配置
            domains = Domain.query.all()
            print(f'📋 找到 {len(domains)} 个域配置')
            
            # 更新每个域
            for domain in domains:
                print(f'\n处理域：{domain.name}')
                print(f'  原 ldap_host: {domain.ldap_host}')
                
                # 将 ldap_host 复制到 ldap_hosts
                # 注意：由于 models.py 已修改，ldap_hosts 字段应该已经存在
                # 这里只是为了确保数据一致性
                if hasattr(domain, 'ldap_hosts'):
                    if not domain.ldap_hosts and domain.ldap_host:
                        domain.ldap_hosts = domain.ldap_host
                        print(f'  ✅ 已同步到 ldap_hosts: {domain.ldap_hosts}')
                    elif domain.ldap_hosts:
                        print(f'  ✅ ldap_hosts 已配置：{domain.ldap_hosts}')
                    else:
                        print(f'  ⚠️  警告：ldap_host 和 ldap_hosts 都为空')
                else:
                    print(f'  ⚠️  警告：Domain 模型没有 ldap_hosts 字段，请先更新 models.py')
            
            # 提交更改
            db.session.commit()
            print('\n✅ 迁移完成!')
            
        except Exception as e:
            db.session.rollback()
            print(f'\n❌ 迁移失败：{str(e)}')
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    migrate_add_ldap_hosts_field()
