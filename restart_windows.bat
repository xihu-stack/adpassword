@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ========================================
echo   AD 密码管理系统 - 重启脚本 (Windows)
echo ========================================
echo.

echo [1/7] 停止现有进程...
echo.

REM 停止 Python 进程（不检查错误）
taskkill /F /IM python.exe >nul 2>&1
if %errorLevel% equ 0 (
    echo ✓ Python 进程已停止
) else (
    echo ℹ 未找到 Python 进程
)

REM 停止 Node.js 进程（不检查错误）
taskkill /F /IM node.exe >nul 2>&1
if %errorLevel% equ 0 (
    echo ✓ Node.js 进程已停止
) else (
    echo ℹ 未找到 Node.js 进程
)

timeout /t 2 /nobreak >nul

echo.
echo [2/7] 检查运行环境...
echo.

REM 检查 Python
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ✗ 错误：未找到 Python 环境
    echo 请先安装 Python 3.8 或更高版本
    pause
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('python --version') do echo ✓ Python 环境：%%i
)

REM 检查 Node.js
node --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ✗ 错误：未找到 Node.js 环境
    echo 请先安装 Node.js 16 或更高版本
    pause
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('node --version') do echo ✓ Node.js 环境：%%i
)

REM 检查 npm
npm --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ✗ 错误：未找到 npm
    pause
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('npm --version') do echo ✓ npm 版本：%%i
)

echo.
echo [3/7] 清理端口占用...
echo.

REM 清理 5000 端口
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000') do (
    echo ℹ 清理端口 5000 的占用进程 %%a
    taskkill /F /PID %%a >nul 2>&1
)

timeout /t 2 /nobreak >nul
echo ✓ 端口清理完成

echo.
echo [4/7] 启动后端服务...
echo.

cd /d "%~dp0backend"

REM 检查环境配置
if not exist ".env" (
    echo ⚠️  未找到 .env 配置文件
    echo 正在从 .env.example 创建...
    copy .env.example .env >nul
    echo ✗ 请编辑 .env 文件配置必要的环境变量
    pause
    exit /b 1
)

echo ℹ 后端工作目录：%cd%
echo ℹ 启动命令：python app.py
echo.

REM 启动后端（新窗口，启动后等待 3 秒）
start "AD 密码管理系统 - 后端服务" cmd /k "cd /d %cd% && python app.py"

echo ✓ 后端服务已启动，等待初始化...
timeout /t 5 /nobreak >nul

echo.
echo [5/7] 启动前端服务...
echo.

cd /d "%~dp0frontend"

echo ℹ 前端工作目录：%cd%
echo ℹ 启动命令：npm run dev
echo.

REM 启动前端（新窗口，启动后等待 5 秒）
start "AD 密码管理系统 - 前端服务" cmd /k "cd /d %cd% && npm run dev"

echo ✓ 前端服务已启动，等待初始化...
timeout /t 8 /nobreak >nul

echo.
echo [6/7] 检查服务状态...
echo.

REM 等待服务完全启动
timeout /t 3 /nobreak >nul

REM 检查后端
netstat -ano | findstr :5000 >nul 2>&1
if %errorLevel% equ 0 (
    echo ✓ 后端服务运行正常（端口 5000）
) else (
    echo ✗ 后端服务启动失败
)

echo.
echo [7/7] 完成！

echo.
echo ========================================
echo   🎉 项目重启完成！
echo ========================================
echo.
echo 访问地址：
echo   前端界面：http://localhost:前端端口（查看控制台输出）
echo   后端 API：http://localhost:5000
echo   健康检查：http://localhost:5000/health
echo.
echo 提示：
echo   - 后端和前端服务已在新窗口打开
echo   - 关闭窗口可停止对应服务
echo   - 查看日志请在对应窗口查看
echo.
echo 按任意键退出...
pause >nul
