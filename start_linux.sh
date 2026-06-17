#!/bin/bash

# =============================================================================
# AD 密码管理系统 - Linux 一键启动脚本
# =============================================================================
# 说明：本脚本用于在 Linux 系统下一键启动 AD 密码管理系统
# 注意：数据库已独立部署，本脚本不包含数据库安装
# 用法：
#   ./start_linux.sh           # 前台启动
#   ./start_linux.sh --daemon  # 后台启动（守护进程模式）
#   ./start_linux.sh -d        # 后台启动（简写）
#   ./start_linux.sh --stop    # 停止服务
#   ./start_linux.sh --status  # 查看服务状态
# =============================================================================

#关闭防火墙
sudo systemctl stop firewalld 2>/dev/null || true
sudo systemctl disable firewalld 2>/dev/null || true


set -e

# 运行模式：foreground（默认）或 daemon
RUN_MODE="foreground"
ACTION="start"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"

# 日志文件
LOG_FILE="${PROJECT_ROOT}/logs/startup.log"
PID_FILE="${PROJECT_ROOT}/logs/app.pid"
mkdir -p "${PROJECT_ROOT}/logs"

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1" >> "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') [SUCCESS] $1" >> "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') [WARNING] $1" >> "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >> "$LOG_FILE"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查系统依赖
check_system_requirements() {
    print_info "=========================================="
    print_info "步骤 1: 检查系统依赖"
    print_info "=========================================="
    
    local missing_deps=()
    
    # 检查 Python
    if ! command_exists python3; then
        missing_deps+=("python3")
    else
        PYTHON_VERSION=$(python3 --version)
        print_success "✓ Python 已安装：$PYTHON_VERSION"
    fi
    
    # 检查 pip（多种方式）
    if command_exists pip3; then
        PIP_VERSION=$(pip3 --version)
        print_success "✓ pip 已安装：$PIP_VERSION"
    elif command_exists pip; then
        PIP_VERSION=$(pip --version)
        print_success "✓ pip 已安装：$PIP_VERSION"
        # 创建别名
        alias pip3='pip'
    elif python3 -m pip --version >/dev/null 2>&1; then
        PIP_VERSION=$(python3 -m pip --version)
        print_success "✓ pip 已安装：$PIP_VERSION"
    else
        missing_deps+=("pip3")
    fi
    
    # 检查 Node.js (用于构建前端)
    if ! command_exists node; then
        print_warning "⚠ Node.js 未安装，如需构建前端请安装 Node.js"
    else
        NODE_VERSION=$(node --version)
        print_success "✓ Node.js 已安装：$NODE_VERSION"
    fi
    
    # 检查 npm
    if ! command_exists npm; then
        print_warning "⚠ npm 未安装，如需构建前端请安装 npm"
    else
        NPM_VERSION=$(npm --version)
        print_success "✓ npm 已安装：$NPM_VERSION"
    fi
    
    # 如果有缺失的依赖
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_error "缺少以下依赖：${missing_deps[*]}"
        print_info "请使用系统包管理器安装："
        print_info "  Ubuntu/Debian: sudo apt-get install ${missing_deps[*]}"
        print_info "  CentOS/RHEL: sudo yum install ${missing_deps[*]}"
        exit 1
    fi
    
    print_success "✓ 系统依赖检查通过"
    echo ""
}

# 创建虚拟环境（如果不存在）
setup_venv() {
    print_info "=========================================="
    print_info "步骤 2: 配置 Python 虚拟环境"
    print_info "=========================================="
    
    VENV_DIR="${BACKEND_DIR}/venv"
    
    if [ ! -d "$VENV_DIR" ]; then
        print_info "创建虚拟环境..."
        python3 -m venv "$VENV_DIR"
        print_success "✓ 虚拟环境创建成功"
    else
        print_success "✓ 虚拟环境已存在"
    fi
    
    # 激活虚拟环境
    source "${VENV_DIR}/bin/activate"
    print_success "✓ 虚拟环境已激活"
    echo ""
}

