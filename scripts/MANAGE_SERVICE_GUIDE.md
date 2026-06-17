# Linux 服务管理脚本使用说明

## 📦 脚本清单

| 脚本名称 | 用途 | 说明 |
|---------|------|------|
| `manage_service.sh` | 服务管理 | 启动、停止、重启、状态查看等 |
| `install_service.sh` | 服务安装 | 安装/卸载 systemd 服务 |
| `start_linux.sh` | 一键启动 | 完整部署和启动流程 |

---

## 🚀 快速开始

### 1. 赋予执行权限

```bash
chmod +x *.sh
```

### 2. 安装 systemd 服务（推荐，首次部署）

```bash
# 安装服务
sudo ./install_service.sh install

# 查看状态
sudo ./install_service.sh status
```

### 3. 管理服务

```bash
# 使用 manage_service.sh（自动检测 systemd）
./manage_service.sh start
./manage_service.sh stop
./manage_service.sh restart
./manage_service.sh status

# 或直接用 systemctl（如果已安装 systemd 服务）
sudo systemctl start ad-password-manager
sudo systemctl stop ad-password-manager
sudo systemctl restart ad-password-manager
sudo systemctl status ad-password-manager
```

---

## 📖 详细用法

### manage_service.sh - 服务管理脚本

#### 基本命令

```bash
# 启动服务
./manage_service.sh start

# 停止服务
./manage_service.sh stop

# 重启服务
./manage_service.sh restart

# 查看状态
./manage_service.sh status

# 重新加载配置（不中断服务）
./manage_service.sh reload

# 查看日志
./manage_service.sh logs

# 清理临时文件
./manage_service.sh clean
```

#### 高级选项

```bash
# 指定运行模式
./manage_service.sh start --mode direct      # 强制使用直接模式
./manage_service.sh start --mode systemd     # 强制使用 systemd 模式

# 自定义端口和 worker 数量
./manage_service.sh start --port 8080 --workers 8

# 查看实时日志
./manage_service.sh logs -f                  # 实时跟踪所有日志
./manage_service.sh logs error -f            # 实时跟踪错误日志
./manage_service.sh logs access -n 100       # 查看最后 100 行访问日志

# 详细输出模式
./manage_service.sh status --verbose
```

#### 示例场景

**场景 1: 首次启动**
```bash
./manage_service.sh start
```

**场景 2: 修改配置后重启**
```bash
./manage_service.sh restart
```

**场景 3: 查看服务运行状态**
```bash
./manage_service.sh status
```

**场景 4: 排查问题**
```bash
# 实时查看错误日志
./manage_service.sh logs error -f

# 查看服务详细信息
./manage_service.sh status --verbose
```

**场景 5: 清理空间**
```bash
./manage_service.sh clean
```

---

### install_service.sh - systemd 服务安装脚本

#### 基本命令

```bash
# 安装 systemd 服务
sudo ./install_service.sh install

# 卸载服务
sudo ./install_service.sh uninstall

# 查看服务状态
sudo ./install_service.sh status

# 启用开机自启
sudo ./install_service.sh enable

# 禁用开机自启
sudo ./install_service.sh disable
```

#### 安装后的管理命令

安装完成后，可以使用以下系统命令：

```bash
# 启动服务
sudo systemctl start ad-password-manager

# 停止服务
sudo systemctl stop ad-password-manager

# 重启服务
sudo systemctl restart ad-password-manager

# 重新加载配置
sudo systemctl reload ad-password-manager

# 查看状态
sudo systemctl status ad-password-manager

# 查看日志
sudo journalctl -u ad-password-manager -f

# 查看最近 100 行日志
sudo journalctl -u ad-password-manager -n 100

# 禁用开机自启
sudo systemctl disable ad-password-manager

# 启用开机自启
sudo systemctl enable ad-password-manager
```

---

## 🔧 运行模式说明

### 1. systemd 模式（推荐生产环境）

**优点**:
- ✅ 开机自启
- ✅ 自动重启（崩溃后）
- ✅ 集中日志管理
- ✅ 资源限制和保护
- ✅ 标准化服务管理

**适用场景**: 生产环境、长期运行的服务

**安装方法**:
```bash
sudo ./install_service.sh install
```

### 2. 直接模式

**优点**:
- ✅ 无需 root 权限
- ✅ 简单快速
- ✅ 便于调试

**适用场景**: 开发环境、测试、临时运行

**使用方法**:
```bash
./manage_service.sh start --mode direct
```

---

## 📊 日志管理

### 日志文件位置

| 日志类型 | 文件路径 | 说明 |
|---------|---------|------|
| 应用日志 | `logs/app.log` | Flask 应用日志 |
| 访问日志 | `logs/access.log` | HTTP 请求日志 |
| 错误日志 | `logs/error.log` | 错误和异常日志 |
| 启动日志 | `logs/startup.log` | 启动过程日志 |
| Gunicorn 日志 | `logs/gunicorn.log` | Gunicorn 标准输出 |
| Gunicorn 错误 | `logs/gunicorn_error.log` | Gunicorn 错误日志 |

### 查看日志的方法

