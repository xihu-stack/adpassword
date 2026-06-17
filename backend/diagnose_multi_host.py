"""
诊断多主机配置问题
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from models.models import db, Domain

app = create_app()
with app.app_context():
    print('=' * 60)
    print('诊断 LDAP 多主机配置')
    print('=' * 60)
    
    # 获取所有域配置
    domains = Domain.query.all()
    
    for domain in domains:
        print(f'\n域：{domain.name}')
        print(f'  ID: {domain.id}')
        print(f'  ldap_hosts 字段：{repr(domain.ldap_hosts)}')
        print(f'  ldap_host 字段：{repr(domain.ldap_host)}')
        print(f'  use_ssl: {domain.use_ssl}')
        print(f'  ldap_port: {domain.ldap_port}')
        print(f'  ldaps_port: {domain.ldaps_port}')
        print(f'  base_dn: {domain.base_dn}')
        print(f'  admin_dn: {domain.admin_dn}')
        
        # 测试解析
        hosts_str = domain.ldap_hosts if hasattr(domain, 'ldap_hosts') and domain.ldap_hosts else domain.ldap_host
        print(f'\n  解析主机地址:')
        print(f'    原始字符串：{repr(hosts_str)}')
        
        if hosts_str:
            hosts = [h.strip() for h in hosts_str.replace(';', ',').split(',') if h.strip()]
            print(f'    解析结果：{hosts}')
            print(f'    主机数量：{len(hosts)}')
            
            for i, host in enumerate(hosts, 1):
                protocol = 'ldaps' if domain.use_ssl else 'ldap'
                port = domain.ldaps_port if domain.use_ssl else domain.ldap_port
                server_url = f"{protocol}://{host}:{port}"
                print(f'    服务器 {i}: {server_url}')
        else:
            print(f'    ❌ 未配置主机地址')
