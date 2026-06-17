"""
检查当前域配置的详细问题
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from models.models import db, Domain

app = create_app()
with app.app_context():
    print('=' * 60)
    print('检查域配置问题')
    print('=' * 60)
    
    # 获取域配置
    domain = Domain.query.first()
    
    if not domain:
        print('❌ 未找到域配置')
        sys.exit(1)
    
    print(f'\n数据库配置:')
    print(f'  域名：{domain.name}')
    print(f'  LDAP 主机：{domain.ldap_hosts or domain.ldap_host}')
    print(f'  use_ssl: {domain.use_ssl}')
    print(f'  ldap_port: {domain.ldap_port}')
    print(f'  ldaps_port: {domain.ldaps_port}')
    print(f'  Base DN: {domain.base_dn}')
    print(f'  管理员 DN: {domain.admin_dn}')
    
    # 检查主机地址
    host = domain.ldap_hosts if hasattr(domain, 'ldap_hosts') and domain.ldap_hosts else domain.ldap_host
    
    print(f'\n主机地址分析:')
    print(f'  原始值：{repr(host)}')
    print(f'  类型：{"域名" if "." in host and not host.replace(".", "").isdigit() else "IP"}')
    
    # 测试解析
    if '.' in host and not host.replace('.', '').isdigit():
        print(f'\n  尝试 DNS 解析...')
        try:
            import socket
            ip = socket.gethostbyname(host)
            print(f'  ✅ DNS 解析成功：{host} -> {ip}')
        except Exception as e:
            print(f'  ❌ DNS 解析失败：{e}')
            print(f'  💡 可能原因:')
            print(f'     1. DNS 服务器无法访问')
            print(f'     2. 域名不存在')
            print(f'     3. hosts 文件配置错误')
    
    # 测试连接
    print(f'\n' + '=' * 60)
    print(f'测试连接...')
    print(f'=' * 60)
    
    from services.ldap_service import LdapService
    
    config = {
        'ldap_hosts': host,
        'ldap_host': host,
        'ldap_port': domain.ldap_port,
        'ldaps_port': domain.ldaps_port if hasattr(domain, 'ldaps_port') else 636,
        'base_dn': domain.base_dn,
        'admin_dn': domain.admin_dn,
        'admin_password': domain.ldap_password or domain.admin_password,
        'use_ssl': domain.use_ssl if hasattr(domain, 'use_ssl') else False
    }
    
    print(f'\n配置详情:')
    print(f'  ldap_hosts: {config["ldap_hosts"]}')
    print(f'  use_ssl: {config["use_ssl"]}')
    print(f'  ldap_port: {config["ldap_port"]}')
    print(f'  ldaps_port: {config["ldaps_port"]}')
    
    result, message = LdapService.test_connection(config)
    
    print(f'\n连接测试结果:')
    print(f'  {"✅ 成功" if result else "❌ 失败"}')
    print(f'  详细信息：{message}')
    
    if not result:
        print(f'\n💡 排查建议:')
        if 'invalid server address' in message.lower():
            print(f'  1. 主机地址格式错误，检查是否有空格或特殊字符')
            print(f'  2. 如果是域名，检查 DNS 解析')
            print(f'  3. 尝试使用 IP 地址代替域名')
        elif 'certificate' in message.lower() or 'ssl' in message.lower():
            print(f'  1. SSL 证书问题')
            print(f'  2. 尝试使用 LDAP (端口 389) 而不是 LDAPS')
