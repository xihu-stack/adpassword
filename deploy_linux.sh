#!/bin/bash
# ============================================================
#  华深智药 · 密码自助重置  ——  一键部署 (Linux)
# ------------------------------------------------------------
#  用法：
#    bash deploy_linux.sh              # DEMO 模式：零配置，立即体验
#    bash deploy_linux.sh prod         # 生产模式（默认 SQLite）
#    DATABASE_URL=postgresql://u:p@h:5432/db  bash deploy_linux.sh prod   # 生产 + PostgreSQL
#
#  首次启动会【自动建表】，无需手动执行 SQL。
#  生产模式启动后，用 admin/admin 登录后台配置【域(AD)】与【阿里云短信】即可。
# ============================================================
set -e
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
cd "$(dirname "$0")/backend"
PY=.venv/bin/python
MODE="${1:-demo}"   # demo | prod

# 1) 虚拟环境
if [ ! -f "$PY" ]; then
    echo "[1/4] 创建虚拟环境..."
    python3 -m venv .venv
fi

# 2) 依赖
echo "[2/4] 安装依赖..."
$PY -m pip install -q -r requirements.txt

# 3) .env（首次运行自动生成，含强随机密钥）
if [ ! -f .env ]; then
    echo "[3/4] 生成 .env（随机密钥）..."
    SK=$($PY -c "import secrets;print(secrets.token_hex(32))")
    FK=$($PY -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())")
    if [ "$MODE" = "prod" ]; then
        DB="${DATABASE_URL:-sqlite:///ad_password.db}"
        cat > .env <<EOF
SECRET_KEY=$SK
SECRET_ENCRYPTION_KEY=$FK
DATABASE_URL=$DB
DEMO_MODE=false
HTTPS_ENABLED=true
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
    echo "[3/4] 已存在 .env，跳过生成"
fi

# 4) 启动（Linux 下 app.py 自动用 gunicorn；首次启动自动建表）
echo "[4/4] 启动服务..."
echo "--------------------------------------------"
if [ "$MODE" = "prod" ]; then
    echo " 生产模式 | DB: $(grep '^DATABASE_URL=' .env | cut -d= -f2-)"
    echo " >> 启动后访问 /login (admin/admin)，配置【域】与【短信】，并改 admin 口令"
else
    echo " DEMO 模式 | 演示账号：邮箱任意 + 手机号 13800000000（验证码见页面/控制台）"
fi
echo " 访问：http://127.0.0.1:5000/reset"
echo "--------------------------------------------"
exec $PY app.py
