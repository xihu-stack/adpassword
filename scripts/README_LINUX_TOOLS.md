# Linux 部署工具包使用说明

## 📦 工具包清单

本项目为 Linux 部署提供了完整的工具包，包含以下脚本和配置文件：

### 核心脚本

| 脚本名称 | 用途 | 说明 |
|---------|------|------|
| `start_linux.sh` | 一键启动 | 自动化部署和启动应用 |
| `fix_frontend_build.sh` | 前端修复 | 解决 npm rollup 模块问题 |
| `diagnose_environment.sh` | 环境诊断 | 检查系统环境和配置问题 |

### 配置文件

| 文件路径 | 用途 |
|---------|------|
| `systemd/ad-password-manager.service` | systemd 服务配置 |
| `nginx/nginx.conf.example` | Nginx 反向代理配置 |

---

## 🚀 快速开始

### 步骤 1: 上传项目到 Linux 服务器

```bash
# 使用 scp、rsync 或 Git 克隆等方式上传项目
scp -r ad2 user@your-server:/home/ad2/
```

### 步骤 2: 赋予脚本执行权限

```bash
cd /home/ad2/ad2
chmod +x start_linux.sh fix_frontend_build.sh diagnose_environment.sh
```

### 步骤 3: 诊断环境（可选但推荐）

```bash
./diagnose_environment.sh
```

该脚本会检查：
- ✅ Python 环境
- ✅ Node.js 和 npm
- ✅ 前端依赖完整性
- ✅ 后端配置文件
- ✅ Python 依赖包
- ✅ 日志目录权限
- ✅ 端口占用情况

### 步骤 4: 启动应用

```bash
./start_linux.sh
```

启动成功后访问：`http://localhost:5000`

**默认账号**: `admin`  
**默认密码**: `admin`

---

## 🔧 常见问题与解决方案

### 问题 1: Rollup 模块错误

**症状**:
```
Error: Cannot find module @rollup/rollup-linux-x64-gnu
```

**原因**: 
npm 的可选依赖存在 bug，导致某些平台特定的模块未正确安装。

**解决方案**:

#### 方案 A: 使用自动修复脚本（推荐）

```bash
./fix_frontend_build.sh
```

该脚本会自动：
1. 清理旧的 node_modules 和 package-lock.json
2. 清理 npm 缓存
3. 重新安装依赖
4. 验证 Rollup 模块
5. 测试构建

#### 方案 B: 手动修复

```bash
cd frontend
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
npm run build
```

#### 方案 C: 让启动脚本自动处理

`start_linux.sh` 已包含自动检测和修复功能，会在构建前端前检查 Rollup 模块完整性。

---

### 问题 2: 数据库连接失败

**症状**:
```
SQLAlchemy Error: Could not connect to database
```

**解决方案**:

1. 编辑配置文件：
```bash
vim backend/.env
```

2. 修改数据库连接字符串：
```ini
# PostgreSQL 示例
DATABASE_URL=postgresql://postgres:password@192.168.1.227/ad_password_db

# MySQL 示例
DATABASE_URL=mysql+pymysql://root:password@192.168.1.227/ad_password_db

# SQL Server 示例
DATABASE_URL=mssql+pyodbc://sa:password@192.168.1.227/ad_password_db?driver=ODBC+Driver+17+for+SQL+Server
```

3. 测试数据库连接：
```bash
# 确保数据库服务器可访问
ping 192.168.1.227

# 测试端口连通性
telnet 192.168.1.227 5432
```

---

### 问题 3: 端口被占用

**症状**:
```
Address already in use: 0.0.0.0:5000
```

**解决方案**:

#### 方案 A: 查找并停止占用进程

```bash
# 查找占用端口的进程
sudo ss -tulnp | grep :5000
sudo kill <PID>
```

#### 方案 B: 修改应用端口

在数据库中修改配置（需要先能连接数据库）：
```sql
UPDATE system_settings 
SET setting_value = '8080' 
WHERE setting_key = 'system_port';
```

或在启动时指定（修改 start_linux.sh）：
```bash
gunicorn --bind 0.0.0.0:8080 ...
```

---

### 问题 4: Python 依赖安装失败

**症状**:
```
ERROR: Could not find a version that satisfies the requirement xxx
```

**解决方案**:

1. 升级 pip：
```bash
source backend/venv/bin/activate
pip install --upgrade pip
```

2. 安装系统依赖（Ubuntu/Debian）：
```bash
sudo apt-get update
sudo apt-get install python3-pip python3-venv python3-dev libpq-dev gcc
```

