#!/bin/bash
# ============================================================
#  华深智药 · 密码自助重置  ——  一键部署 (Linux)
# ------------------------------------------------------------
#  用法：
#    bash deploy_linux.sh              # DEMO 模式：零配置，立即体验
#    bash deploy_linux.sh prod         # 生产模式（默认 SQLite）
#    DATABASE_URL=postgresql://u:p@h:5432/db  bash deploy_linux.sh prod
#    SYSTEM_PORT=5001 bash deploy_linux.sh prod   # 换端口
#
#  部署后自动后台运行。管理：
#    查看日志：tail -f backend/logs/app.log
#    查看进程：cat backend/.app.pid
#    停止：     kill $(cat backend/.app.pid)
#    重启：     重新运行本脚本即可（自动停旧起新）
# ============================================================
set -e
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
cd "$(dirname "$0")/backend"
PY=.venv/bin/python
MODE="${1:-demo}"   # demo | prod
PORT="${SYSTEM_PORT:-5000}"
HOST="${SYSTEM_HOST:-0.0.0.0}"
PID_FILE=.app.pid
LOG_FILE=logs/app.log

# ---- 子命令 ----
if [ "$MODE" = "stop" ]; then
    if [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
        kill "$(cat $PID_FILE)" && echo "已停止 (PID $(cat $PID_FILE))"
        rm -f "$PID_FILE"
    else
        echo "服务未在运行"
    fi
    exit 0
fi
if [ "$MODE" = "status" ]; then
    if [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
        echo "✅ 运行中 (PID $(cat $PID_FILE)) | 端口 $PORT | 日志 $LOG_FILE"
    else
        echo "❌ 未运行"
    fi
    exit 0
fi

# ---- 1) 虚拟环境 ----
if [ ! -f "$PY" ]; then
    echo "[1/5] 创建虚拟环境..."
    python3 -m venv .venv
fi

# ---- 2) 依赖 ----
echo "[2/5] 安装依赖..."
$PY -m pip install --upgrade pip -q
$PY -m pip install -q -r requirements.txt

# ---- 3) .env ----
if [ ! -f .env ]; then
    echo "[3/5] 生成 .env（随机密钥）..."
    SK=$($PY -c "import secrets;print(secrets.token_hex(32))")
    FK=$($PY -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())")
    if [ "$MODE" = "prod" ]; then
        DB="${DATABASE_URL:-sqlite:///ad_password.db}"
        cat > .env <<EOF
SECRET_KEY=$SK
SECRET_ENCRYPTION_KEY=$FK
DATABASE_URL=$DB
DEMO_MODE=false
HTTPS_ENABLED=false
SESSION_TIMEOUT=8
CORS_ORIGINS=
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBER=true
PASSWORD_REQUIRE_SPECIAL=true
EOF
    else
        cat > .env <<EOF
SECRET_KEY=$SK
SECRET_ENCRYPTION_KEY=$FK
DATABASE_URL=sqlite:///ad_demo.db
DEMO_MODE=true
CORS_ORIGINS=
EOF
    fi
else
    echo "[3/5] 已存在 .env，跳过生成"
fi

# ---- 4) 端口冲突检查 + 停旧实例 ----
echo "[4/5] 检查端口 $PORT..."
PORT_BUSY=$($PY -c "import socket;s=socket.socket();print('YES' if s.connect_ex(('127.0.0.1',$PORT))==0 else 'NO');s.close()")
if [ "$PORT_BUSY" = "YES" ]; then
    if [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
        echo "  端口被旧实例占用 (PID $(cat $PID_FILE))，正在重启..."
        kill "$(cat $PID_FILE)" 2>/dev/null || true
        sleep 2
        rm -f "$PID_FILE"
    else
        echo "  ⚠ 端口 $PORT 已被其他程序占用！"
        echo "  查看占用：ss -tlnp | grep :$PORT"
        echo "  换端口：SYSTEM_PORT=5001 bash deploy_linux.sh $MODE"
        exit 1
    fi
fi

# ---- 5) 后台启动 ----
mkdir -p logs
echo "[5/5] 后台启动 (gunicorn $HOST:$PORT)..."
nohup $PY -m gunicorn --bind "$HOST:$PORT" --workers 2 --threads 4 app:app >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
sleep 3

# ---- 验证 ----
RECHECK=$($PY -c "import socket;s=socket.socket();print('YES' if s.connect_ex(('127.0.0.1',$PORT))==0 else 'NO');s.close()")
if [ "$RECHECK" = "YES" ]; then
    echo ""
    echo "============================================"
    echo "  ✅ 启动成功！PID $(cat $PID_FILE)"
    echo "  重置页：http://服务器IP:$PORT/reset"
    echo "  管理后台：http://服务器IP:$PORT/login (admin/admin)"
    if [ "$MODE" = "prod" ]; then
        echo "  生产模式 → 登录后台配【域】+【短信】"
    else
        echo "  DEMO 模式 → 邮箱任意 + 手机 13800000000"
    fi
    echo "--------------------------------------------"
    echo "  查看日志：tail -f $(pwd)/$LOG_FILE"
    echo "  查看状态：bash deploy_linux.sh status"
    echo "  停止：     bash deploy_linux.sh stop"
    echo "  重启：     重新运行本脚本即可"
    echo "============================================"
else
    echo "  ❌ 启动失败！查看日志：tail -f $(pwd)/$LOG_FILE"
    exit 1
fi