```bash
# 使用管理脚本
./manage_service.sh logs                    # 显示最近的日志
./manage_service.sh logs -f                 # 实时跟踪日志
./manage_service.sh logs error              # 查看错误日志
./manage_service.sh logs access -n 100      # 查看最近 100 行访问日志

# 使用 tail 命令
tail -f logs/error.log                      # 实时查看错误日志
tail -n 200 logs/access.log                 # 查看最近 200 行访问日志

# 使用 journalctl (systemd 模式)
sudo journalctl -u ad-password-manager -f   # 实时跟踪服务日志
sudo journalctl -u ad-password-manager \
    --since "2026-03-22 10:00:00"          # 查看特定时间日志
```

---

## 🎯 常见使用场景

### 场景 1: 日常启动/停止

```bash
# 早上启动服务
./manage_service.sh start

# 晚上下班停止服务
./manage_service.sh stop
```

### 场景 2: 更新代码后

```bash
# 方式 1: 使用 restart
./manage_service.sh restart

# 方式 2: 使用 systemctl (如果是 systemd 模式)
sudo systemctl restart ad-password-manager
```

### 场景 3: 排查问题

```bash
# 1. 查看状态
./manage_service.sh status

# 2. 实时查看错误日志
./manage_service.sh logs error -f

# 3. 检查端口占用
sudo ss -tulnp | grep :5000

# 4. 查看进程信息
ps aux | grep gunicorn
```

### 场景 4: 性能调优

```bash
# 增加 worker 数量（CPU 核心数 * 2 + 1）
./manage_service.sh restart --workers 8

# 或者修改配置文件后重新加载
vim backend/.env
./manage_service.sh reload
```

### 场景 5: 临时维护

```bash
# 1. 暂停服务（停止）
./manage_service.sh stop

# 2. 进行维护操作...

# 3. 恢复服务（启动）
./manage_service.sh start
```

---

## ⚙️ 配置选项

### manage_service.sh 配置

编辑脚本顶部的配置部分：

```bash
GUNICORN_WORKERS=4          # Worker 数量
GUNICORN_THREADS=2          # 每个 Worker 的线程数
GUNICORN_PORT=5000          # 监听端口
GUNICORN_HOST="0.0.0.0"     # 监听地址
```

### install_service.sh 配置

安装时会自动使用当前用户和项目路径，也可以手动修改生成的服务文件：

```bash
sudo vim /etc/systemd/system/ad-password-manager.service
```

---

## 🔐 安全建议

1. **使用 systemd 模式**: 提供更好的隔离和保护
2. **定期清理日志**: 避免日志文件过大
   ```bash
   ./manage_service.sh clean
   ```
3. **监控资源使用**: 
   ```bash
   ./manage_service.sh status
   ```
4. **限制访问权限**: 确保只有授权用户可以管理服务

---

## 🆘 故障排查

### 问题 1: 服务无法启动

```bash
# 1. 查看详细错误
./manage_service.sh logs error

# 2. 检查端口占用
sudo ss -tulnp | grep :5000

# 3. 检查依赖
source backend/venv/bin/activate
pip list | grep gunicorn
```

### 问题 2: systemd 服务未找到

```bash
# 重新安装服务
sudo ./install_service.sh uninstall
sudo ./install_service.sh install
```

### 问题 3: 权限错误

```bash
# 确保脚本有执行权限
chmod +x *.sh

# 如果使用 systemd，确保用户正确
sudo ./install_service.sh uninstall
sudo ./install_service.sh install
```

### 问题 4: 日志文件过大

```bash
# 清理旧日志
./manage_service.sh clean

# 或手动清理
find logs -name "*.log" -mtime +7 -delete
```

---

## 💡 最佳实践

### 开发环境

```bash
# 使用直接模式，便于调试
./manage_service.sh start --mode direct

# 实时查看日志
./manage_service.sh logs -f
```

### 测试环境

```bash
# 安装 systemd 服务
sudo ./install_service.sh install

# 使用标准命令管理
sudo systemctl restart ad-password-manager
```

### 生产环境

```bash
# 1. 安装 systemd 服务
sudo ./install_service.sh install

# 2. 启用开机自启
sudo systemctl enable ad-password-manager

# 3. 配置日志轮转
sudo vim /etc/logrotate.d/ad-password-manager

# 4. 设置监控告警
# (配置监控系统检查服务状态)
```

---

## 📚 相关文档

- [`LINUX_DEPLOYMENT.md`](LINUX_DEPLOYMENT.md) - 完整部署指南
- [`scripts/README_LINUX_TOOLS.md`](scripts/README_LINUX_TOOLS.md) - 工具包使用说明
- [`../wendang/生产环境部署指南.md`](wendang/生产环境部署指南.md) - 中文部署文档

---

## 🎉 总结

### 快速参考

```bash
# 日常管理三件套
./manage_service.sh start      # 启动
./manage_service.sh stop       # 停止
./manage_service.sh restart    # 重启

# 查看状态和日志
./manage_service.sh status     # 状态
./manage_service.sh logs -f    # 日志

# systemd 服务管理
sudo ./install_service.sh install    # 安装
sudo systemctl status ad-password-manager  # 查看
```

### 脚本选择

- **首次部署**: 使用 `start_linux.sh`
- **日常管理**: 使用 `manage_service.sh`
- **安装服务**: 使用 `install_service.sh`
- **遇到问题**: 先运行 `diagnose_environment.sh`

---

**祝您使用愉快！** 🚀
