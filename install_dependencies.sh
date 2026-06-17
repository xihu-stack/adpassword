#!/bin/bash

# =============================================================================
# AD 密码管理系统 - Linux 系统依赖安装脚本
# =============================================================================
# 功能：自动检测并安装项目所需的所有系统级依赖和插件
# 支持：Ubuntu/Debian/CentOS/RHEL/Rocky Linux/Fedora
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 全局变量
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${PROJECT_ROOT}/logs/install_deps.log"
BACKUP_DIR="${PROJECT_ROOT}/backups"

# 确保日志目录存在
mkdir -p "${PROJECT_ROOT}/logs"
mkdir -p "$BACKUP_DIR"

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1" >> "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') [SUCCESS] $1" >> "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') [WARNING] $1" >> "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >> "$LOG_FILE"
}

# 显示使用帮助
show_help() {
    cat << EOF
${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}
${CYAN}║${NC}       AD 密码管理系统 - 系统依赖安装工具            ${CYAN}║${NC}
${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}

${GREEN}用法:${NC}
  $0 [选项]

${GREEN}选项:${NC}
  ${CYAN}-a, --all${NC}         - 安装所有依赖（推荐）
  ${CYAN}-s, --system${NC}      - 仅安装系统工具
  ${CYAN}-p, --python${NC}      - 仅安装 Python 环境
  ${CYAN}-n, --nodejs${NC}      - 仅安装 Node.js 环境
  ${CYAN}-d, --database${NC}    - 仅安装数据库客户端
  ${CYAN}-l, --ldap${NC}        - 仅安装 LDAP 相关库
  ${CYAN}-t, --tools${NC}       - 仅安装辅助工具
  ${CYAN}--dry-run${NC}         - 模拟执行，不实际安装
  ${CYAN}--force${NC}           - 强制重新安装
  ${CYAN}-h, --help${NC}        - 显示此帮助信息
  ${CYAN}-v, --verbose${NC}     - 详细输出模式

${GREEN}示例:${NC}
  $0 --all              # 安装所有依赖
  $0 --python           # 仅安装 Python 环境
  $0 --dry-run          # 预览将要安装的内容

EOF
}

# 检测操作系统
detect_os() {
    print_info "检测操作系统..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
        print_success "检测到操作系统：$PRETTY_NAME"
    elif [ -f /etc/redhat-release ]; then
        OS="centos"
        OS_VERSION=$(cat /etc/redhat-release | grep -oP '\d+\.\d+')
        print_success "检测到操作系统：CentOS/RHEL $OS_VERSION"
    else
        print_error "无法识别操作系统类型"
        exit 1
    fi
    
    # 确定包管理器
    case $OS in
        ubuntu|debian)
            PACKAGE_MANAGER="apt"
            ;;
        centos|rhel|rocky|almalinux)
            PACKAGE_MANAGER="yum"
            ;;
        fedora)
            PACKAGE_MANAGER="dnf"
            ;;
        *)
            print_error "不支持的操作系统：$OS"
            exit 1
            ;;
    esac
    
    print_info "使用包管理器：$PACKAGE_MANAGER"
}

# 检查是否以 root 权限运行
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "请使用 sudo 或 root 用户运行此脚本"
        print_info "用法：sudo $0 $@"
        exit 1
    fi
}

# 更新包管理器缓存
update_package_cache() {
    print_info "更新包管理器缓存..."
    
    case $PACKAGE_MANAGER in
        apt)
            apt-get update -qq
            ;;
        yum|dnf)
            yum makecache -y
            ;;
    esac
    
    print_success "包管理器缓存已更新"
}

# 安装系统基础工具
install_system_tools() {
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_info "安装系统基础工具..."
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local packages=(
        # 编译工具
        gcc
        gcc-c++
        make
        cmake
        
        # 版本控制
        git
        
        # 网络工具
        curl
        wget
        net-tools
        telnet
        
        # 文本处理
        vim
        jq
        unzip
        zip
        
        # 安全工具
        openssl
        openssl-devel
        
        # 其他工具
        cronie
        logrotate
    )
    
    install_packages "${packages[@]}"
}

