#!/usr/bin/env python3
"""
AD 密码管理系统 - 生产环境安全检查脚本
用于检查系统是否满足生产环境安全要求
"""

import os
import sys
import secrets
import re
from pathlib import Path

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# 检查结果统计
passed = []
warnings = []
errors = []

def print_header(text):
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}{text}{NC}")
    print(f"{BLUE}{'='*60}{NC}\n")

def check_pass(text):
    print(f"{GREEN}✓ {text}{NC}")
    passed.append(text)

def check_warning(text):
    print(f"{YELLOW}⚠️  {text}{NC}")
    warnings.append(text)

def check_error(text):
    print(f"{RED}✗ {text}{NC}")
    errors.append(text)

def check_secret_key():
    """检查 SECRET_KEY 配置"""
    print_header("检查 SECRET_KEY 配置")
    
    secret_key = os.getenv('SECRET_KEY')
    
    if not secret_key:
        check_error("SECRET_KEY 未设置")
        return False
    
    if len(secret_key) < 32:
        check_error("SECRET_KEY 长度不足 32 位")
        return False
    
    # 检查是否为默认值
    default_patterns = [
        'your-secret-key',
        'your-super-secret-key',
        'change-this',
        'change-in-production',
        'default',
        'secret'
    ]
    
    for pattern in default_patterns:
        if pattern.lower() in secret_key.lower():
            check_error(f"SECRET_KEY 包含默认字符串：{pattern}")
            return False
    
    check_pass("SECRET_KEY 配置安全")
    return True

def check_database_url():
    """检查数据库连接配置"""
    print_header("检查 DATABASE_URL 配置")
    
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        check_error("DATABASE_URL 未设置")
        return False
    
    # 检查是否使用 SQLite（不推荐生产环境）
    if db_url.startswith('sqlite'):
        check_warning("生产环境建议使用 PostgreSQL/MySQL/SQL Server，而不是 SQLite")
        return True
    
    # 检查是否包含密码
    if '@' not in db_url:
        check_error("DATABASE_URL 格式不正确，可能缺少密码")
        return False
    
    # 检查弱密码
    weak_passwords = ['password', '123456', 'admin', 'root', 'default']
    for weak in weak_passwords:
        if weak in db_url.lower():
            check_warning(f"数据库密码可能包含弱密码：{weak}")
            break
    
    check_pass("DATABASE_URL 配置正确")
    return True

def check_debug_mode():
    """检查 DEBUG 模式"""
    print_header("检查 DEBUG 模式")
    
    debug = os.getenv('FLASK_DEBUG', 'False').lower()
    
    if debug == 'true':
        check_error("生产环境必须关闭 DEBUG 模式")
        return False
    
    check_pass("DEBUG 模式已关闭")
    return True

def check_admin_password():
    """检查管理员密码"""
    print_header("检查管理员密码配置")
    
    admin_pwd = os.getenv('ADMIN_PASSWORD', 'admin')
    
    if admin_pwd == 'admin':
        check_error("使用默认管理员密码，必须修改！")
        return False
    
    if len(admin_pwd) < 8:
        check_error("管理员密码长度不足 8 位")
        return False
    
    # 密码复杂度检查
    has_upper = bool(re.search(r'[A-Z]', admin_pwd))
    has_lower = bool(re.search(r'[a-z]', admin_pwd))
    has_digit = bool(re.search(r'\d', admin_pwd))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', admin_pwd))
    
    if not has_upper:
        check_warning("密码不包含大写字母")
    if not has_lower:
        check_warning("密码不包含小写字母")
    if not has_digit:
        check_warning("密码不包含数字")
    if not has_special:
        check_warning("密码不包含特殊字符")
    
    if has_upper and has_lower and has_digit and len(admin_pwd) >= 12:
        check_pass("管理员密码强度足够")
    else:
        check_warning("建议使用更复杂的密码（至少 12 位，包含大小写字母、数字和特殊字符）")
    
    return True

