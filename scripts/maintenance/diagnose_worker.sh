#!/bin/bash

# =============================================================================
# Gunicorn Worker 启动失败诊断脚本
# =============================================================================
# 用途：诊断 worker 无法启动的原因
# 使用：./diagnose_worker.sh
# =============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
LOGS_DIR="${PROJECT_ROOT}/logs"
PYTHON_BIN="${BACKEND_DIR}/venv/bin/python3"
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
print_info "║  Gunicorn Worker 启动失败诊断         ║"
print_info "╚════════════════════════════════════════╝"
echo ""

# 1. 检查 Python 虚拟环境
print_info "1. 检查 Python 虚拟环境..."
if [ ! -f "$PYTHON_BIN" ]; then
    print_error "Python 虚拟环境不存在：$PYTHON_BIN"
    exit 1
fi
print_success "Python 虚拟环境存在"

# 2. 检查 gunicorn 是否安装
print_info "2. 检查 Gunicorn 是否安装..."
if [ ! -f "${BACKEND_DIR}/venv/bin/gunicorn" ]; then
    print_error "Gunicorn 未安装"
    exit 1
fi
print_success "Gunicorn 已安装"

# 3. 检查 .env 文件
print_info "3. 检查环境变量配置..."
if [ ! -f "$ENV_FILE" ]; then
    print_error ".env 文件不存在：$ENV_FILE"
    print_warning "请创建 .env 文件并设置必要的环境变量"
    cat << 'EOF'

示例 .env 文件内容:
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
PORT=5000
HOST=0.0.0.0
WORKERS=4
THREADS=2
HTTPS_ENABLED=false

EOF
    exit 1
fi

# 加载并检查关键环境变量
source "$ENV_FILE" 2>/dev/null || true

missing_vars=()
if [ -z "$SECRET_KEY" ]; then
    missing_vars+=("SECRET_KEY")
fi
if [ -z "$DATABASE_URL" ]; then
    missing_vars+=("DATABASE_URL")
fi

if [ ${#missing_vars[@]} -gt 0 ]; then
    print_error "缺少必要的环境变量:"
    for var in "${missing_vars[@]}"; do
        print_error "  - $var"
    done
    print_warning "请在 $ENV_FILE 中设置这些变量"
    exit 1
fi
print_success "环境变量配置正确"

# 4. 检查数据库连接
print_info "4. 测试数据库连接..."
cd "$BACKEND_DIR"
source venv/bin/activate

db_test_result=$("$PYTHON_BIN" -c "
import os
import sys
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    from models.models import db, User
    from config import Config
    from flask import Flask
    
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    
    with app.app_context():
        # 尝试连接数据库
        db.engine.connect()
        print('SUCCESS')
except Exception as e:
    print(f'ERROR: {str(e)}')
    sys.exit(1)
" 2>&1) || db_exit_code=$?

if [[ "$db_test_result" == *"SUCCESS"* ]]; then
    print_success "数据库连接正常"
else
    print_error "数据库连接失败:"
    echo "$db_test_result" | sed 's/^/  /'
    print_warning "请检查 DATABASE_URL 配置和数据库服务状态"
fi

# 5. 检查应用是否能正常导入
print_info "5. 检查应用导入..."
import_test_result=$("$PYTHON_BIN" -c "
import sys
try:
    import app
    print('SUCCESS')
except Exception as e:
    print(f'ERROR: {str(e)}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" 2>&1) || import_exit_code=$?

if [[ "$import_test_result" == *"SUCCESS"* ]]; then
    print_success "应用导入成功"
else
    print_error "应用导入失败:"
    echo "$import_test_result" | sed 's/^/  /'
    exit 1
fi

# 6. 检查端口占用
print_info "6. 检查端口占用..."
port=${PORT:-5000}
if command -v ss &> /dev/null; then
    port_check=$(ss -tuln 2>/dev/null | grep ":$port " || true)
    if [ -n "$port_check" ]; then
        print_warning "端口 $port 已被占用"
        echo "$port_check" | sed 's/^/  /'
        print_info "停止占用端口的进程或更改端口配置"
    else
        print_success "端口 $port 可用"
    fi
elif command -v netstat &> /dev/null; then
    port_check=$(netstat -tuln 2>/dev/null | grep ":$port " || true)
    if [ -n "$port_check" ]; then
        print_warning "端口 $port 已被占用"
        echo "$port_check" | sed 's/^/  /'
    else
        print_success "端口 $port 可用"
    fi
fi

# 7. 检查日志文件
print_info "7. 检查错误日志..."
error_log="${LOGS_DIR}/error.log"
app_log="${LOGS_DIR}/app.log"

if [ -f "$error_log" ] && [ -s "$error_log" ]; then
    print_info "最近错误日志:"
    tail -n 20 "$error_log" | sed 's/^/  /'
elif [ -f "$app_log" ] && [ -s "$app_log" ]; then
    print_info "最近应用日志:"
    tail -n 20 "$app_log" | sed 's/^/  /'
else
    print_warning "未找到日志文件或日志为空"
fi

# 8. 手动测试启动 Gunicorn (单次测试)
print_info "8. 测试启动 Gunicorn (3 秒超时测试)..."
cd "$BACKEND_DIR"

timeout 3 "${BACKEND_DIR}/venv/bin/gunicorn" \
    --bind "${HOST:-0.0.0.0}:${port}" \
    --workers 1 \
    --threads 1 \
    --access-logfile - \
    --error-logfile - \
    --log-level debug \
    app:app > /tmp/gunicorn_test.log 2>&1 &

test_pid=$!
sleep 2

if ps -p $test_pid > /dev/null 2>&1; then
    print_success "Gunicorn 可以正常启动"
    kill -TERM $test_pid 2>/dev/null || true
    wait $test_pid 2>/dev/null || true
else
    print_error "Gunicorn 启动失败，详细日志:"
    if [ -f /tmp/gunicorn_test.log ]; then
        cat /tmp/gunicorn_test.log | sed 's/^/  /'
    fi
fi

rm -f /tmp/gunicorn_test.log

# 9. 检查依赖包
print_info "9. 检查关键依赖包..."
check_package() {
    local pkg=$1
    if "${PYTHON_BIN}" -c "import $pkg" 2>/dev/null; then
        print_success "  ✓ $pkg 已安装"
        return 0
    else
        print_error "  ✗ $pkg 未安装"
        return 1
    fi
}

missing_packages=()
for pkg in flask bcrypt ldap3 psycopg2; do
    if ! check_package "$pkg"; then
        missing_packages+=("$pkg")
    fi
done

if [ ${#missing_packages[@]} -gt 0 ]; then
    print_warning "缺失依赖包，请运行以下命令安装:"
    print_info "cd $BACKEND_DIR && source venv/bin/activate && pip install -r requirements.txt"
fi

echo ""
print_info "╔════════════════════════════════════════╗"
print_info "║          诊断完成                     ║"
print_info "╚════════════════════════════════════════╝"
echo ""

print_info "建议的解决步骤:"
echo "  1. 确保所有环境变量已正确配置 (.env 文件)"
echo "  2. 确保数据库服务正在运行且可访问"
echo "  3. 确保所有依赖已安装：pip install -r requirements.txt"
echo "  4. 检查端口是否被占用"
echo "  5. 查看详细错误日志：tail -f $LOGS_DIR/error.log"
echo ""
