@echo off
:: ============================================================
::  华深智药 · 密码自助重置  ——  一键部署 (Windows)
:: ------------------------------------------------------------
::  用法：
::    deploy_windows.bat            DEMO 模式：零配置，立即体验
::    deploy_windows.bat prod       生产模式（默认 SQLite）
::    set DATABASE_URL=postgresql://u:p@h:5432/db ^&^& deploy_windows.bat prod
::  首次启动自动建表，无需手动 SQL。
:: ============================================================
setlocal enabledelayedexpansion
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set MODE=%1
if "%MODE%"=="" set MODE=demo

cd /d "%~dp0backend"
set PY=.venv\Scripts\python.exe

if not exist "%PY%" (
    echo [1/4] 创建虚拟环境...
    python -m venv .venv
)

echo [2/4] 安装依赖...
"%PY%" -m pip install -q -r requirements.txt

if not exist ".env" (
    echo [3/4] 生成 .env（随机密钥）...
    for /f "delims=" %%k in ('"%PY%" -c "import secrets;print(secrets.token_hex(32))"') do set SK=%%k
    for /f "delims=" %%k in ('"%PY%" -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"') do set FK=%%k
    if /I "%MODE%"=="prod" (
        if "%DATABASE_URL%"=="" set DATABASE_URL=sqlite:///ad_password.db
        > ".env" (
            echo SECRET_KEY=!SK!
            echo SECRET_ENCRYPTION_KEY=!FK!
            echo DATABASE_URL=!DATABASE_URL!
            echo DEMO_MODE=false
            echo HTTPS_ENABLED=true
            echo SESSION_TIMEOUT=8
            echo CORS_ORIGINS=
            echo PASSWORD_MIN_LENGTH=8
            echo PASSWORD_REQUIRE_UPPERCASE=true
            echo PASSWORD_REQUIRE_LOWERCASE=true
            echo PASSWORD_REQUIRE_NUMBER=true
            echo PASSWORD_REQUIRE_SPECIAL=true
        )
    ) else (
        > ".env" (
            echo SECRET_KEY=!SK!
            echo SECRET_ENCRYPTION_KEY=!FK!
            echo DATABASE_URL=sqlite:///ad_demo.db
            echo DEMO_MODE=true
            echo CORS_ORIGINS=
        )
    )
) else (
    echo [3/4] 已存在 .env，跳过生成
)

echo [4/4] 启动服务（首次启动自动建表）...
echo --------------------------------------------
if /I "%MODE%"=="prod" (
    echo  生产模式 ^| 启动后访问 /login ^(admin/admin^)，配置【域】与【短信】，并改 admin 口令
) else (
    echo  DEMO 模式 ^| 演示账号：邮箱任意 + 手机号 13800000000
)
echo  访问：http://127.0.0.1:5000/reset
echo --------------------------------------------
"%PY%" app.py
endlocal
