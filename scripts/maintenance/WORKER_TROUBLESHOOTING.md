# Gunicorn Worker 启动失败问题解决方案

## 问题描述

在 Linux 系统下执行 `manage_service.sh restart` 时，出现以下错误:

```
gunicorn.errors.HaltServer: <HaltServer 'Worker failed to boot.' 3>
```

这表示 Gunicorn 的 worker 进程无法启动。

## 常见原因

1. **环境变量配置缺失** - 缺少必要的环境变量 (SECRET_KEY, DATABASE_URL)
2. **数据库连接失败** - 数据库服务未启动或配置错误
3. **依赖包缺失** - Python 依赖未正确安装
4. **端口被占用** - 5000 端口已被其他进程占用
5. **应用导入错误** - 代码中存在导入错误或语法错误
6. **Python 缓存问题** - __pycache__ 文件损坏

## 快速诊断

将 `diagnose_worker.sh` 脚本上传到 Linux 服务器并执行:

```bash
cd /home/ad2/backend
chmod +x diagnose_worker.sh
./diagnose_worker.sh
```

该脚本会自动检查:
- ✓ Python 虚拟环境
- ✓ Gunicorn 安装
- ✓ 环境变量配置
- ✓ 数据库连接
- ✓ 应用导入
- ✓ 端口占用
- ✓ 日志文件
- ✓ 依赖包

## 一键修复

将 `fix_worker.sh` 脚本上传到 Linux 服务器并执行:

```bash
cd /home/ad2/backend
chmod +x fix_worker.sh
./fix_worker.sh
```

该脚本会自动:
1. 停止现有服务
2. 清理残留进程
3. 重新安装依赖
4. 清理 Python 缓存
5. 验证环境变量
6. 测试数据库连接
7. 测试应用导入
8. 重新启动服务

## 手动排查步骤

### 1. 查看详细错误日志

```bash
# 查看错误日志
tail -f /home/ad2/logs/error.log

# 查看应用日志
tail -f /home/ad2/logs/app.log

# 查看最近 100 行日志
tail -n 100 /home/ad2/logs/error.log
```

### 2. 检查环境变量

```bash
cd /home/ad2/backend
cat .env
```

确保 `.env` 文件包含以下必要变量:

```bash
# 必须设置
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# 可选配置
PORT=5000
HOST=0.0.0.0
WORKERS=4
THREADS=2
HTTPS_ENABLED=false
```

### 3. 检查数据库连接

```bash
cd /home/ad2/backend
source venv/bin/activate

python -c "
from models.models import db
from config import Config
from flask import Flask

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    db.engine.connect()
    print('数据库连接成功!')
"
```

如果报错，请检查:
- 数据库服务是否运行
- DATABASE_URL 配置是否正确
- 数据库用户权限
- 防火墙设置

### 4. 检查依赖包

```bash
cd /home/ad2/backend
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 重新安装依赖
pip install -r requirements.txt

# 检查关键包
pip list | grep -E "flask|gunicorn|bcrypt|psycopg2"
```

### 5. 清理缓存

```bash
cd /home/ad2/backend

# 删除 Python 缓存
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete

# 清理日志 (可选)
rm -f logs/*.log.*
```

### 6. 测试单 worker 启动

```bash
cd /home/ad2/backend
source venv/bin/activate

# 使用单 worker 模式测试
gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 1 \
    --threads 2 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level debug \
    app:app
```

观察输出，看是否有具体的错误信息。

### 7. 检查端口占用

```bash
# 查看 5000 端口占用
ss -tulnp | grep :5000

# 或使用 netstat
netstat -tulnp | grep :5000

# 如果发现占用，杀死进程
kill -9 <PID>
```

### 8. 使用 systemd 模式 (推荐生产环境)

如果已安装 systemd 服务:

```bash
# 查看服务状态
systemctl status ad-password-manager

# 查看详细日志
journalctl -u ad-password-manager -f

# 重启服务
systemctl restart ad-password-manager
```

## 常见问题及解决方案

### 问题 1: SECRET_KEY 未设置

**错误信息:**
```
ValueError: ⚠️  生产环境必须设置 SECRET_KEY 环境变量!
```