def check_cors_config():
    """检查 CORS 配置"""
    print_header("检查 CORS 配置")
    
    cors_origins = os.getenv('CORS_ORIGINS', '')
    
    if not cors_origins:
        check_warning("CORS_ORIGINS 未设置，将允许所有来源（不安全）")
        return False
    
    # 检查是否包含 localhost（开发环境）
    if 'localhost' in cors_origins or '127.0.0.1' in cors_origins:
        check_warning("CORS 配置包含 localhost，生产环境应使用实际域名")
    
    # 检查是否使用通配符
    if '*' in cors_origins:
        check_error("CORS 配置使用通配符 *，生产环境必须指定具体域名")
        return False
    
    check_pass("CORS 配置正确")
    return True

def check_session_config():
    """检查会话配置"""
    print_header("检查会话安全配置")
    
    # 检查 session 超时
    session_timeout = int(os.getenv('SESSION_TIMEOUT', '8'))
    if session_timeout > 24:
        check_warning(f"Session 超时时间过长：{session_timeout}小时，建议不超过 24 小时")
    else:
        check_pass(f"Session 超时时间合理：{session_timeout}小时")
    
    # 检查是否启用 HTTPS cookie
    secure = os.getenv('SESSION_COOKIE_SECURE', 'true').lower()
    if secure != 'true':
        check_warning("建议启用 SESSION_COOKIE_SECURE（仅 HTTPS 传输）")
    else:
        check_pass("SESSION_COOKIE_SECURE 已启用")
    
    return True

def check_password_policy():
    """检查密码策略"""
    print_header("检查密码策略配置")
    
    min_length = int(os.getenv('PASSWORD_MIN_LENGTH', '8'))
    if min_length < 8:
        check_error(f"密码最小长度不足 8 位：{min_length}")
        return False
    elif min_length < 12:
        check_warning(f"建议密码最小长度至少 12 位，当前：{min_length}")
    else:
        check_pass(f"密码最小长度合理：{min_length}")
    
    # 检查密码复杂度要求
    require_upper = os.getenv('PASSWORD_REQUIRE_UPPERCASE', 'true').lower() == 'true'
    require_lower = os.getenv('PASSWORD_REQUIRE_LOWERCASE', 'true').lower() == 'true'
    require_number = os.getenv('PASSWORD_REQUIRE_NUMBER', 'true').lower() == 'true'
    require_special = os.getenv('PASSWORD_REQUIRE_SPECIAL', 'true').lower() == 'true'
    
    if not (require_upper and require_lower and require_number):
        check_warning("建议启用所有密码复杂度要求（大写、小写、数字、特殊字符）")
    else:
        check_pass("密码复杂度要求完整")
    
    return True

def check_log_config():
    """检查日志配置"""
    print_header("检查日志配置")
    
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('LOG_FILE', 'logs/app.log')
    
    check_pass(f"日志级别：{log_level}")
    check_pass(f"日志文件路径：{log_file}")
    
    # 检查日志目录是否可写
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
            check_pass(f"已创建日志目录：{log_dir}")
        except Exception as e:
            check_error(f"无法创建日志目录：{e}")
            return False
    
    return True

def check_file_permissions():
    """检查文件权限"""
    print_header("检查文件权限（仅 Linux/Unix）")
    
    if os.name != 'posix':
        print(f"{YELLOW}跳过：Windows 系统不检查文件权限{NC}")
        return True
    
    # 检查 .env 文件权限
    env_file = '.env'
    if os.path.exists(env_file):
        stat_info = os.stat(env_file)
        mode = oct(stat_info.st_mode)[-3:]
        
        if mode != '600':
            check_warning(f".env 文件权限为 {mode}，建议设置为 600（仅所有者可读写）")
            check_warning(f"运行命令：chmod 600 {env_file}")
        else:
            check_pass(f".env 文件权限正确：{mode}")
    
    return True

