"""
实时监控域配置变化
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from models.models import db, Domain

app = create_app()

print('=' * 60)
print('监控域配置变化 (按 Ctrl+C 停止)')
print('=' * 60)

last_config = None

try:
    while True:
        with app.app_context():
            domain = Domain.query.first()
            if domain:
                current_config = {
                    'name': domain.name,
                    'ldap_hosts': domain.ldap_hosts if hasattr(domain, 'ldap_hosts') else domain.ldap_host,
                    'ldap_host': domain.ldap_host,
                    'use_ssl': domain.use_ssl if hasattr(domain, 'use_ssl') else False,
                    'ldap_port': domain.ldap_port,
                }
                
                if last_config != current_config:
                    print(f'\n[{time.strftime("%H:%M:%S")}] 配置已更新!')
                    print(f'  域名：{current_config["name"]}')
                    print(f'  LDAP 主机：{current_config["ldap_hosts"]}')
                    print(f'  use_ssl: {current_config["use_ssl"]}')
                    print(f'  ldap_port: {current_config["ldap_port"]}')
                    print('-' * 60)
                    last_config = current_config
            else:
                print(f'[{time.strftime("%H:%M:%S")}] 未找到域配置')
        
        time.sleep(2)
        
except KeyboardInterrupt:
    print('\n\n监控已停止')