**解决方案:**
```bash
cd /home/ad2/backend
echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" >> .env
```

### 问题 2: DATABASE_URL 配置错误

**错误信息:**
```
ValueError: ⚠️  生产环境必须设置 DATABASE_URL 环境变量!
```

**解决方案:**
编辑 `.env` 文件，设置正确的数据库连接字符串:
```bash
DATABASE_URL=postgresql://username:password@hostname:port/database_name
```

### 问题 3: psycopg2 未安装

**错误信息:**
```
ModuleNotFoundError: No module named 'psycopg2'
```

**解决方案:**
```bash
cd /home/ad2/backend
source venv/bin/activate
pip install psycopg2-binary
```

### 问题 4: 端口被占用

**错误信息:**
```
OSError: [Errno 98] Address already in use
```

**解决方案:**
```bash
# 查找占用端口的进程
lsof -i :5000

# 或
ss -tulnp | grep :5000

# 杀死进程
kill -9 <PID>

# 或更改端口
echo "PORT=5001" >> .env
```

### 问题 5: LDAP 配置错误导致启动失败

如果 LDAP 配置有误，可能在初始化时失败:

**解决方案:**
```bash
# 临时禁用 LDAP 检查 (仅用于测试启动)
# 编辑 routes/ldap_auth.py，注释掉初始化时的 LDAP 连接检查

# 或修正 LDAP 配置
cd /home/ad2/backend
cat .env | grep LDAP
```

## 预防措施

### 1. 使用 systemd 管理服务

创建 systemd 服务文件 `/etc/systemd/system/ad-password-manager.service`:

```ini
[Unit]
Description=AD Password Manager Service
After=network.target postgresql.service

[Service]
Type=notify
User=ad2
Group=ad2
WorkingDirectory=/home/ad2/backend
Environment="PATH=/home/ad2/backend/venv/bin"
ExecStart=/home/ad2/backend/venv/bin/gunicorn -c gunicorn_config.py app:app
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

然后:
```bash
systemctl daemon-reload
systemctl enable ad-password-manager
systemctl start ad-password-manager
```

### 2. 配置 Gunicorn 配置文件

创建 `gunicorn_config.py`:

```python
import multiprocessing

# 绑定地址
bind = "0.0.0.0:5000"

# Worker 数量
workers = multiprocessing.cpu_count() * 2 + 1

# Worker 类型
worker_class = "sync"

# 线程数
threads = 2

# 超时时间
timeout = 120

# 日志配置
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"

# 进程命名
proc_name = "ad-password-manager"

# PID 文件
pidfile = "logs/gunicorn.pid"

# 守护进程
daemon = False

# 预加载应用
preload_app = True
```

### 3. 设置日志轮转

创建 `/etc/logrotate.d/ad-password-manager`:

```
/home/ad2/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 ad2 ad2
    postrotate
        systemctl reload ad-password-manager > /dev/null 2>&1 || true
    endscript
}
```

## 调试技巧

### 1. 增加日志级别

在 `.env` 中设置:
```bash
LOG_LEVEL=DEBUG
```

### 2. 前台运行查看实时日志

```bash
cd /home/ad2/backend
source venv/bin/activate

gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 1 \
    --access-logfile - \
    --error-logfile - \
    --log-level debug \
    app:app
```

### 3. 使用 strace 跟踪系统调用

```bash
cd /home/ad2/backend
source venv/bin/activate

strace -f -o /tmp/gunicorn_strace.log \
    gunicorn --bind 0.0.0.0:5000 --workers 1 app:app
```

### 4. 检查资源限制

```bash
# 查看 ulimit
ulimit -a

# 特别是文件描述符限制
ulimit -n

# 如果太低，可以临时提高
ulimit -n 65536
```

## 联系支持

如果以上方法都无法解决问题，请收集以下信息:

1. 完整的错误日志 (`logs/error.log`)
2. 应用日志 (`logs/app.log`)
3. 系统日志 (`journalctl -xe`)
4. 环境变量配置 (隐藏敏感信息)
5. Python 版本 (`python --version`)
6. 操作系统版本 (`cat /etc/os-release`)

然后寻求进一步的技术支持。
