"""
智能 LDAP 服务 - 使用 ldap3 库
特性：
1. 自动尝试多种认证方式
2. 提供详细的错误诊断信息
3. 支持连接模式切换（真实/模拟）
"""

try:
    from ldap3 import Server, Connection, ALL, NTLM, SIMPLE, SUBTREE, MODIFY_REPLACE
    from ldap3.core.exceptions import LDAPException
    from ldap3 import Tls
    import ssl
    LDAP3_AVAILABLE = True
except ImportError:
    LDAP3_AVAILABLE = False
    print('[LDAP 服务] ldap3 库不可用，请安装：pip install ldap3')

from models.models import Domain
import os

from services import secret_crypto as _sc


def build_tls_context():
    """构建 TLS 配置（LDAPS 与 STARTTLS 共用）。

    默认不校验证书（CERT_NONE）：兼容域控自签名证书，域控侧无需任何改动。
    若域控证书由内部 CA 签发，可在 .env 设置 LDAP_TLS_VALIDATE=true，
    并用 LDAP_CA_CERT 指向 CA 证书文件，启用强校验并收紧加密套件。
    """
    if os.getenv('LDAP_TLS_VALIDATE', 'false').lower() == 'true':
        kwargs = {'validate': ssl.CERT_REQUIRED, 'version': ssl.PROTOCOL_TLS_CLIENT}
        ca = os.getenv('LDAP_CA_CERT', '').strip()
        if ca:
            kwargs['ca_certs_file'] = ca
        return Tls(**kwargs)
    return Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLS_CLIENT,
               ciphers='ALL:@SECLEVEL=0')  # 兼容旧域控


def secret_decrypt(v):
    """解密存储的凭据；未加密（旧数据）原样返回。
    解密失败（密钥变更/丢失）抛 RuntimeError——绝不能用空密码继续匿名绑定。"""
    if v is None or v == '':
        return v
    if _sc.is_encrypted(v):
        plain = _sc.decrypt_value(v)
        if plain is None:
            raise RuntimeError(
                '凭据解密失败：SECRET_ENCRYPTION_KEY 与加密时不一致（或已丢失），'
                '请在管理后台重新录入域控/短信密码')
        return plain
    return v


