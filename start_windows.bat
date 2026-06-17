@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ╔══════════════════════════════════════════════════════════╗
:: ║                                                          ║
:: ║          AD 密码管理系统 - 一键启动脚本 (Windows)        ║
:: ║          Version 2.0  |  2026                            ║
:: ║                                                          ║
:: ╚══════════════════════════════════════════════════════════╝

:: 颜色设置
color 0A

:: 清屏
cls

:: 设置控制台标题
title AD 密码管理系统 - 一键启动控制台

:: 显示启动横幅
echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║                                                          ║
echo ║          AD 密码管理系统 - 一键启动脚本                  ║
echo ║          Version 2.0  |  Windows                         ║
echo ║                                                          ║
echo ══════════════════════════════════════════════════════════╝
echo.

:: 获取脚本所在目录
set SCRIPT_DIR=%~dp0
set BACKEND_DIR=%SCRIPT_DIR%backend
set FRONTEND_DIR=%SCRIPT_DIR%frontend

:: 检查 Python 环境
echo [1/6] 检查 Python 环境...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误：未检测到 Python 环境，请先安装 Python 3.8+
    pause
    exit /b 1
)

python --version
echo ✅ Python 环境检查通过
echo.

:: 检查 Node.js 环境
echo [2/6] 检查 Node.js 环境...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误：未检测到 Node.js 环境，请先安装 Node.js 16+
    pause
    exit /b 1
)

node --version
echo ✅ Node.js 环境检查通过
echo.

:: 检查并安装 Python 依赖
echo [3/6] 检查 Python 依赖...
if not exist "%BACKEND_DIR%\.venv" (
    echo ⚙️  正在创建虚拟环境...
    cd /d "%BACKEND_DIR%"
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo ❌ 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo ✅ 虚拟环境创建成功
)

echo ⚙️  正在安装/更新 Python 依赖...
cd /d "%BACKEND_DIR%"
call .venv\Scripts\activate.bat
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo ❌ 安装依赖失败
    pause
    exit /b 1
)
echo ✅ Python 依赖安装完成
echo.

:: 检查并安装 Node.js 依赖
echo [4/6] 检查 Node.js 依赖...
if not exist "%FRONTEND_DIR%\node_modules" (
    echo ⚙️  正在安装前端依赖（首次启动可能需要几分钟）...
    cd /d "%FRONTEND_DIR%"
    call npm install
    if %errorlevel% neq 0 (
        echo ❌ 安装前端依赖失败
        pause
        exit /b 1
    )
    echo ✅ 前端依赖安装完成
) else (
    echo ✅ 前端依赖已安装
)
echo.

:: 构建前端
echo [5/6] 构建前端...
cd /d "%FRONTEND_DIR%"
call npm run build
if %errorlevel% neq 0 (
    echo ❌ 前端构建失败
    pause
    exit /b 1
)
echo ✅ 前端构建完成
echo.

:: 启动后端服务
echo [6/6] 启动后端服务...
cd /d "%BACKEND_DIR%"
call .venv\Scripts\activate.bat

:: 设置环境变量
set FLASK_APP=app.py
set FLASK_ENV=production

:: 启动 Flask 应用
echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║                                                          ║
echo ║  ✅ 系统启动成功！                                       ║
echo ║                                                          ║
echo   📍 访问地址：http://127.0.0.1:5000                      ║
echo ║  📍 局域网访问：http://%COMPUTERNAME%:5000               ║
echo ║                                                          ║
echo ║  👤 默认账号：admin                                      ║
echo ║  🔑 默认密码：admin                                      ║
echo ║                                                          ║
echo   ⚠️  首次登录后请立即修改密码！                          ║
echo ║                                                          ║
echo   按 Ctrl+C 停止服务                                      ║
echo ║                                                          ║
echo ══════════════════════════════════════════════════════════╝
echo.

:: 使用虚拟环境中的 Python 解释器
.venv\Scripts\python app.py

:: 服务停止后的清理
echo.
echo 服务已停止
pause