# 安装 Python 环境和依赖
install_python_deps() {
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_info "安装 Python 环境和依赖..."
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local packages=(
        python3
        python3-pip
        python3-devel
        python3-virtualenv
        python3-setuptools
    )
    
    install_packages "${packages[@]}"
    
    # 验证 Python 版本
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version)
        print_success "Python 已安装：$python_version"
    else
        print_error "Python 安装失败"
        return 1
    fi
}

# 安装 Node.js 环境
install_nodejs() {
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_info "安装 Node.js 环境..."
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # 检查是否已安装
    if command -v node &> /dev/null; then
        local node_version=$(node --version)
        print_warning "Node.js 已安装：$node_version"
        
        read -p "是否继续安装？(y/N): " choice
        case "$choice" in
            y|Y) print_info "继续安装..." ;;
            *) print_info "跳过 Node.js 安装"; return 0 ;;
            *) print_info "跳过 Node.js 安装"; return 0 ;;
        esac
    fi
    
    case $PACKAGE_MANAGER in
        apt)
        # Ubuntu/Debian: 使用 NodeSource 仓库
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
        apt-get install -y nodejs
        ;;
        yum|dnf)
        # CentOS/RHEL: 使用 NodeSource 仓库
        curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
        yum install -y nodejs
        ;;
    esac
    
    # 验证安装
    if command -v node &> /dev/null && command -v npm &> /dev/null; then
        local node_version=$(node --version)
        local npm_version=$(npm --version)
        print_success "Node.js 已安装：$node_version"
        print_success "npm 已安装：$npm_version"
    else
        print_error "Node.js 安装失败"
        return 1
    fi
}

# 安装数据库客户端
install_database_clients() {
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_info "安装数据库客户端..."
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local packages=()
    
    case $PACKAGE_MANAGER in
        apt)
            packages=(
                postgresql-client      # PostgreSQL 客户端
                default-mysql-client   # MySQL 客户端
                freetds-dev            # SQL Server 客户端 (FreeTDS)
            )
            ;;
        yum|dnf)
            packages=(
                postgresql             # PostgreSQL 客户端
                mysql                  # MySQL 客户端
                unixODBC               # SQL Server ODBC
                unixODBC-devel
            )
            ;;
    esac
    
    install_packages "${packages[@]}"
    
    print_success "数据库客户端已安装"
}

# 安装 LDAP 相关库
install_ldap_libs() {
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_info "安装 LDAP 相关库..."
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local packages=()
    
    case $PACKAGE_MANAGER in
        apt)
            packages=(
                libldap2-dev
                libsasl2-dev
                libssl-dev
                ldap-utils
            )
            ;;
        yum|dnf)
            packages=(
                openldap-devel
                openldap-clients
                cyrus-sasl-devel
                cyrus-sasl-md5
            )
            ;;
    esac
    
    install_packages "${packages[@]}"
    
    print_success "LDAP 库已安装"
}

# 安装辅助工具
install_auxiliary_tools() {
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_info "安装辅助工具..."
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local packages=(
        htop              # 系统监控
        iotop             # IO 监控
        nethogs           # 网络监控
        ncdu              # 磁盘使用分析
        tree              # 目录树查看
        rsync             # 文件同步
        screen            # 终端复用
        tmux              # 终端复用
        lsof              # 查看打开的文件
        strace            # 系统调用跟踪
    )
    
    install_packages "${packages[@]}" || print_warning "部分辅助工具安装失败（可选）"
}