# 安装 Python 依赖
install_python_dependencies() {
    print_info "=========================================="
    print_info "步骤 3: 安装 Python 依赖"
    print_info "=========================================="
    
    REQUIREMENTS_FILE="${BACKEND_DIR}/requirements.txt"
    
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        print_error "找不到 requirements.txt 文件"
        exit 1
    fi
    
    # 升级 pip
    print_info "升级 pip..."
    pip install --upgrade pip
    
    # 安装依赖
    print_info "安装 Python 依赖包..."
    pip install -r "$REQUIREMENTS_FILE"
    
    print_success "✓ Python 依赖安装完成"
    echo ""
}

# 构建前端资源
build_frontend() {
    print_info "=========================================="
    print_info "步骤 4: 构建前端资源"
    print_info "=========================================="
    
    if ! command_exists npm; then
        print_warning "⚠ npm 未安装，跳过前端构建"
        print_info "前端资源需要手动构建或使用已构建的版本"
        return 0
    fi
    
    cd "$FRONTEND_DIR"
    
    # 检查 node_modules
    if [ ! -d "node_modules" ]; then
        print_info "安装前端依赖..."
        npm install
    else
        # 检查是否存在 rollup 模块问题
        if [ -f "node_modules/rollup/dist/native.js" ]; then
            print_info "检测 Rollup 模块完整性..."
            if ! node -e "require('@rollup/rollup-linux-x64-gnu')" 2>/dev/null; then
                print_warning "⚠ 发现 Rollup 模块问题，正在修复..."
                print_info "清除 node_modules 和 package-lock.json..."
                rm -rf node_modules package-lock.json
                print_info "重新安装依赖..."
                npm install
            fi
        fi
    fi
    
    # 构建前端
    print_info "构建前端资源..."
    npm run build
    
    print_success "✓ 前端资源构建完成"
    cd "$PROJECT_ROOT"
    echo ""
}

# 初始化配置文件
init_config() {
    print_info "=========================================="
    print_info "步骤 5: 检查配置文件"
    print_info "=========================================="
    
    ENV_FILE="${BACKEND_DIR}/.env"
    
    if [ ! -f "$ENV_FILE" ]; then
        print_warning "⚠ .env 配置文件不存在"
        print_info "正在创建默认配置文件..."
        
        cat > "$ENV_FILE" << 'EOF'
# Flask 配置
SECRET_KEY=your-super-secret-key-change-this-in-production

# 数据库配置（PostgreSQL）
DATABASE_URL=postgresql://postgres:password@localhost/ad_password_db

# CAS 配置（暂时禁用，使用本地登录）
CAS_SERVER_LOGIN_URL=http://localhost:5000/mock-cas/login
CAS_SERVER_LOGOUT_URL=http://localhost:5000/logout
CAS_SERVER_VALIDATE_URL=http://localhost:5000/mock-cas/validate
CAS_AFTER_LOGIN_URL=http://localhost:5000/cas/callback

# CORS 配置（前端地址）
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
EOF
        
        print_success "✓ 已创建默认配置文件，请根据实际情况修改"
    else
        print_success "✓ 配置文件已存在"
    fi
    
    echo ""
}

# 检查服务是否正在运行
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    
    # 通过进程名查找
    if pgrep -f "gunicorn.*app:app" > /dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

# 获取服务 PID
get_pid() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
            echo "$pid"
            return 0
        fi
    fi
    
    pgrep -f "gunicorn.*app:app" | head -n 1
}

# 停止服务
stop_service() {
    print_info "正在停止服务..."
    
    local pid=$(get_pid)
    
    if [ -z "$pid" ]; then
        print_warning "服务未运行"
        return 0
    fi
    
    print_info "检测到服务正在运行 (PID: $pid)"
    
    # 优雅停止
    kill -TERM "$pid" 2>/dev/null || true
    
    # 等待结束
    local count=0
    while [ $count -lt 30 ]; do
        if ! ps -p "$pid" > /dev/null 2>&1; then
            print_success "服务已优雅停止"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        if [ $((count % 5)) -eq 0 ]; then
            print_info "等待服务停止... ($count/30 秒)"
        fi
    done
    
    # 强制停止
    print_warning "优雅停止超时，强制停止..."
    kill -9 "$pid" 2>/dev/null || true
    pkill -9 -f "gunicorn.*app:app" 2>/dev/null || true
    rm -f "$PID_FILE"
    print_success "服务已强制停止"
    return 0
}

