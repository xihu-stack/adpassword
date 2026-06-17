#!/usr/bin/env python3
"""
快速更新 LDAP 管理员密码 - 解决认证失败问题
"""
import sys
import getpass
sys.path.insert(0, '.')

from app import create_app
from models.models import Domain, db

app = create_app()

print("="*70)
print("快速更新 LDAP 管理员密码")
print("="*70)
print()

with app.app_context():
    # 获取当前域配置
    domain = Domain.query.filter_by(is_active=True).first()
    
    if not domain:
        print("❌ 未找到域配置")
        sys.exit(1)
    
    print(f"当前域：{domain.name}")
    print(f"LDAP 主机：{domain.ldap_host}:{domain.ldap_port}")
    print(f"Admin DN: {domain.admin_dn}")
    print()
    
    # 显示当前密码状态
    if domain.ldap_password:
        pwd_len = len(domain.ldap_password)
        if pwd_len > 2:
            pwd_masked = domain.ldap_password[:2] + '*' * (pwd_len - 2)
        else:
            pwd_masked = '**'
        print(f"⚠️  当前 LDAP 密码：{pwd_masked} (长度：{pwd_len})")
        print(f"   这个密码认证失败，需要更新")
    else:
        print("⚠️  当前 LDAP 密码：(空)")
    
    if domain.admin_password and domain.admin_password.startswith('$2b$'):
        print(f"⚠️  admin_password 是 bcrypt 加密格式，不能用于 LDAP 连接")
    
    print()
    print("="*70)
    print("请输入正确的 LDAP 管理员明文密码")
    print("="*70)
    print()
    print("💡 提示:")
    print("  - 密码必须是明文 (例如：Password123)")
    print("  - 不能是 bcrypt 加密格式 ($2b$开头)")
    print("  - 如果不确定密码，请联系 AD 域管理员")
    print()
    
    # 输入新密码
    while True:
        new_password = getpass.getpass("请输入 LDAP 管理员明文密码：")
        
        if not new_password:
            print("❌ 密码不能为空，请重新输入\n")
            continue
        
        confirm_password = getpass.getpass("请再次输入密码确认：")
        
        if new_password != confirm_password:
            print("❌ 两次输入的密码不一致，请重新输入\n")
            continue
        
        # 基本密码强度检查
        if len(new_password) < 6:
            print(f"⚠️  警告：密码长度只有 {len(new_password)} 位，建议至少 8 位")
            choice = input("是否继续？(y/n): ")
            if choice.lower() != 'y':
                continue
        
        # 检查是否是 bcrypt 格式
        if new_password.startswith('$2b$'):
            print("❌ 错误：这是 bcrypt 加密格式，请输入明文密码\n")
            continue
        
        break
    
    print()
    print("正在更新密码...")
    
    # 更新密码
    domain.ldap_password = new_password
    db.session.commit()
    
    print("✅ 密码已更新!")
    print()
    
    # 显示新密码信息
    pwd_len = len(new_password)
    if pwd_len > 2:
        pwd_masked = new_password[:2] + '*' * (pwd_len - 2)
    else:
        pwd_masked = '**'
    print(f"新 LDAP 密码：{pwd_masked} (长度：{pwd_len})")
    print()
    
    # 立即测试连接
    print("="*70)
    print("正在测试 LDAP 连接...")
    print("="*70)
    print()
    
    from ldap3 import Server, Connection, ALL, SIMPLE, Tls
    import ssl
    
    # 使用 LDAPS
    ldaps_port = domain.ldaps_port or 636
    protocol = 'ldaps'
    
    tls_context = Tls(
        validate=ssl.CERT_NONE,
        version=ssl.PROTOCOL_TLS_CLIENT,
        ciphers='ALL:@SECLEVEL=0'
    )
    
    server = Server(
        f"{protocol}://{domain.ldap_host}:{ldaps_port}",
        get_info=ALL,
        tls=tls_context,
        connect_timeout=10
    )
    
    try:
        conn = Connection(
            server,
            user=domain.admin_dn,
            password=new_password,
            authentication=SIMPLE,
            auto_bind=True,
            receive_timeout=30
        )
        
        print("✅ LDAP 连接成功!")
        print()
        print("🎉 可以正常使用管理员后台修改密码功能了!")
        print()
        print("下一步:")
        print("  1. 返回管理后台")
        print("  2. 进入域配置页面")
        print("  3. 点击'测试连接'按钮验证")
        print("  4. 如果成功，点击'保存配置'")
        
        conn.unbind()
        
    except Exception as e:
        print(f"❌ LDAP 连接仍然失败：{str(e)}")
        print()
        print("可能原因:")
        print("  1. 密码仍然不正确")
        print("  2. 账户被锁定或禁用")
        print("  3. 网络问题或防火墙阻止")
        print("  4. DN 格式不正确")
        print()
        print("建议:")
        print("  - 确认密码正确 (联系 AD 域管理员)")
        print("  - 检查账户状态")
        print("  - 检查网络连接")
    
    print()
    print("="*70)
    print("操作完成")
    print("="*70)