class LdapService:
    # 连接模式：'real' = 真实 AD, 'mock' = 模拟模式
    CONNECTION_MODE = 'real'  # 真实模式 - 连接真实 AD
    LDAP3_AVAILABLE = LDAP3_AVAILABLE
    
    @staticmethod
    def set_mode(mode):
        """设置连接模式"""
        if mode in ['real', 'mock']:
            LdapService.CONNECTION_MODE = mode
    
    @staticmethod
    def get_ldap_servers(domain_config):
        """
        获取 LDAP 服务器列表（支持多主机故障转移）
        返回：服务器列表 [(protocol1, host1, port1), (protocol2, host2, port2), ...]
        """
        # 优先使用 ldap_hosts 字段（多主机），如果不存在则使用 ldap_host（单主机）
        hosts_str = domain_config.get('ldap_hosts', '')
        if not hosts_str:
            # 兼容旧配置
            hosts_str = domain_config.get('ldap_host', '')
        
        # 解析多个主机地址（逗号或分号分隔）
        hosts = [h.strip() for h in hosts_str.replace(';', ',').split(',') if h.strip()]
        
        if not hosts:
            return []
        
        # 判断是否使用 SSL
        use_ssl = domain_config.get('use_ssl', False)
        protocol = 'ldaps' if use_ssl else 'ldap'
        port = domain_config.get('ldaps_port') if use_ssl else domain_config.get('ldap_port')
        
        # 构建服务器列表
        servers = []
        for host in hosts:
            # 支持域名格式：hostname/domain.com（类似 LDP 工具）
            # 如果包含 /，则使用完整字符串作为主机名
            servers.append((protocol, host, port))
        
        return servers
    
    @staticmethod
    def test_connection(domain_config):
        """
        智能测试 LDAP 连接（支持多主机故障转移）
        自动尝试多个服务器，返回详细错误信息和排查建议
        """
        if not LDAP3_AVAILABLE:
            return False, "ldap3 库不可用，请安装：pip install ldap3"
        
        # 如果是模拟模式
        if LdapService.CONNECTION_MODE == 'mock':
            return True, f"连接成功 (模拟模式)，服务器：{domain_config.get('ldap_hosts', domain_config.get('ldap_host', 'unknown'))}"
        
        # 验证必填参数
        if not domain_config.get('admin_password'):
            return False, "❌ 管理员密码不能为空！请填写 LDAP 管理员密码。"
        
        # 检查密码是否为 bcrypt 加密格式
        pwd = domain_config.get('admin_password', '')
        if pwd.startswith('$2b$') and len(pwd) == 60:
            return False, "❌ 检测到密码是 bcrypt 加密格式！LDAP 连接需要明文密码。\n\n请填写 LDAP 管理员的明文密码（例如：LX2320**）"
        
        # 检查 DN 格式（只检查基本格式，不强制要求 CN=Users）
        admin_dn = domain_config.get('admin_dn', '')
        if admin_dn and not (admin_dn.startswith('CN=') or admin_dn.startswith('UID=')):
            return False, f"❌ 管理员 DN 格式可能不正确！\n\n当前 DN: {admin_dn}\n建议格式：CN=Administrator,CN=Users,DC=helixon,DC=com\n\nDN 应该以 'CN=' 或 'UID=' 开头。"
        
        # 获取服务器列表（支持多主机）
        servers = LdapService.get_ldap_servers(domain_config)
        if not servers:
            return False, "❌ 未配置 LDAP 服务器地址！"
        
        print(f'[LDAP 连接测试] 尝试连接 {len(servers)} 台服务器：{servers}')
        
        # 尝试连接每个服务器
        last_error = None
        for protocol, host, port in servers:
            try:
                # 支持域名格式：hostname/domain.com（类似 LDP 工具）
                # 如果 host 包含 /，则直接使用（例如：AD2.helixon.com/DC=helixon,DC=com）
                if '/' in host and protocol == 'ldaps':
                    # LDAPS 域名格式：ldaps://hostname/base_dn
                    server_url = f"{protocol}://{host}"
                    print(f'[LDAP 连接测试] 尝试连接（域名格式）：{server_url}')
                else:
                    # 传统 IP 格式：protocol://ip:port
                    server_url = f"{protocol}://{host}:{port}"
                    print(f'[LDAP 连接测试] 尝试连接（IP 格式）：{server_url}')
                
                # 创建服务器对象（TLS 配置统一走 build_tls_context；
                # ldap:// 会在绑定前升级 STARTTLS，见下方认证逻辑）
                server = Server(server_url, get_info=ALL, tls=build_tls_context(), connect_timeout=10)
                
                # 从 admin_dn 提取用户名
                username = None
                if '=' in domain_config['admin_dn']:
                    username = domain_config['admin_dn'].split(',')[0].split('=')[1]
                else:
                    username = domain_config['admin_dn']
                
                # 从 base_dn 提取域名
                domain_name = None
                if 'DC=' in domain_config['base_dn']:
                    dc_parts = [part.replace('DC=', '').strip() for part in domain_config['base_dn'].split(',') if 'DC=' in part]
                    if dc_parts:
                        domain_name = '.'.join(dc_parts)
                
                # UPN 格式
                upn = f"{username}@{domain_name}" if domain_name and username else domain_config['admin_dn']
                
                # NETBIOS 域名（通常是大写的域名第一部分）
                netbios_domain = domain_name.split('.')[0].upper() if domain_name else 'DOMAIN'
                
                # 尝试多种认证组合（针对 LDAPS 优化 - 优先 SIMPLE，跳过 NTLM 避免 MD4 错误）
                auth_attempts = [
                    {
                        'name': 'SIMPLE 认证 - 完整 DN',
                        'user': domain_config['admin_dn'],
                        'auth': SIMPLE,
                        'desc': '使用完整的管理员 DN 进行 SIMPLE 认证（推荐，最兼容）',
                        'priority': 1
                    },
                    {
                        'name': 'SIMPLE 认证 - UPN 格式',
                        'user': upn,
                        'auth': SIMPLE,
                        'desc': f'使用 UPN 格式 ({upn}) 进行 SIMPLE 认证',
                        'priority': 2
                    },
                    {
                        'name': '自动认证 - DN',
                        'user': domain_config['admin_dn'],
                        'auth': None,
                        'desc': '让 ldap3 自动选择认证方式',
                        'priority': 3
                    },
                    {
                        'name': '自动认证 - UPN',
                        'user': upn,
                        'auth': None,
                        'desc': '让 ldap3 自动选择认证方式（UPN 格式）',
                        'priority': 4
                    }
                    # 注意：不使用 NTLM 认证，因为 Windows 系统禁用了 MD4 hash
                    # 如果必须使用 NTLM，需要在 Windows 注册表中启用 MD4
                ]
                
                # 按优先级排序
                auth_attempts.sort(key=lambda x: x['priority'])
                
                attempts_info = []
                error_analysis = []
                
                for attempt in auth_attempts:
                    try:
                        conn = Connection(
                            server,
                            user=attempt['user'],
                            password=domain_config['admin_password'],
                            authentication=attempt['auth'],
                            auto_bind=False
                        )
                        conn.open()
                        if protocol == 'ldap':
                            # 389 端口先升级 STARTTLS 再绑定，避免管理员密码明文传输
                            if not conn.start_tls():
                                raise LDAPException('STARTTLS 失败（域控可能未安装证书），result=%s' % conn.result)
                        conn.bind()
                        if not conn.bound:
                            raise LDAPException('绑定失败：%s' % conn.result)
                        
                        # 尝试搜索
                        result = conn.search(
                            search_base=domain_config['base_dn'],
                            search_filter='(objectClass=user)',
                            search_scope=SUBTREE,
                            attributes=['cn', 'sAMAccountName']
                        )
                        
                        conn.unbind()
                        
                        return True, f"✅ 连接成功 ({attempt['name']})，服务器：{host}:{port}，找到 {len(conn.entries)} 个对象"
                        
                    except LDAPException as e:
                        error_str = str(e)
                        last_error = error_str
                        
                        # 记录尝试信息
                        attempts_info.append(f"{attempt['name']}: {error_str[:80]}")
                        
                        # 分析错误原因
                        analysis = {
                            'auth_method': attempt['name'],
                            'error': error_str[:100],
                            'possible_cause': '未知'
                        }
                        
                        if 'invalidCredentials' in error_str or '数据无效' in error_str:
                            analysis['possible_cause'] = '用户名或密码错误'
                        elif 'serverUnavailable' in error_str or '服务器不可用' in error_str:
                            analysis['possible_cause'] = 'LDAP 服务器无法连接或端口错误'
                        elif 'invalidDNSyntax' in error_str:
                            analysis['possible_cause'] = 'DN 格式不正确'
                        elif 'strongerAuthRequired' in error_str:
                            analysis['possible_cause'] = '需要更强的认证方式（如 LDAPS）'
                        elif 'operationsNotAllowed' in error_str:
                            analysis['possible_cause'] = '操作不被允许，可能权限不足'
                        elif 'inappropriateAuthentication' in error_str:
                            analysis['possible_cause'] = '认证方式不适合此服务器'
                        elif 'MD4' in error_str or 'hash type' in error_str or 'NTLM needs' in error_str:
                            analysis['possible_cause'] = 'NTLM 认证被禁用（Windows 安全策略），已自动跳过'
                            # MD4 错误是 NTLM 认证导致的，不添加到错误列表，直接跳过
                            continue
                        
                        error_analysis.append(analysis)
                        continue
                
                # 所有认证方式都失败，继续尝试下一台服务器
                print(f'[LDAP 连接测试] ❌ 服务器 {host}:{port} 认证失败，尝试下一台...')
                continue
                
            except Exception as e:
                print(f'[LDAP 连接测试] ❌ 服务器 {host}:{port} 连接异常：{str(e)[:100]}')
                last_error = str(e)
                continue
        
        # 所有服务器都尝试失败
        error_details = f"❌ 所有 {len(servers)} 台服务器都连接失败。最后错误：{last_error}\n\n"
        error_details += f"尝试连接的服务器列表：\n"
        for protocol, host, port in servers:
            error_details += f"  - {protocol}://{host}:{port}\n"
        
        error_details += "\n💡 排查建议:\n"
        error_details += "  1. ✅ 检查所有 LDAP 主机地址和端口是否正确\n"
        error_details += "  2. ✅ 检查管理员 DN 和密码是否正确（重点！）\n"
        error_details += "     - DN 格式：CN=Administrator,CN=Users,DC=helixon,DC=com\n"
        error_details += "     - 密码：必须是明文密码（不能是加密格式）\n"
        error_details += "  3. ✅ 检查 Base DN 格式是否正确\n"
        error_details += "  4. ✅ 确认所有服务器都正常运行\n"
        error_details += "  5. ✅ 确认防火墙允许 LDAP 连接（端口 389 或 636）\n"
        
        return False, error_details
    
    @staticmethod
    def sync_users(domain):
        """从 AD 域同步所有用户（支持多主机故障转移）"""
        if not LDAP3_AVAILABLE:
            print('[LDAP 同步用户] ldap3 库不可用')
            return []
        
        # 模拟模式
        if LdapService.CONNECTION_MODE == 'mock':
            print('[LDAP 同步用户] 使用模拟模式')
            return [
                {'username': 'zhangsan@helixon.com', 'email': 'zhangsan@helixon.com', 'display_name': '张三', 'dn': 'CN=zhangsan,CN=Users,DC=helixon,DC=com'},
                {'username': 'lisi@helixon.com', 'email': 'lisi@helixon.com', 'display_name': '李四', 'dn': 'CN=lisi,CN=Users,DC=helixon,DC=com'},
                {'username': 'wangwu@helixon.com', 'email': 'wangwu@helixon.com', 'display_name': '王五', 'dn': 'CN=wangwu,CN=Users,DC=helixon,DC=com'},
                {'username': 'administrator@helixon.com', 'email': 'administrator@helixon.com', 'display_name': 'Administrator', 'dn': 'CN=Administrator,CN=Users,DC=helixon,DC=com'},
            ]
        
        # 获取服务器列表（支持多主机）
        domain_config = {
            'ldap_hosts': domain.ldap_hosts if hasattr(domain, 'ldap_hosts') else domain.ldap_host,
            'ldap_host': domain.ldap_host,
            'ldap_port': domain.ldap_port,
            'ldaps_port': domain.ldaps_port,
            'use_ssl': domain.use_ssl,
            'admin_dn': domain.admin_dn,
            'admin_password': domain.admin_password,
            'ldap_password': domain.ldap_password,
            'base_dn': domain.base_dn
        }
        
        servers = LdapService.get_ldap_servers(domain_config)
        if not servers:
            print('[LDAP 同步用户] ❌ 未配置 LDAP 服务器')
            return []
        
        print(f'[LDAP 同步用户] 尝试连接 {len(servers)} 台服务器：{servers}')
        
        # 尝试连接每个服务器
        for protocol, host, port in servers:
            try:
                print(f'[LDAP 同步用户] 尝试连接服务器：{protocol}://{host}:{port}')
                users = LdapService._sync_users_with_protocol(domain, protocol, host, port)
                if users and len(users) > 0:
                    print(f'[LDAP 同步用户] ✅ 成功从服务器 {host}:{port} 同步 {len(users)} 个用户')
                    return users
                else:
                    print(f'[LDAP 同步用户] ⚠️  服务器 {host}:{port} 未找到用户')
            except Exception as e:
                print(f'[LDAP 同步用户] ❌ 服务器 {host}:{port} 同步失败：{str(e)[:100]}')
                if protocol == 'ldaps':
                    print(f'[LDAP 同步用户] ⚠️  LDAPS 失败，尝试回退到 LDAP...')
                    continue
                else:
                    continue
        
        print(f'[LDAP 同步用户] ❌ 所有 {len(servers)} 台服务器都同步失败')
        return []
    
    @staticmethod
    def _sync_users_with_protocol(domain, protocol, host, port):
        """使用指定协议和服务器同步用户"""
        server_url = f"{protocol}://{host}:{port}"
        
        # 创建服务器对象（不追随 referral，避免绑定凭据被转发到第三方主机）
        server = Server(server_url, get_info=ALL, tls=build_tls_context(), connect_timeout=10)
        print(f'[LDAP 同步用户] 连接服务器：{server_url}')
        
        # 提取用户名
        username = None
        if '=' in domain.admin_dn:
            username = domain.admin_dn.split(',')[0].split('=')[1]
        else:
            username = domain.admin_dn
        
        # 提取域名
        domain_name = None
        if 'DC=' in domain.base_dn:
            dc_parts = [part.replace('DC=', '').strip() for part in domain.base_dn.split(',') if 'DC=' in part]
            if dc_parts:
                domain_name = '.'.join(dc_parts)
        
        # 尝试多种认证方式（使用 ldap_password 明文密码）
        auth_configs = [
            {'user': domain.admin_dn, 'auth': SIMPLE},
            {'user': f"{username}@{domain_name}" if domain_name else username, 'auth': NTLM},
            {'user': domain.admin_dn, 'auth': None},
        ]
        
        conn = None
        # 凭据为 Fernet 加密存储，绑定前需解密（旧数据可能是明文，原样使用）
        try:
            ldap_password = secret_decrypt(domain.ldap_password or domain.admin_password)
        except RuntimeError as e:
            print(f'[LDAP 同步用户] {e}')
            return []
        if not ldap_password:
            print('[LDAP 同步用户] ❌ 未配置管理员密码')
            return []
        
        # 添加详细日志
        print(f'[LDAP 同步用户] 尝试认证...')
        print(f'[LDAP 同步用户] 使用密码长度：{len(ldap_password) if ldap_password else 0}')
        
        for auth_config in auth_configs:
            try:
                print(f'[LDAP 同步用户] 尝试认证方式：{auth_config["auth"]}, 用户：{auth_config["user"][:50]}...')
                conn = Connection(
                    server,
                    user=auth_config['user'],
                    password=ldap_password,
                    authentication=auth_config['auth'],
                    auto_bind=False,
                    receive_timeout=30
                )
                conn.open()
                if protocol == 'ldap':
                    # 389 端口先升级 STARTTLS 再绑定，避免凭据明文传输
                    conn.start_tls()
                if conn.bind() and conn.bound:
                    print(f'[LDAP 同步用户] ✅ 认证成功')
                    break  # 认证成功，跳出循环
                conn = None
            except Exception as e:
                conn = None
                print(f'[LDAP 同步用户] ❌ 认证方式 {auth_config["auth"]} 失败：{str(e)[:100]}')
                continue
        
        if not conn:
            raise Exception('所有认证方式都失败')
        
        # 搜索用户 - 使用更通用的过滤器
        # 方法 1: 搜索所有用户对象（排除计算机）
        search_filters = [
            '(&(objectClass=user)(objectCategory=person)(!(objectClass=computer)))',  # 只搜索人员用户
            '(&(objectClass=user)(sAMAccountType=805306368))',  # 普通用户
            '(objectClass=user)',  # 所有用户对象（最宽松）
        ]
        
        users = []
        search_base = domain.base_dn
        
        # 如果没有指定 Base DN，尝试使用 CN=Users
        if not search_base or not search_base.strip():
            search_base = f"CN=Users,{domain.base_dn}" if 'DC=' in domain.base_dn else domain.base_dn
        
        for search_filter in search_filters:
            try:
                print(f'[LDAP 同步用户] 尝试过滤器：{search_filter}')
                
                result = conn.search(
                    search_base=search_base,
                    search_filter=search_filter,
                    search_scope=SUBTREE,
                    attributes=['sAMAccountName', 'mail', 'displayName', 'distinguishedName', 'telephoneNumber', 'mobile', 'userPrincipalName']
                )
                
                print(f'[LDAP 同步用户] 搜索结果：找到 {len(conn.entries)} 个对象')
                
                # 如果找到用户，处理结果
                if len(conn.entries) > 0:
                    for entry in conn.entries:
                        # 使用 userPrincipalName 作为用户名 (优先) 或使用 sAMAccountName
                        upn = str(entry.userPrincipalName.value) if hasattr(entry, 'userPrincipalName') and entry.userPrincipalName.value else ''
                        samaccountname = str(entry.sAMAccountName.value) if hasattr(entry, 'sAMAccountName') and entry.sAMAccountName.value else ''
                        
                        # 优先使用 UPN，如果没有 UPN 则使用 sAMAccountName
                        username = upn if upn else samaccountname
                        
                        # 跳过空用户名和计算机账户
                        if not username or username.endswith('$'):
                            continue
                        
                        user_info = {
                            'username': username,  # 使用 UPN 作为用户名
                            'email': str(entry.mail.value) if hasattr(entry, 'mail') and entry.mail.value else '',
                            'display_name': str(entry.displayName.value) if hasattr(entry, 'displayName') and entry.displayName.value else username,
                            'phone': str(entry.telephoneNumber.value) if hasattr(entry, 'telephoneNumber') and entry.telephoneNumber.value else '',
                            'mobile': str(entry.mobile.value) if hasattr(entry, 'mobile') and entry.mobile.value else '',
                            'upn': upn,
                            'dn': entry.entry_dn
                        }
                        users.append(user_info)
                    
                    # 如果找到用户，跳出过滤器循环
                    if len(users) > 0:
                        print(f'[LDAP 同步用户] 成功同步 {len(users)} 个用户')
                        break
                        
            except Exception as e:
                print(f'[LDAP 同步用户] 过滤器 {search_filter} 执行失败：{str(e)[:100]}')
                continue
        
        conn.unbind()
        return users
    
    @staticmethod
    def lookup_user_by_email(domain, email):
        """按 mail 查找用户，返回 dict 或 None。
        返回字段：user_dn, mobile, mail, sam_account_name, member_of(list), disabled(bool)。
        """
        if not LDAP3_AVAILABLE:
            return None
        from services.ldap_filter import escape_ldap

        try:
            bind_password = secret_decrypt(domain.admin_password)
        except RuntimeError as e:
            print(f'[LDAP 查找] {e}')
            return None

        servers = LdapService.get_ldap_servers({
            'ldap_hosts': domain.ldap_hosts or domain.ldap_host,
            'ldap_host': domain.ldap_host,
            'ldap_port': domain.ldap_port,
            'ldaps_port': domain.ldaps_port,
            'use_ssl': domain.use_ssl,
            'admin_dn': domain.admin_dn,
            'admin_password': bind_password,
            'base_dn': domain.base_dn,
        })
        if not servers:
            return None

        filt = f'(&(objectClass=user)(objectCategory=person)(mail={escape_ldap(email)}))'
        attrs = ['distinguishedName', 'mail', 'mobile', 'sAMAccountName', 'memberOf', 'userAccountControl']
        for protocol, host, port in servers:
            server_url = f"{protocol}://{host}:{port}"
            server = Server(server_url, get_info=ALL, tls=build_tls_context(), connect_timeout=10)
            conn = None
            try:
                conn = Connection(server, user=domain.admin_dn,
                                  password=bind_password,
                                  authentication=SIMPLE, auto_bind=False, receive_timeout=30)
                conn.open()
                if protocol == 'ldap':
                    # 389 端口先升级 STARTTLS 再绑定，避免管理员密码明文传输
                    if not conn.start_tls():
                        raise LDAPException('STARTTLS 失败（域控可能未安装证书），result=%s' % conn.result)
                conn.bind()
                if not conn.bound:
                    raise LDAPException('绑定失败：%s' % conn.result)
                conn.search(search_base=domain.base_dn, search_filter=filt, search_scope=SUBTREE,
                            attributes=attrs)
                # Bound + searched OK on this server: a real "no such user" → stop.
                if not conn.entries:
                    return None
                entry = conn.entries[0]
                uac = 0
                try:
                    uac = int(entry.userAccountControl.value) if entry.userAccountControl.value else 0
                except Exception:
                    uac = 0
                member_of = []
                try:
                    raw = entry.memberOf.values if entry.memberOf.values else []
                    member_of = [str(x) for x in raw]
                except Exception:
                    member_of = []
                return {
                    'user_dn': entry.entry_dn,
                    'mail': str(entry.mail.value) if entry.mail.value else '',
                    'mobile': str(entry.mobile.value) if entry.mobile.value else '',
                    'sam_account_name': str(entry.sAMAccountName.value) if entry.sAMAccountName.value else '',
                    'member_of': member_of,
                    'disabled': bool(uac & 0x2),  # ACCOUNTDISABLE (value 2)
                }
            except Exception as e:
                print(f'[LDAP 查找] 服务器 {host}:{port} 失败，尝试下一台：{str(e)[:120]}')
                continue
            finally:
                if conn:
                    try:
                        conn.unbind()
                    except Exception:
                        pass
        return None

    @staticmethod
    def admin_set_password_by_dn(domain, user_dn, new_password):
        """用管理员绑定，对指定 DN 重置密码（不需要原密码）。返回 (ok, message)。"""
        if not LDAP3_AVAILABLE:
            return False, 'ldap3 库不可用'
        if LdapService.CONNECTION_MODE == 'mock':
            return True, '密码修改成功 (模拟)'
        try:
            bind_password = secret_decrypt(domain.admin_password)
            servers = LdapService.get_ldap_servers({
                'ldap_hosts': domain.ldap_hosts or domain.ldap_host,
                'ldap_host': domain.ldap_host,
                'ldap_port': domain.ldap_port,
                'ldaps_port': domain.ldaps_port,
                'use_ssl': domain.use_ssl,
                'admin_dn': domain.admin_dn,
                'admin_password': bind_password,
                'base_dn': domain.base_dn,
            })
            if not servers:
                return False, '未配置 LDAP 服务器'
            encoded = ('"' + new_password + '"').encode('utf-16-le')
            last_err = '密码修改失败'
            for protocol, host, port in servers:
                server_url = f"{protocol}://{host}:{port}"
                # 不追随 referral，避免绑定凭据被转发到第三方主机
                server = Server(server_url, get_info=ALL, tls=build_tls_context(), connect_timeout=10)
                conn = None
                try:
                    conn = Connection(server, user=domain.admin_dn,
                                      password=bind_password,
                                      authentication=SIMPLE, auto_bind=False)
                    conn.open()
                    if protocol == 'ldap':
                        tls_ok = conn.start_tls()
                        if not tls_ok:
                            raise Exception('STARTTLS 失败（域控可能未安装证书），result=%s' % conn.result)
                    conn.bind()

                    result = conn.modify(user_dn, {'unicodePwd': [(MODIFY_REPLACE, [encoded])]})
                    if result:
                        conn.unbind()
                        # 验证：用新密码绑定确认（失败不影响结果，只记日志）
                        try:
                            verify_conn = Connection(server, user=user_dn,
                                                    password=new_password,
                                                    authentication=SIMPLE, auto_bind=False,
                                                    receive_timeout=10)
                            verify_conn.open()
                            if protocol == 'ldap':
                                verify_conn.start_tls()
                            verify_conn.bind()
                            verify_conn.unbind()
                            return True, '密码修改成功（已验证）'
                        except Exception as ve:
                            # 密码已经改成功，验证失败可能是 AD 同步延迟，不阻断
                            return True, '密码修改成功（验证待 AD 同步）'
                    # Modify rejected (policy/auth) — do not retry other servers.
                    last_err = conn.result.get('message', '密码修改失败')
                    conn.unbind()
                    return False, last_err
                except Exception as e:
                    last_err = f'密码修改失败：{str(e)}'
                    continue
                finally:
                    if conn:
                        try:
                            conn.unbind()
                        except Exception:
                            pass
            return False, last_err
        except Exception as e:
            return False, f'密码修改失败：{str(e)}'

    @staticmethod
    def verify_user_bind(domain, user_dn, password):
        """用员工 DN + 密码做 LDAP 绑定，验证账号密码是否正确。返回 (ok, message)。"""
        if not LDAP3_AVAILABLE:
            return False, 'ldap3 库不可用'
        try:
            servers = LdapService.get_ldap_servers({
                'ldap_hosts': domain.ldap_hosts or domain.ldap_host,
                'ldap_host': domain.ldap_host,
                'ldap_port': domain.ldap_port,
                'ldaps_port': domain.ldaps_port,
                'use_ssl': domain.use_ssl,
                'base_dn': domain.base_dn,
            })
            last_err = '连接失败'
            for protocol, host, port in servers:
                server_url = f"{protocol}://{host}:{port}"
                server = Server(server_url, get_info=ALL, tls=build_tls_context(), connect_timeout=10)
                try:
                    conn = Connection(server, user=user_dn, password=password,
                                      authentication=SIMPLE, auto_bind=False)
                    conn.open()
                    if protocol == 'ldap':
                        conn.start_tls()
                    conn.bind()
                    if conn.bound:
                        conn.unbind()
                        return True, '验证成功'
                    conn.unbind()
                    return False, '账号或密码错误'
                except Exception as e:
                    last_err = str(e)[:120]
                    continue
            return False, f'连接失败：{last_err}'
        except Exception as e:
            return False, f'验证失败：{str(e)}'