# 显示服务状态
show_status() {
    echo ""
    print_info "╔════════════════════════════════════════╗"
    print_info "║   AD 密码管理系统 - 服务状态          ║"
    print_info "╚════════════════════════════════════════╝"
    echo ""
    
    if is_running; then
        local pid=$(get_pid)
        print_success "运行状态：${GREEN}正在运行${NC}"
        print_info "进程 PID: $pid"
        print_info "监听端口：5000"
        
        if ps -p "$pid" > /dev/null 2>&1; then
            local cpu_usage=$(ps -p "$pid" -o %cpu= 2>/dev/null | xargs)
            local mem_usage=$(ps -p "$pid" -o %mem= 2>/dev/null | xargs)
            local uptime=$(ps -p "$pid" -o etime= 2>/dev/null | xargs)
            
            print_info "CPU 使用率：${cpu_usage:-N/A}%"
            print_info "内存使用率：${mem_usage:-N/A}%"
            print_info "运行时间：${uptime:-N/A}"
        fi
        
        print_info "日志文件：${LOG_FILE}"
    else
        print_error "运行状态：${RED}已停止${NC}"
    fi
    
    echo ""
}

# 启动应用（后台模式）
start_application_daemon() {
    print_info "=========================================="
    print_info "步骤 6: 启动应用服务 (后台模式)"
    print_info "=========================================="
    
    cd "$BACKEND_DIR"
    
    # 确保日志目录存在
    mkdir -p "${PROJECT_ROOT}/logs"
    
    # 检查是否已运行
    if is_running; then
        local pid=$(get_pid)
        print_warning "服务已经在运行中 (PID: $pid)"
        print_info "如需重启，请先停止：$0 --stop"
        return 0
    fi
    
    # 检查 Gunicorn 是否安装
    if ! python -c "import gunicorn" 2>/dev/null; then
        print_warning "⚠ Gunicorn 未安装，正在安装..."
        pip install gunicorn
    fi
    
    # 获取端口配置
    PORT=5000
    HOST="0.0.0.0"
    
    print_info "启动 Gunicorn 服务器 (后台模式)..."
    print_info "监听地址：http://${HOST}:${PORT}"
    
    # 使用 nohup 后台启动
    nohup "${BACKEND_DIR}/venv/bin/gunicorn" \
        --bind "${HOST}:${PORT}" \
        --workers 4 \
        --threads 2 \
        --worker-class sync \
        --timeout 120 \
        --keep-alive 5 \
        --pid "${PID_FILE}" \
        --access-logfile "${PROJECT_ROOT}/logs/access.log" \
        --error-logfile "${PROJECT_ROOT}/logs/error.log" \
        --capture-output \
        --log-level info \
        app:app >> "${LOG_FILE}" 2>&1 &
    
    # 等待启动
    sleep 3
    
    # 验证启动
    if is_running; then
        local pid=$(get_pid)
        print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        print_success "🚀 AD 密码管理系统启动成功！"
        print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        print_success "✓ 运行模式：后台守护进程"
        print_success "✓ 访问地址：http://${HOST}:${PORT}"
        print_success "✓ 默认账号：admin"
        print_success "✓ 默认密码：admin"
        print_success "✓ 进程 PID: $pid"
        print_success "✓ 日志文件：${LOG_FILE}"
        print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        print_info ""
        print_info "停止服务：$0 --stop"
        print_info "查看状态：$0 --status"
        print_info "查看日志：tail -f ${LOG_FILE}"
        print_info ""
        
        # 保存 PID
        if [ -f "${PID_FILE}" ]; then
            print_success "✓ PID 文件已保存：${PID_FILE}"
        fi
        
        return 0
    else
        print_error "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        print_error "✗ 服务启动失败"
        print_error "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        print_error "请查看日志："
        print_error "  • 启动日志：${LOG_FILE}"
        print_error "  • 错误日志：${PROJECT_ROOT}/logs/error.log"
        
        if [ -f "${PROJECT_ROOT}/logs/error.log" ]; then
            print_error "\n最近错误:"
            tail -n 10 "${PROJECT_ROOT}/logs/error.log" | sed 's/^/  /'
        fi
        
        return 1
    fi
}

