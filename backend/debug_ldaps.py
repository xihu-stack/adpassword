"""
调试 LDAPS 连接问题
添加详细日志
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from models.models import db, Domain
from services.ldap_service import LdapService

app = create_app()
with app.app_context():
    print('=' * 60)
    print('调试 LDAPS 连接问题')
    print('=' * 60)
    
    # 获取域配置
    domain = Domain.query.first()
    
    if not domain:
        print('❌ 未找到域配置')
        sys.exit(1)
    
    print(f'\n域：{domain.name}')
    print(f'LDAP 主机：{domain.ldap_hosts or domain.ldap_host}')
    print(f'use_ssl: {domain.use_ssl}')
    print(f'ldap_port: {domain.ldap_port}')
    print(f'ldaps_port: {domain.ldaps_port}')
    
    # 构建配置 (模拟前端发送的数据)
    config = {
        'ldap_hosts': domain.ldap_hosts if hasattr(domain, 'ldap_hosts') else domain.ldap_host,
        'ldap_host': domain.ldap_host,
        'ldap_port': domain.ldap_port,
        'ldaps_port': domain.ldaps_port if hasattr(domain, 'ldaps_port') else 636,
        'base_dn': domain.base_dn,
        'admin_dn': domain.admin_dn,
        'admin_password': domain.ldap_password or domain.admin_password,
        'use_ssl': domain.use_ssl if hasattr(domain, 'use_ssl') else False
    }
    
    print('\n' + '=' * 60)
    print('配置详情:')
    print('=' * 60)
    for key, value in config.items():
        if key == 'admin_password':
            print(f'  {key}: {"*" * len(value) if value else "None"}')
        else:
            print(f'  {key}: {value}')
    
    print('\n' + '=' * 60)
    print('开始测试连接...')
    print('=' * 60)
    
    # 测试连接
    result, message = LdapService.test_connection(config)
    
    print('\n' + '=' * 60)
    if result:
        print(f'✅ 连接成功!')
        print(f'详细信息：{message}')
    else:
        print(f'❌ 连接失败!')
        print(f'错误信息：{message}')
        
        # 详细分析
        print('\n' + '=' * 60)
        print('错误分析:')
        print('=' * 60)
        
        if 'invalid server address' in message.lower():
            print('❌ 服务器地址格式错误')
            print('可能原因:')
            print('  1. LDAP 主机地址包含空格或特殊字符')
            print('  2. 端口配置错误')
            print('  3. 协议与端口不匹配')
        elif 'certificate' in message.lower() or 'ssl' in message.lower():
            print('❌ SSL 证书问题')
            print('可能原因:')
            print('  1. SSL 证书验证失败')
            print('  2. 自签名证书未受信任')
            print('  3. TLS 配置不正确')
        elif 'connection' in message.lower() or 'receiving data' in message.lower():
            print('❌ 网络连接问题')
            print('可能原因:')
            print('  1. 服务器未运行')
            print('  2. 防火墙阻止连接')
            print('  3. 网络不可达')
            print('  4. 协议与端口不匹配 (LDAP 用 389, LDAPS 用 636)')
        elif '10054' in message:
            print('❌ WinError 10054 - 远程主机关闭连接')
            print('可能原因:')
            print('  1. 服务器拒绝该类型的连接')
            print('  2. 协议与端口不匹配')
            print('  3. 防火墙或安全策略阻止')
    
    print('=' * 60)
