"""
手动修复 LDAPS 配置
将配置改为正确的 LDAPS 模式
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from models.models import db, Domain

app = create_app()
with app.app_context():
    print('=' * 60)
    print('手动修复 LDAPS 配置')
    print('=' * 60)
    
    # 获取域配置
    domain = Domain.query.first()
    
    if not domain:
        print('❌ 未找到域配置')
        sys.exit(1)
    
    print(f'\n当前配置:')
    print(f'  域名：{domain.name}')
    print(f'  LDAP 主机：{domain.ldap_hosts or domain.ldap_host}')
    print(f'  use_ssl: {domain.use_ssl}')
    print(f'  ldap_port: {domain.ldap_port}')
    print(f'  ldaps_port: {domain.ldaps_port}')
    
    # 修复配置
    print('\n' + '=' * 60)
    print('修复为 LDAPS 模式 (SSL 加密):')
    print('=' * 60)
    
    domain.use_ssl = True
    domain.ldap_port = 636  # LDAPS 端口
    domain.ldaps_port = 636
    
    print(f'  ✅ use_ssl = True')
    print(f'  ✅ ldap_port = 636')
    print(f'  ✅ ldaps_port = 636')
    
    # 提交更改
    db.session.commit()
    
    print('\n✅ 配置已更新并提交!')
    
    # 验证
    print('\n新配置:')
    print(f'  域名：{domain.name}')
    print(f'  LDAP 主机：{domain.ldap_hosts or domain.ldap_host}')
    print(f'  use_ssl: {domain.use_ssl}')
    print(f'  ldap_port: {domain.ldap_port}')
    print(f'  ldaps_port: {domain.ldaps_port}')
    
    print('\n' + '=' * 60)
    print('现在可以测试连接了!')
    print('=' * 60)
