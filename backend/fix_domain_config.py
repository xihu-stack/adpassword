"""
修复域配置问题
自动修正端口和 SSL 配置不匹配的问题
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from models.models import db, Domain

app = create_app()
with app.app_context():
    print('=' * 60)
    print('修复域配置问题')
    print('=' * 60)
    
    # 获取所有域配置
    domains = Domain.query.all()
    
    for domain in domains:
        print(f'\n处理域：{domain.name}')
        print(f'  当前配置:')
        print(f'    ldap_hosts: {domain.ldap_hosts}')
        print(f'    use_ssl: {domain.use_ssl}')
        print(f'    ldap_port: {domain.ldap_port}')
        print(f'    ldaps_port: {domain.ldaps_port}')
        
        # 检查并修复配置
        need_fix = False
        
        # 问题 1: 端口 636 但未启用 SSL
        if domain.ldap_port == 636 and not domain.use_ssl:
            print(f'\n  ⚠️  问题：端口 636 但未启用 SSL')
            fix_choice = input('  修复方案:\n    1. 将端口改为 389 (LDAP)\n    2. 启用 SSL (LDAPS)\n    选择 (1/2): ')
            
            if fix_choice == '1':
                domain.ldap_port = 389
                print(f'  ✅ 已将 LDAP 端口改为 389')
                need_fix = True
            elif fix_choice == '2':
                domain.use_ssl = True
                print(f'  ✅ 已启用 SSL 加密')
                need_fix = True
            else:
                print(f'  ⚠️  未做修改')
        
        # 问题 2: 启用 SSL 但端口是 389
        elif domain.use_ssl and domain.ldap_port == 389:
            print(f'\n  ⚠️  问题：启用 SSL 但端口是 389')
            fix_choice = input('  修复方案:\n    1. 将 LDAP 端口改为 636\n    2. 关闭 SSL\n    选择 (1/2): ')
            
            if fix_choice == '1':
                domain.ldap_port = 636
                print(f'  ✅ 已将 LDAP 端口改为 636')
                need_fix = True
            elif fix_choice == '2':
                domain.use_ssl = False
                print(f'  ✅ 已关闭 SSL 加密')
                need_fix = True
            else:
                print(f'  ⚠️  未做修改')
        
        if need_fix:
            # 提交更改
            db.session.commit()
            print(f'\n  ✅ 配置已更新并提交')
        else:
            print(f'\n  ✅ 配置正确，无需修复')
    
    print('\n' + '=' * 60)
    print('修复完成!')
    print('=' * 60)