# 通用包安装函数
install_packages() {
    local packages=("$@")
    local failed_packages=()
    
    for pkg in "${packages[@]}"; do
        print_info "正在安装：$pkg"
        
        case $PACKAGE_MANAGER in
            apt)
                if DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$pkg" >> "$LOG_FILE" 2>&1; then
                    print_success "✓ $pkg 安装成功"
                else
                    print_error "✗ $pkg 安装失败"
                    failed_packages+=("$pkg")
                fi
                ;;
            yum|dnf)
                if yum install -y -q "$pkg" >> "$LOG_FILE" 2>&1; then
                    print_success "✓ $pkg 安装成功"
                else
                    print_error "✗ $pkg 安装失败"
                    failed_packages+=("$pkg")
                fi
                ;;
        esac
    done
    
    if [ ${#failed_packages[@]} -gt 0 ]; then
        print_warning "以下包安装失败：${failed_packages[*]}"
        return 1
    fi
    
    return 0
}

# 安装 Python 项目的依赖
install_project_python_deps() {
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_info "安装项目 Python 依赖..."
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    cd "${PROJECT_ROOT}/backend"
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        print_info "创建 Python 虚拟环境..."
        python3 -m venv venv
        print_success "虚拟环境创建成功"
    else
        print_success "虚拟环境已存在"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级 pip
    print_info "升级 pip..."
    pip install --upgrade pip -q
    
    # 安装 requirements.txt
    if [ -f "requirements.txt" ]; then
        print_info "安装 Python 依赖包..."
        pip install -r requirements.txt -q
        print_success "Python 依赖安装完成"
    else
        print_error "找不到 requirements.txt"
        return 1
    fi
    
    # 验证关键包
    print_info "验证关键 Python 包..."
    local required_packages=("flask" "gunicorn" "bcrypt" "ldap3" "psycopg2-binary")
    
    for pkg in "${required_packages[@]}"; do
        if python -c "import $pkg" 2>/dev/null; then
            print_success "✓ $pkg 已安装"
        else
            print_warning "⚠ $pkg 未安装（可能不影响使用）"
        fi
    done
    
    deactivate
}

# 安装前端依赖
install_frontend_deps() {
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_info "安装前端依赖..."
    print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    cd "${PROJECT_ROOT}/frontend"
    
    if [ ! -f "package.json" ]; then
        print_error "找不到 package.json"
        return 1
    fi
    
    # 检查 node_modules
    if [ -d "node_modules" ]; then
        print_warning "node_modules 已存在"
        read -p "是否删除并重新安装？(y/N): " choice
        case "$choice" in
            y|Y)
                print_info "删除旧的 node_modules..."
                rm -rf node_modules package-lock.json
                ;;
            *)
                print_info "跳过前端依赖安装"
                return 0
                ;;
        esac
    fi
    
    # 安装依赖
    print_info "安装 npm 依赖..."
    npm install --loglevel=error
    
    if [ $? -eq 0 ]; then
        print_success "前端依赖安装完成"
    else
        print_error "前端依赖安装失败"
        return 1
    fi
}

# 显示摘要信息
show_summary() {
    echo ""
    print_info "╔════════════════════════════════════════╗"
    print_info "║   安装完成！                         ║"
    print_info "╚════════════════════════════════════════╝"
    echo ""
    
    # 显示版本信息
    print_info "已安装的组件版本:"
    
    if command -v python3 &> /dev/null; then
        print_info "  • Python: $(python3 --version)"
    fi
    
    if command -v node &> /dev/null; then
        print_info "  • Node.js: $(node --version)"
    fi
    
    if command -v npm &> /dev/null; then
        print_info "  • npm: $(npm --version)"
    fi
    
    if command -v git &> /dev/null; then
        print_info "  • Git: $(git --version)"
    fi
    
    echo ""
    print_info "下一步操作:"
    print_info "  1. 配置环境变量：编辑 backend/.env"
    print_info "  2. 初始化数据库：运行数据库迁移脚本"
    print_info "  3. 启动应用：./start_linux.sh"
    print_info "  4. 查看日志：tail -f logs/app.log"
    echo ""
    
    # 提示配置
    if [ ! -f "${PROJECT_ROOT}/backend/.env" ]; then
        print_warning "⚠ backend/.env 文件不存在，请复制示例文件并修改："
        print_info "  cp backend/.env.example backend/.env"
        echo ""
    fi
}