def check_dependencies():
    """检查依赖包"""
    print_header("检查安全相关依赖")
    
    required_packages = [
        'Flask',
        'Flask-SQLAlchemy',
        'bcrypt',
        'ldap3',
        'pyotp'
    ]
    
    missing = []
    
    for pkg in required_packages:
        try:
            __import__(pkg.lower().replace('-', '_'))
            check_pass(f"{pkg} 已安装")
        except ImportError:
            check_error(f"{pkg} 未安装")
            missing.append(pkg)
    
    if missing:
        check_error(f"缺少依赖包：{', '.join(missing)}")
        check_error("运行命令：pip install -r requirements.txt")
        return False
    
    return True

def print_summary():
    """打印总结"""
    print_header("安全检查总结")
    
    print(f"\n{GREEN}通过检查：{len(passed)}{NC}")
    print(f"{YELLOW}警告项：{len(warnings)}{NC}")
    print(f"{RED}错误项：{len(errors)}{NC}\n")
    
    if errors:
        print(f"\n{RED}❌ 发现 {len(errors)} 个严重问题，不建议部署到生产环境！{NC}")
        print("\n请修复以下问题：")
        for i, error in enumerate(errors, 1):
            print(f"{RED}{i}. {error}{NC}")
    elif warnings:
        print(f"\n{YELLOW}⚠️  发现 {len(warnings)} 个警告，建议优化后部署{NC}")
        print("\n建议优化项：")
        for i, warning in enumerate(warnings, 1):
            print(f"{YELLOW}{i}. {warning}{NC}")
    else:
        print(f"\n{GREEN}✅ 所有安全检查通过，可以部署到生产环境！{NC}")
    
    print()

def generate_report():
    """生成检查报告"""
    report_file = 'security_check_report.txt'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("AD 密码管理系统 - 生产环境安全检查报告\n")
        f.write("="*60 + "\n")
        f.write(f"检查时间：{os.popen('date').read().strip()}\n")
        f.write(f"检查主机：{os.uname().nodename if os.name == 'posix' else os.environ.get('COMPUTERNAME', 'Unknown')}\n\n")
        
        f.write(f"\n通过检查：{len(passed)}\n")
        f.write(f"警告项：{len(warnings)}\n")
        f.write(f"错误项：{len(errors)}\n\n")
        
        if errors:
            f.write("\n严重问题：\n")
            for i, error in enumerate(errors, 1):
                f.write(f"{i}. {error}\n")
        
        if warnings:
            f.write("\n警告项：\n")
            for i, warning in enumerate(warnings, 1):
                f.write(f"{i}. {warning}\n")
        
        f.write("\n建议：\n")
        if errors:
            f.write("❌ 发现严重安全问题，不建议部署到生产环境！\n")
            f.write("请先修复所有错误项后再进行部署。\n")
        elif warnings:
            f.write("⚠️  存在警告项，建议优化后部署。\n")
            f.write("如果时间允许，请尽量修复所有警告项。\n")
        else:
            f.write("✅ 所有安全检查通过，可以安全部署！\n")
    
    print(f"{BLUE}检查报告已保存到：{report_file}{NC}\n")

def main():
    """主函数"""
    print(f"\n{BLUE}╔══════════════════════════════════════════════════════════╗{NC}")
    print(f"{BLUE}║                                                          ║{NC}")
    print(f"{BLUE}║     AD 密码管理系统 - 生产环境安全检查                   ║{NC}")
    print(f"{BLUE}║                                                          ║{NC}")
    print(f"{BLUE}╚══════════════════════════════════════════════════════════╝{NC}\n")
    
    # 加载 .env 文件
    env_file = '.env'
    if not os.path.exists(env_file):
        env_file = '.env.production'
    
    if os.path.exists(env_file):
        print(f"{GREEN}✓ 加载环境配置文件：{env_file}{NC}\n")
        from dotenv import load_dotenv
        load_dotenv(env_file)
    else:
        print(f"{YELLOW}⚠️  未找到环境配置文件，使用默认配置{NC}\n")
    
    # 执行检查
    check_secret_key()
    check_database_url()
    check_debug_mode()
    check_admin_password()
    check_cors_config()
    check_session_config()
    check_password_policy()
    check_log_config()
    check_file_permissions()
    check_dependencies()
    
    # 打印总结
    print_summary()
    
    # 生成报告
    generate_report()
    
    # 返回状态码
    if errors:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
