#!/bin/bash

# =============================================================================
# AD 密码管理系统 - Linux 重启脚本
# =============================================================================
# 说明：本脚本用于在 Linux 系统下重启 AD 密码管理系统
# 用法：
#   ./restart_linux.sh           # 快速重启（默认）
#   ./restart_linux.sh -f        # 强制重启（清理所有进程）
#   ./restart_linux.sh --force   # 强制重启（同上）
#   ./restart_linux.sh -d        # 后台模式重启
#   ./restart_linux.sh --daemon  # 后台模式重启
#   ./restart_linux.sh -h        # 显示帮助
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
LOGS_DIR="${PROJECT_ROOT}/logs"
PID_FILE="${LOGS_DIR}/app.pid"

# 运行模式
FORCE_MODE=false
DAEMON_MODE=true  # 默认后台运行

# =============================================================================
# 辅助函数
# =============================================================================

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_step() {
    echo ""
    echo -e "${CYAN}════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}════════════════════════════════════════${NC}"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 获取进程 PID
get_pid() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
            echo "$pid"
            return 0
        fi
    fi
    
    # 通过进程名查找
    pgrep -f "gunicorn.*app:app" | head -n 1
}

# 检查服务是否正在运行
is_running() {
    local pid=$(get_pid)
    [ -n "$pid" ]
}

# =============================================================================
# 停止服务
# =============================================================================

stop_service() {
    print_step "步骤 1/6: 停止现有服务"
    
    local pid=$(get_pid)
    
    if [ -z "$pid" ]; then
        print_warning "服务未运行"
        return 0
    fi
    
    print_info "检测到服务正在运行 (PID: $pid)"
    print_info "正在优雅停止服务..."
    
    # 发送 SIGTERM 信号
    kill -TERM "$pid" 2>/dev/null || true
    
    # 等待进程结束
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
    if [ "$FORCE_MODE" = true ]; then
        print_warning "优雅停止超时，强制停止..."
        kill -9 "$pid" 2>/dev/null || true
        pkill -9 -f "gunicorn.*app:app" 2>/dev/null || true
        sleep 2
        print_success "服务已强制停止"
    else
        print_warning "优雅停止超时，如需强制停止请使用 -f 参数"
        return 1
    fi
    
    rm -f "$PID_FILE"
}

# =============================================================================
# 清理残留进程
# =============================================================================

cleanup_processes() {
    print_step "步骤 2/6: 清理残留进程"
    
    local cleaned=false
    
    # 清理 Gunicorn 进程
    if pgrep -f "gunicorn.*app:app" > /dev/null 2>&1; then
        print_warning "发现残留的 Gunicorn 进程"
        
        if [ "$FORCE_MODE" = true ]; then
            pkill -9 -f "gunicorn.*app:app" 2>/dev/null || true
            print_success "已强制清理 Gunicorn 进程"
            cleaned=true
        else
            pkill -f "gunicorn.*app:app" 2>/dev/null || true
            print_success "已清理 Gunicorn 进程"
            cleaned=true
        fi
    fi
    
    # 清理僵尸 Python 进程（仅强制模式）
    if [ "$FORCE_MODE" = true ]; then
        if pgrep -f "python.*app.py" > /dev/null 2>&1; then
            print_warning "发现僵尸 Python 进程"
            pkill -9 -f "python.*app.py" 2>/dev/null || true
            print_success "已清理僵尸 Python 进程"
            cleaned=true
        fi
    fi
    
    if [ "$cleaned" = false ]; then
        print_info "✓ 无残留进程"
    fi
    
    sleep 2
}

# =============================================================================
# 清理端口占用
# =============================================================================