# 主函数
main() {
    # 没有参数时显示帮助
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi
    
    # 解析参数
    local install_all=false
    local install_system=false
    local install_python=false
    local install_nodejs=false
    local install_database=false
    local install_ldap=false
    local install_tools=false
    local dry_run=false
    local force=false
    local verbose=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -a|--all)
                install_all=true
                shift
                ;;
            -s|--system)
                install_system=true
                shift
                ;;
            -p|--python)
                install_python=true
                shift
                ;;
            -n|--nodejs)
                install_nodejs=true
                shift
                ;;
            -d|--database)
                install_database=true
                shift
                ;;
            -l|--ldap)
                install_ldap=true
                shift
                ;;
            -t|--tools)
                install_tools=true
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --force)
                force=true
                shift
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "未知选项：$1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 如果没有指定具体选项，默认安装所有
    if [ "$install_all" = true ] || \
       { [ "$install_system" = false ] && [ "$install_python" = false ] && \
         [ "$install_nodejs" = false ] && [ "$install_database" = false ] && \
         [ "$install_ldap" = false ] && [ "$install_tools" = false ]; }; then
        install_all=true
    fi
    
    # 开始安装
    echo ""
    print_info "╔═══════════════════════════════════════════════════════════╗"
    print_info "║   AD 密码管理系统 - 系统依赖安装                        ║"
    print_info "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    
    # 检测操作系统
    detect_os
    
    # 检查 root 权限
    check_root
    
    # 如果是 dry-run 模式，只显示不安装
    if [ "$dry_run" = true ]; then
        print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        print_info "模拟执行模式 - 不会实际安装任何软件包"
        print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if [ "$install_all" = true ] || [ "$install_system" = true ]; then
            print_info "将安装系统工具：gcc, make, git, curl, wget, openssl-devel 等"
        fi
        
        if [ "$install_all" = true ] || [ "$install_python" = true ]; then
            print_info "将安装 Python: python3, python3-pip, python3-devel, python3-virtualenv"
        fi
        
        if [ "$install_all" = true ] || [ "$install_nodejs" = true ]; then
            print_info "将安装 Node.js: nodejs, npm (版本 18.x)"
        fi
        
        if [ "$install_all" = true ] || [ "$install_database" = true ]; then
            print_info "将安装数据库客户端：PostgreSQL, MySQL, SQL Server 客户端"
        fi
        
        if [ "$install_all" = true ] || [ "$install_ldap" = true ]; then
            print_info "将安装 LDAP 库：libldap2-dev/openldap-devel, libsasl2-dev 等"
        fi
        
        if [ "$install_all" = true ] || [ "$install_tools" = true ]; then
            print_info "将安装辅助工具：htop, iotop, ncdu, tree, rsync 等"
        fi
        
        echo ""
        print_success "模拟执行完成"
        exit 0
    fi
    
    # 实际安装模式
    print_info "开始安装系统依赖..."
    echo ""
    
    # 更新包缓存
    update_package_cache
    
    # 根据选项安装
    if [ "$install_all" = true ] || [ "$install_system" = true ]; then
        install_system_tools || print_warning "部分系统工具安装失败"
    fi
    
    if [ "$install_all" = true ] || [ "$install_python" = true ]; then
        install_python_deps || print_warning "Python 环境安装失败"
    fi
    
    if [ "$install_all" = true ] || [ "$install_nodejs" = true ]; then
        install_nodejs || print_warning "Node.js 环境安装失败"
    fi
    
    if [ "$install_all" = true ] || [ "$install_database" = true ]; then
        install_database_clients || print_warning "数据库客户端安装失败"
    fi
    
    if [ "$install_all" = true ] || [ "$install_ldap" = true ]; then
        install_ldap_libs || print_warning "LDAP 库安装失败"
    fi
    
    if [ "$install_all" = true ] || [ "$install_tools" = true ]; then
        install_auxiliary_tools || print_warning "部分辅助工具安装失败（可选）"
    fi
    
    # 安装项目特定依赖
    if [ "$install_all" = true ]; then
        install_project_python_deps || print_warning "项目 Python 依赖安装失败"
        install_frontend_deps || print_warning "前端依赖安装失败"
    fi
    
    # 显示摘要
    show_summary
}

# 捕获错误
trap 'print_error "安装过程中断"; exit 1' INT TERM

# 执行主函数
main "$@"