# 启动应用（前台模式）
start_application_foreground() {
    print_info "=========================================="
    print_info "步骤 6: 启动应用服务 (前台模式)"
    print_info "=========================================="
    
    cd "$BACKEND_DIR"
    
    # 确保日志目录存在
    mkdir -p "${PROJECT_ROOT}/logs"
    
    # 检查 Gunicorn 是否安装
    if ! python -c "import gunicorn" 2>/dev/null; then
        print_warning "⚠ Gunicorn 未安装，正在安装..."
        pip install gunicorn
    fi
    
    # 获取端口配置（从 app.py 读取数据库或默认 5000）
    PORT=5000
    HOST="0.0.0.0"
    
    print_info "启动 Gunicorn 服务器 (前台模式)..."
    print_info "监听地址：http://${HOST}:${PORT}"
    print_info "日志文件：${LOG_FILE}"
    print_info ""
    print_info "=========================================="
    print_success "🚀 AD 密码管理系统启动成功！"
    print_info "=========================================="
    print_info "访问地址：http://${HOST}:${PORT}"
    print_info "默认账号：admin"
    print_info "默认密码：admin"
    print_info ""
    print_info "按 Ctrl+C 停止服务"
    print_info "=========================================="
    
    # 启动 Gunicorn（前台模式，使用 exec 替换当前进程）
    exec gunicorn \
        --workers 4 \
        --threads 2 \
        --worker-class sync \
        --timeout 120 \
        --keep-alive 5 \
        --access-logfile "${PROJECT_ROOT}/logs/access.log" \
        --error-logfile "${PROJECT_ROOT}/logs/error.log" \
        --capture-output \
        --log-level info \
        app:app
}

# 清理函数（仅用于前台模式）
cleanup() {
    echo ""
    print_info "正在停止服务..."
    if [ -n "$MAIN_PID" ]; then
        kill $MAIN_PID 2>/dev/null || true
    fi
    print_info "服务已停止"
    exit 0
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--daemon)
                RUN_MODE="daemon"
                ACTION="start"
                shift
                ;;
            --stop)
                ACTION="stop"
                shift
                ;;
            --status)
                ACTION="status"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "未知参数：$1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 显示帮助信息
show_help() {
    cat << EOF
${BLUE}╔═══════════════════════════════════════════════════════╗${NC}
${BLUE}║${NC}       AD 密码管理系统 - Linux 一键启动脚本         ${BLUE}║${NC}
${BLUE}╚═══════════════════════════════════════════════════════╝${NC}

${GREEN}用法:${NC}
  $0 [选项]

${GREEN}选项:${NC}
  (无参数)       - 前台启动服务（默认）
  -d, --daemon   - 后台启动服务（守护进程模式）
  --stop         - 停止服务
  --status       - 查看服务状态
  -h, --help     - 显示帮助信息

${GREEN}示例:${NC}
  $0             # 前台启动（阻塞终端）
  $0 -d          # 后台启动（不阻塞终端）
  $0 --daemon    # 后台启动（同上）
  $0 --stop      # 停止服务
  $0 --status    # 查看服务状态

${GREEN}其他管理方式:${NC}
  tail -f logs/startup.log     # 查看启动日志
  tail -f logs/error.log       # 查看错误日志
  ps aux | grep gunicorn       # 查看进程
  kill \$(cat logs/app.pid)    # 通过 PID 文件停止

EOF
}

# 主函数
main() {
    # 解析命令行参数
    parse_args "$@"
    
    echo ""
    print_info "╔════════════════════════════════════════╗"
    print_info "║   AD 密码管理系统 - 一键启动脚本       ║"
    print_info "║   Linux 版本                           ║"
    print_info "╚════════════════════════════════════════╝"
    echo ""
    
    # 根据动作执行
    case $ACTION in
        stop)
            stop_service
            exit 0
            ;;
        status)
            show_status
            exit 0
            ;;
        start)
            # 设置信号处理（仅前台模式）
            if [ "$RUN_MODE" = "foreground" ]; then
                trap cleanup SIGINT SIGTERM
            fi
            
            # 执行各个步骤
            check_system_requirements
            setup_venv
            install_python_dependencies
            build_frontend
            init_config
            
            # 根据模式选择启动方式
            if [ "$RUN_MODE" = "daemon" ]; then
                start_application_daemon
            else
                start_application_foreground
            fi
            ;;
        *)
            print_error "未知操作：$ACTION"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
