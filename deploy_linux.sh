#!/bin/bash
# AD 密码自助重置系统 - 一键部署 (Linux)
set -e
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

cd "$(dirname "$0")/backend"
PY=.venv/bin/python

# 1) 虚拟环境
if [ ! -f "$PY" ]; then
    echo "[1/4] 创建虚拟环境..."
    python3 -m venv .venv
fi

# 2) 依赖
echo "[2/4] 安装依赖..."
$PY -m pip install -q -r requirements.txt

# 3) .env（首次运行生成；默认演示模式，开箱即用）
if [ ! -f .env ]; then
    echo "[3/4] 生成 .env（DEMO_MODE=true，SQLite）..."
    FKEY=$($PY -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    cat > .env <<EOF
SECRET_KEY=please-change-this-secret-key-in-production
DATABASE_URL=sqlite:///ad_demo.db
SECRET_ENCRYPTION_KEY=$FKEY
DEMO_MODE=true
CORS_ORIGINS=
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBER=true
PASSWORD_REQUIRE_SPECIAL=true
EOF
else
    echo "[3/4] 已存在 .env，跳过生成"
fi

# 4) 启动
echo "[4/4] 启动服务..."
echo "--------------------------------------------"
echo " 重置页面: http://127.0.0.1:5000/reset"
echo " 管理后台: http://127.0.0.1:5000/   (admin / admin)"
echo " 演示账号: 邮箱任意 + 手机号 13800000000"
echo " 演示验证码会显示在页面提示和本控制台"
echo "--------------------------------------------"
exec $PY app.py