3. 安装系统依赖（CentOS/RHEL）：
```bash
sudo yum install python3-pip python3-virtualenv python3-devel postgresql-devel gcc
```

---

## 📝 注册为系统服务

### 1. 配置 systemd 服务

编辑服务文件（替换实际路径）：
```bash
sudo vim /etc/systemd/system/ad-password-manager.service
```

参考 `systemd/ad-password-manager.service` 模板，修改以下内容：
- `WorkingDirectory`: 项目后端目录绝对路径
- `Environment`: 虚拟环境路径
- `ExecStart`: Gunicorn 完整路径

### 2. 启用服务

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启用服务
sudo systemctl enable ad-password-manager

# 启动服务
sudo systemctl start ad-password-manager

# 查看状态
sudo systemctl status ad-password-manager
```

### 3. 服务管理

```bash
# 停止服务
sudo systemctl stop ad-password-manager

# 重启服务
sudo systemctl restart ad-password-manager

# 查看日志
sudo journalctl -u ad-password-manager -f
```

---

## 🔐 生产环境建议

### 1. 使用 Nginx 反向代理

参考 `nginx/nginx.conf.example` 配置：

```bash
sudo cp nginx/nginx.conf.example /etc/nginx/sites-available/ad-password-manager
sudo ln -s /etc/nginx/sites-available/ad-password-manager /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2. 配置防火墙

```bash
# Ubuntu (UFW)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# CentOS (firewalld)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 3. 禁用 SELinux（如遇到问题）

```bash
# 临时禁用
sudo setenforce 0

# 永久禁用
sudo sed -i 's/SELINUX=enforcing/SELINUX=permissive/' /etc/selinux/config
```

---

## 📊 日志管理

### 日志位置

| 日志类型 | 文件路径 |
|---------|---------|
| 启动日志 | `logs/startup.log` |
| 应用日志 | `logs/app.log` |
| 访问日志 | `logs/access.log` |
| 错误日志 | `logs/error.log` |
| Gunicorn 日志 | `logs/gunicorn.log` |

### 查看日志

```bash
# 实时查看错误日志
tail -f logs/error.log

# 查看最近 100 行
tail -n 100 logs/app.log

# 搜索特定关键词
grep "ERROR" logs/app.log
```

---

## 🛠️ 维护命令

### 更新应用

```bash
# 1. 停止服务
sudo systemctl stop ad-password-manager

# 2. 更新代码
git pull  # 或重新上传文件

# 3. 重新安装依赖
./start_linux.sh

# 4. 启动服务
sudo systemctl start ad-password-manager
```

### 备份数据库

```bash
# PostgreSQL 备份
pg_dump -h 192.168.1.227 -U postgres ad_password_db > backup_$(date +%Y%m%d).sql

# MySQL 备份
mysqldump -h 192.168.1.227 -u root -p ad_password_db > backup_$(date +%Y%m%d).sql
```

### 恢复数据库

```bash
psql -h 192.168.1.227 -U postgres ad_password_db < backup_20260322.sql
# 或
mysql -h 192.168.1.227 -u root -p ad_password_db < backup_20260322.sql
```

---

## 📞 故障排查流程

1. **运行诊断脚本**:
   ```bash
   ./diagnose_environment.sh
   ```

2. **查看详细日志**:
   ```bash
   tail -f logs/error.log
   ```

3. **检查服务状态**:
   ```bash
   sudo systemctl status ad-password-manager
   ```

4. **测试数据库连接**:
   ```bash
   psql -h 192.168.1.227 -U postgres -d ad_password_db
   ```

5. **检查端口监听**:
   ```bash
   ss -tulnp | grep :5000
   ```

6. **检查防火墙**:
   ```bash
   sudo ufw status
   # 或
   sudo firewall-cmd --list-all
   ```

---

## 📚 相关文档

- [`LINUX_DEPLOYMENT.md`](LINUX_DEPLOYMENT.md) - 详细部署指南
- [`../wendang/生产环境部署指南.md`](wendang/生产环境部署指南.md) - 中文部署文档
- [`../docs/nginx.conf.example`](docs/nginx.conf.example) - Nginx 配置示例

---

## 💡 提示

1. **首次部署**: 建议先运行 `diagnose_environment.sh` 检查环境
2. **前端构建问题**: 直接运行 `fix_frontend_build.sh` 即可解决大部分问题
3. **生产环境**: 务必使用 systemd 管理服务，配置 Nginx 反向代理和 HTTPS
4. **定期备份**: 设置定时任务备份数据库和配置文件
5. **监控日志**: 配置日志轮转，定期检查错误日志

---

**祝您部署顺利！** 🎉