cleanup_ports() {
    print_step "步骤 3/6: 清理端口占用"
    
    local port=${PORT:-5000}
    local cleaned=false
    
    # 使用 ss 查找占用端口的进程
    if command_exists ss; then
        local port_pids=$(ss -tulnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K[0-9]+' || true)
        
        if [ -n "$port_pids" ]; then
            print_warning "端口 $port 被占用"
            
            for pid in $port_pids; do
                if [ "$FORCE_MODE" = true ]; then
                    print_info "强制杀死进程 $pid"
                    kill -9 "$pid" 2>/dev/null || true
                else
                    print_info "停止进程 $pid"
                    kill -TERM "$pid" 2>/dev/null || true
                fi
                cleaned=true
            done
            
            sleep 2
        fi
    fi
    
    # 备选：使用 netstat
    if [ "$cleaned" = false ] && command_exists netstat; then
        local port_pids=$(netstat -tulnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 || true)
        
        if [ -n "$port_pids" ]; then
            print_warning "端口 $port 被占用"
            
            for pid in $port_pids; do
                if [ -n "$pid" ] && [ "$pid" != "-" ]; then
                    if [ "$FORCE_MODE" = true ]; then
                        kill -9 "$pid" 2>/dev/null || true
                    else
                        kill -TERM "$pid" 2>/dev/null || true
                    fi
                    cleaned=true
                fi
            done
            
            sleep 2
        fi
    fi
    
    if [ "$cleaned" = false ]; then
        print_info "✓ 端口 $port 可用"
    else
        print_success "✓ 端口已清理"
    fi
}

# =============================================================================
# 清理缓存和日志
# =============================================================================

cleanup_cache() {
    print_step "步骤 4/6: 清理缓存和日志"
    
    # 清理 Python 缓存
    if [ -d "$BACKEND_DIR" ]; then
        find "$BACKEND_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find "$BACKEND_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
        print_info "✓ Python 缓存已清理"
    fi
    
    # 清理旧日志（保留最近 7 天的）
    if [ -d "$LOGS_DIR" ]; then
        find "$LOGS_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null || true
        print_info "✓ 7 天前的日志已清理"
    fi
    
    # 清理 PID 文件
    rm -f "$PID_FILE"
    
    print_success "✓ 缓存和日志清理完成"
}

# =============================================================================
# 启动服务
# =============================================================================

start_service() {
    print_step "步骤 5/6: 启动服务"
    
    cd "$BACKEND_DIR"
    
    # 检查虚拟环境
    if [ ! -f "${BACKEND_DIR}/venv/bin/python3" ]; then
        print_error "Python 虚拟环境不存在!"
        print_info "请先运行：./start_linux.sh"
        exit 1
    fi
    
    # 激活虚拟环境
    source "${BACKEND_DIR}/venv/bin/activate"
    
    # 检查 Gunicorn
    if ! python -c "import gunicorn" 2>/dev/null; then
        print_warning "⚠ Gunicorn 未安装，正在安装..."
        pip install gunicorn
    fi
    
    # 检查环境变量
    ENV_FILE="${BACKEND_DIR}/.env"
    if [ ! -f "$ENV_FILE" ]; then
        print_error ".env 文件不存在!"
        print_info "请创建配置文件"
        exit 1
    fi
    
    # 获取配置
    local port=${PORT:-5000}
    local host=${HOST:-0.0.0.0}
    local workers=${WORKERS:-4}
    local threads=${THREADS:-2}
    
    if [ "$DAEMON_MODE" = true ]; then
        # 后台模式启动
        print_info "启动模式：后台守护进程"
        print_info "监听地址：http://${host}:${port}"
        
        nohup "${BACKEND_DIR}/venv/bin/gunicorn" \
            --bind "${host}:${port}" \
            --workers "$workers" \
            --threads "$threads" \
            --worker-class sync \
            --timeout 120 \
            --keep-alive 5 \
            --pid "$PID_FILE" \
            --access-logfile "${LOGS_DIR}/access.log" \
            --error-logfile "${LOGS_DIR}/error.log" \
            --capture-output \
            --log-level info \
            app:app >> "${LOGS_DIR}/startup.log" 2>&1 &
        
        # 等待启动
        sleep 3
        
        # 验证启动
        if is_running; then
            local pid=$(get_pid)
            print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            print_success "✓ 服务已成功启动 (后台模式)"
            print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            print_success "访问地址：http://${host}:${port}"
            print_success "进程 PID: $pid"
            print_success "日志文件：${LOGS_DIR}/startup.log"
            print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        else
            print_error "服务启动失败，请查看日志:"
            print_error "  tail -f ${LOGS_DIR}/error.log"
            deactivate
            exit 1
        fi
    else
        # 前台模式启动
        print_info "启动模式：前台模式"
        print_info "监听地址：http://${host}:${port}"
        print_info ""
        print_info "按 Ctrl+C 停止服务"
        print_info ""
        
        # 使用虚拟环境中的 gunicorn
        exec "${BACKEND_DIR}/venv/bin/gunicorn" \
            --bind "${host}:${port}" \
            --workers "$workers" \
            --threads "$threads" \
            --worker-class sync \
            --timeout 120 \
            --keep-alive 5 \
            --access-logfile "${LOGS_DIR}/access.log" \
            --error-logfile "${LOGS_DIR}/error.log" \
            --capture-output \
            --log-level info \
            app:app
    fi
}

# =============================================================================
# 检查服务状态
# =============================================================================

check_status() {
    print_step "步骤 6/6: 检查服务状态"
    
    sleep 3
    
    if is_running; then
        local pid=$(get_pid)
        print_success "✓ 服务运行正常"
        print_info "进程 PID: $pid"
        
        # 检查端口
        local port=${PORT:-5000}
        if ss -tuln 2>/dev/null | grep -q ":$port "; then
            print_success "✓ 端口 $port 正在监听"
        else
            print_warning "⚠ 端口 $port 未监听"
        fi
        
        # 健康检查
        if command_exists curl; then
            if curl -s --connect-timeout 2 "http://localhost:$port/health" > /dev/null 2>&1; then
                print_success "✓ 健康检查通过"
            else
                print_warning "⚠ 健康检查未响应"
            fi
        fi
    else
        print_error "✗ 服务未运行"
        exit 1
    fi
}

# =============================================================================
# 显示帮助
# =============================================================================

show_help() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}       AD 密码管理系统 - Linux 重启脚本              ${BLUE}║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}用法:${NC}"
    echo "  $0 [选项]"
    echo ""
    echo -e "${GREEN}选项:${NC}"
    echo "  (无参数)        - 快速重启（默认后台运行）"
    echo "  -f, --force     - 强制重启（清理所有进程和端口）"
    echo "  -d, --daemon    - 后台模式启动（守护进程）"
    echo "  --foreground    - 前台模式启动（调试用）"
    echo "  -h, --help      - 显示帮助信息"
    echo ""
    echo -e "${GREEN}示例:${NC}"
    echo "  $0              # 快速重启（后台运行）"
    echo "  $0 -f           # 强制重启（后台运行）"
    echo "  $0 --foreground # 前台重启（占用终端）"
    echo "  $0 --help       # 显示帮助"
    echo ""
    echo -e "${GREEN}其他管理命令:${NC}"
    echo "  ./start_linux.sh -d     # 后台启动"
    echo "  ./start_linux.sh --stop # 停止服务"
    echo "  ./start_linux.sh --status # 查看状态"
    echo "  tail -f logs/error.log  # 查看错误日志"
    echo ""
}

