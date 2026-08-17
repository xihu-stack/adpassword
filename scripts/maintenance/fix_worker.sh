#!/bin/bash

# =============================================================================
# Gunicorn Worker 启动问题一键修复脚本
# =============================================================================
# 用途：自动诊断并尝试修复 worker 启动问题
# 使用：./fix_worker.sh
# =============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
LOGS_DIR="${PROJECT_ROOT}/logs"
PYTHON_BIN="${BACKEND_DIR}/venv/bin/python3"
PIP_BIN="${BACKEND_DIR}/venv/bin/pip"
ENV_FILE="${BACKEND_DIR}/.env"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

echo ""
print_info "╔════════════════════════════════════════╗"
print_info "║  Gunicorn Worker 问题修复工具         ║"
print_info "╚════════════════════════════════════════╝"
echo ""

# 步骤 1: 停止现有服务
print_info "步骤 1: 停止现有服务..."
if [ -f "${LOGS_DIR}/gunicorn.pid" ]; then
    pid=$(cat "${LOGS_DIR}/gunicorn.pid" 2>/dev/null)
    if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
        print_info "停止进程 (PID: $pid)..."
        kill -TERM "$pid" 2>/dev/null || true
        sleep 2
        if ps -p "$pid" > /dev/null 2>&1; then
            kill -9 "$pid" 2>/dev/null || true
        fi
        print_success "服务已停止"
    fi
fi

# 清理 PID 文件
rm -f "${LOGS_DIR}/gunicorn.pid"
pkill -f "gunicorn.*app:app" 2>/dev/null || true
print_success "已清理残留进程"

# 步骤 2: 检查并安装依赖
print_info "步骤 2: 检查依赖包..."
cd "$BACKEND_DIR"

if [ ! -f "$PYTHON_BIN" ]; then
    print_error "Python 虚拟环境不存在!"
    print_info "请先运行：./start_linux.sh"
    exit 1
fi

source venv/bin/activate

# 检查关键包
missing_deps=false

for pkg in flask gunicorn bcrypt psycopg2 ldap3 pyotp qrcode; do
    if ! python -c "import $pkg" 2>/dev/null; then
        print_warning "缺少依赖：$pkg"
        missing_deps=true
    fi
done

if [ "$missing_deps" = true ]; then
    print_info "重新安装依赖..."
    pip install --upgrade pip
    pip install -r requirements.txt
    print_success "依赖安装完成"
else
    print_success "所有依赖已安装"
fi

# 步骤 3: 清理 Python 缓存
print_info "步骤 3: 清理 Python 缓存..."
find "$BACKEND_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BACKEND_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$BACKEND_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true
print_success "缓存清理完成"

# 步骤 4: 检查环境变量
print_info "步骤 4: 检查环境变量..."
if [ ! -f "$ENV_FILE" ]; then
    print_error ".env 文件不存在!"
    
    # 创建示例文件
    if [ -f "${ENV_FILE}.example" ]; then
        print_info "从示例文件创建 .env..."
        cp "${ENV_FILE}.example" "$ENV_FILE"
        print_warning "请编辑 $ENV_FILE 并设置正确的配置"
        exit 1
    else
        print_info "创建默认 .env 文件..."
        cat > "$ENV_FILE" << 'EOF'
# Flask 配置
SECRET_KEY=your-secret-key-change-in-production
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# 服务器配置
PORT=5000
HOST=0.0.0.0
WORKERS=4
THREADS=2

# HTTPS 配置
HTTPS_ENABLED=false

# CORS 配置
CORS_ORIGINS=http://localhost:5000,http://127.0.0.1:5000

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
EOF
        print_warning "已创建 .env 文件，请修改配置"
        exit 1
    fi
fi

# 加载并验证关键变量
source "$ENV_FILE" 2>/dev/null || true

