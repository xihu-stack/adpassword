@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
echo ============================================
echo   AD 密码自助重置系统 - 一键部署 (Windows)
echo ============================================

cd /d "%~dp0backend"
set PY=.venv\Scripts\python.exe

REM 1) 虚拟环境
if not exist "%PY%" (
    echo [1/4] 创建虚拟环境...
    python -m venv .venv
)

REM 2) 依赖
echo [2/4] 安装依赖...
"%PY%" -m pip install -q -r requirements.txt

REM 3) .env（首次运行生成；默认演示模式，开箱即用）
if not exist ".env" (
    echo [3/4] 生成 .env（DEMO_MODE=true，SQLite）...
    "%PY%" -c "from cryptography.fernet import Fernet; open('_key.txt','w').write(Fernet.generate_key().decode())"
    set /p FKEY=<_key.txt
    del _key.txt
    > ".env" (
        echo SECRET_KEY=please-change-this-secret-key-in-production
        echo DATABASE_URL=sqlite:///ad_demo.db
        echo SECRET_ENCRYPTION_KEY=!FKEY!
        echo DEMO_MODE=true
        echo CORS_ORIGINS=
        echo PASSWORD_MIN_LENGTH=8
        echo PASSWORD_REQUIRE_UPPERCASE=true
        echo PASSWORD_REQUIRE_LOWERCASE=true
        echo PASSWORD_REQUIRE_NUMBER=true
        echo PASSWORD_REQUIRE_SPECIAL=true
    )
) else (
    echo [3/4] 已存在 .env，跳过生成
)

REM 4) 启动
echo [4/4] 启动服务...
echo --------------------------------------------
echo  重置页面: http://127.0.0.1:5000/reset
echo  管理后台: http://127.0.0.1:5000/   (admin / admin)
echo  演示账号: 邮箱任意 + 手机号 13800000000
echo  演示验证码会显示在页面提示和本控制台
echo --------------------------------------------
"%PY%" app.py
endlocal