# =============================================================================
# 解析参数
# =============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--force)
                FORCE_MODE=true
                shift
                ;;
            -d|--daemon)
                DAEMON_MODE=true
                shift
                ;;
            --foreground)
                DAEMON_MODE=false
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

# =============================================================================
# 主流程
# =============================================================================

main() {
    parse_args "$@"
    
    echo ""
    print_info "╔════════════════════════════════════════╗"
    print_info "║   AD 密码管理系统 - 重启服务          ║"
    print_info "╚════════════════════════════════════════╝"
    echo ""
    
    print_info "重启模式:"
    if [ "$FORCE_MODE" = true ]; then
        print_warning "• 强制模式：是"
    else
        print_info "• 强制模式：否"
    fi
    
    if [ "$DAEMON_MODE" = true ]; then
        print_success "• 后台启动：是（默认）"
    else
        print_info "• 后台启动：否"
    fi
    
    # 执行重启流程
    stop_service
    cleanup_processes
    cleanup_ports
    cleanup_cache
    start_service
    check_status
    
    echo ""
    print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_success "🎉 项目重启完成！"
    print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    if [ "$DAEMON_MODE" = true ]; then
        print_success "提示:"
        echo "  • 服务已在后台运行 ✓"
        echo "  • 停止服务：./start_linux.sh --stop"
        echo "  • 查看状态：./start_linux.sh --status"
        echo "  • 查看日志：tail -f logs/error.log"
        echo "  • 访问地址：http://localhost:5000"
    else
        print_info "提示:"
        echo "  • 按 Ctrl+C 停止服务"
        echo "  • 服务在前台运行"
    fi
    
    echo ""
}

# =============================================================================
# 执行
# =============================================================================

main "$@"