if [ -z "$SECRET_KEY" ]; then
    print_warning "生成随机 SECRET_KEY..."
    random_key=$(python -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$random_key/" "$ENV_FILE" 2>/dev/null || \
    echo "SECRET_KEY=$random_key" >> "$ENV_FILE"
    source "$ENV_FILE" 2>/dev/null || true
fi

if [ -z "$DATABASE_URL" ]; then
    print_error "DATABASE_URL 未设置!"
    print_warning "请在 .env 文件中设置 DATABASE_URL"
    exit 1
fi

print_success "环境变量配置正确"

# 步骤 5: 测试数据库连接
print_info "步骤 5: 测试数据库连接..."
db_test=$(python -c "
import os
from dotenv import load_dotenv
load_dotenv()

try:
    from models.models import db
    from config import Config
    from flask import Flask
    
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    with app.app_context():
        db.engine.connect()
        print('OK')
except Exception as e:
    print(f'FAILED: {str(e)}')
" 2>&1) || db_exit=$?

if [[ "$db_test" == *"OK"* ]]; then
    print_success "数据库连接正常"
else
    print_error "数据库连接失败:"
    echo "$db_test" | sed 's/^/  /'
    print_warning "请检查数据库配置和服务状态"
fi

# 步骤 6: 测试应用导入
print_info "步骤 6: 测试应用导入..."
import_test=$(python -c "
try:
    import app
    print('OK')
except Exception as e:
    print(f'FAILED: {str(e)}')
    import traceback
    traceback.print_exc()
" 2>&1) || import_exit=$?

if [[ "$import_test" == *"OK"* ]]; then
    print_success "应用导入成功"
else
    print_error "应用导入失败:"
    echo "$import_test" | sed 's/^/  /'
    exit 1
fi

# 步骤 7: 重新启动服务
print_info "步骤 7: 启动服务..."
cd "$BACKEND_DIR"

port=${PORT:-5000}
host=${HOST:-0.0.0.0}
workers=${WORKERS:-4}
threads=${THREADS:-2}

print_info "启动配置:"
print_info "  • 监听地址：http://${host}:${port}"
print_info "  • Worker 数量：${workers}"
print_info "  • 线程数：${threads}"

# 先单 worker 测试启动
print_info "使用单 worker 模式测试启动..."
nohup "${BACKEND_DIR}/venv/bin/gunicorn" \
    --bind "${host}:${port}" \
    --workers 1 \
    --threads "${threads}" \
    --pid "${LOGS_DIR}/gunicorn.pid" \
    --access-logfile "${LOGS_DIR}/access.log" \
    --error-logfile "${LOGS_DIR}/error.log" \
    --log-level info \
    --capture-output \
    --timeout 120 \
    app:app >> "${LOGS_DIR}/app.log" 2>&1 &

sleep 3

# 检查是否启动成功
if [ -f "${LOGS_DIR}/gunicorn.pid" ]; then
    pid=$(cat "${LOGS_DIR}/gunicorn.pid")
    if ps -p "$pid" > /dev/null 2>&1; then
        print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        print_success "✓ 服务已成功启动 (PID: $pid)"
        print_success "✓ 访问地址：http://${host}:${port}"
        print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # 健康检查
        sleep 2
        if curl -s --connect-timeout 2 "http://${host}:${port}/health" > /dev/null 2>&1; then
            print_success "✓ 健康检查通过"
        else
            print_warning "⚠ 健康检查未通过，请查看日志"
        fi
        
        # 尝试扩展到多 worker
        if [ "$workers" -gt 1 ]; then
            print_info "检测到配置了多个 worker ($workers)，建议手动重启以应用配置"
            print_info "执行：./manage_service.sh restart"
        fi
        
        exit 0
    fi
fi

# 启动失败
print_error "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_error "✗ 服务启动失败"
print_error "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "${LOGS_DIR}/error.log" ]; then
    print_error "最近错误:"
    tail -n 20 "${LOGS_DIR}/error.log" | sed 's/^/  /'
fi

echo ""
print_info "建议排查步骤:"
echo "  1. 查看详细日志：tail -f ${LOGS_DIR}/error.log"
echo "  2. 运行诊断脚本：./diagnose_worker.sh"
echo "  3. 检查数据库连接和配置"
echo "  4. 确保端口 $port 未被占用"
echo ""

exit 1
