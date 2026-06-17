#!/usr/bin/env python3
"""
LDAP/LDAPS 配置管理工具
"""
import sys
sys.path.insert(0, '.')

from app import create_app
from models.models import Domain, db

app = create_app()

def show_config():
    """显示当前配置"""
    with app.app_context():
        domain = Domain.query.filter_by(is_active=True).first()
        if not domain:
            print("❌ 未找到域配置")
            return
        
        print("="*70)
        print("当前 LDAP/LDAPS 配置")
        print("="*70)
        print(f"域名：{domain.name}")
        print(f"LDAP 主机：{domain.ldap_host}")
        print(f"LDAP 端口：{domain.ldap_port}")
        print(f"LDAPS 端口：{domain.ldaps_port}")
        print(f"use_ssl: {domain.use_ssl}")
        print(f"连接 URL: {'ldaps' if domain.use_ssl else 'ldap'}://{domain.ldap_host}:{domain.ldaps_port if domain.use_ssl else domain.ldap_port}")
        print("="*70)

def use_ldap():
    """切换到 LDAP (不加密)"""
    with app.app_context():
        domain = Domain.query.filter_by(is_active=True).first()
        if not domain:
            print("❌ 未找到域配置")
            return
        
        print("切换到 LDAP (不加密模式)...")
        domain.ldap_port = 389
        domain.ldaps_port = 636
        domain.use_ssl = False
        db.session.commit()
        print("✅ 已切换到 LDAP 模式")
        print(f"   连接 URL: ldap://{domain.ldap_host}:{domain.ldap_port}")
        show_config()

def use_ldaps():
    """切换到 LDAPS (加密模式)"""
    with app.app_context():
        domain = Domain.query.filter_by(is_active=True).first()
        if not domain:
            print("❌ 未找到域配置")
            return
        
        print("切换到 LDAPS (加密模式)...")
        domain.ldap_port = 389
        domain.ldaps_port = 636
        domain.use_ssl = True
        db.session.commit()
        print("✅ 已切换到 LDAPS 模式")
        print(f"   连接 URL: ldaps://{domain.ldap_host}:{domain.ldaps_port}")
        show_config()

def test_sync():
    """测试同步功能"""
    with app.app_context():
        from services.ldap_service import LdapService
        
        domain = Domain.query.filter_by(is_active=True).first()
        if not domain:
            print("❌ 未找到域配置")
            return
        
        print("="*70)
        print("测试同步功能")
        print("="*70)
        
        try:
            users = LdapService.sync_users(domain)
            print(f"\n✅ 同步成功！共 {len(users)} 个用户")
            
            if users:
                print("\n前 10 个用户:")
                for i, user in enumerate(users[:10], 1):
                    print(f"  {i}. {user['username']:20} {user['email']:30} {user['display_name']}")
        except Exception as e:
            print(f"\n❌ 同步失败：{str(e)}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法：python ldap_config.py [ldap|ldaps|show|test]")
        print()
        print("命令说明:")
        print("  ldap   - 切换到 LDAP (不加密，端口 389)")
        print("  ldaps  - 切换到 LDAPS (加密，端口 636)")
        print("  show   - 显示当前配置")
        print("  test   - 测试同步功能")
        print()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'ldap':
        use_ldap()
    elif command == 'ldaps':
        use_ldaps()
    elif command == 'show':
        show_config()
    elif command == 'test':
        test_sync()
    else:
        print(f"❌ 未知命令：{command}")
        sys.exit(1)
