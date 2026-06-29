# 域账号密码自助重置系统

> 面向远程/办公用户的 **忘记密码自助重置** 系统：用户输入邮箱与手机号，与域控（AD）登记信息校验后通过短信验证码重置密码。AD 密码改完后由 **Microsoft Entra Connect** 自动同步到 Azure AD（本系统不直连 AAD）。

![tech](https://img.shields.io/badge/Python-3.10+-blue) ![tech](https://img.shields.io/badge/Flask-3.0-green) ![tech](https://img.shields.io/badge/SQLite-默认-green) ![tech](https://img.shields.io/badge/ldap3-AD/LDAP-orange)

---

## ✨ 功能特性

- **公开 4 步重置向导**（无需登录）：邮箱 + 手机号强校验 AD → 短信验证码（60s 倒计时）→ 设新密码 → 动画成功页
- **域名自动生成 DN**：填域名即可，Base DN 和 Admin DN 自动生成
- **改密后验证**：用新密码做 LDAP 绑定确认密码确实生效
- **STARTTLS 支持**：AD 389 端口自动升级加密改密，无需开 636/LDAPS
- **三层限流**（原子行锁）：手机 60s 冷却 + 5 次/小时、邮箱 5 次/小时、IP 20 次/小时
- **IP 锁定**：身份校验失败 10 次/管理员登录失败 5 次 → 锁 IP 30/15 分钟
- **凭据加密**：AD 密码、阿里云 Secret 用 Fernet 加密存库；接口永不回传明文
- **CSRF 全量保护** · LDAP/SQL/XSS 注入防护 · 保护名单（默认挡 admin/Administrator）
- **管理员后台**：域配置（含连接测试）、短信配置（含发送测试）、保护名单管理（页面）、修改密码（页面）、员工域账号验证、操作日志（9 种事件筛选）
- **审计日志**：登录成功/失败、重置成功/失败、验证码错误、身份校验、短信故障、改密、保护名单更新
- **品牌化 UI**：LOGO + 蛋白分子结构（α-螺旋）p5.js 动态背景（本地化，无外部 CDN）
- **一键部署**：一条命令自动后台运行 + 端口检查 + stop/status 管理

## 🏗 架构

```
内网用户 ──HTTP──>  服务器:5000 (gunicorn)
外网用户 ──HTTPS──> [WAF（证书/TLS）] ──HTTP──> 服务器:5000
                                                    ├─ /reset        公开重置向导（未认证）
                                                    ├─ /login        管理员登录（IP 限流）
                                                    └─ /admin/*      管理后台（admin_required）
                                                          │
                                                          ├─ SQLite / PostgreSQL
                                                          ├─ AD/LDAP（查 mail+mobile、STARTTLS 改密、绑定验证）
                                                          └─ 阿里云短信（验证码 + 重置通知）
[Microsoft Entra Connect]  自动同步 AD 密码到 Azure AD
```
> 内网直连 HTTP + 外网 WAF 做 HTTPS 同时支持：`.env` 设 `HTTPS_ENABLED=false`。

**技术栈**：Flask 3 · Flask-SQLAlchemy · ldap3 · bcrypt · cryptography(Fernet) · 阿里云短信 SDK · SQLite（默认）/ PostgreSQL · p5.js

## 🚀 部署（一条命令，自动后台运行）

> 默认 **SQLite**、管理员 **admin / admin**，首次启动自动建表。

```bash
bash deploy_linux.sh prod
```

脚本自动：建虚拟环境 → 升级 pip → 装依赖 → 生成 `.env`（随机密钥）→ 强制 `DEMO_MODE=false` → 端口冲突检查 → **后台启动 gunicorn**。

### 访问
- 重置页：http://服务器IP:5000/reset
- 管理后台：http://服务器IP:5000/login → **`admin` / `admin`**

### 服务管理
| 操作 | 命令 |
|---|---|
| 查状态 | `bash deploy_linux.sh status` |
| 停止 | `bash deploy_linux.sh stop` |
| 重启 | 重新运行 `bash deploy_linux.sh prod`（自动停旧起新） |
| 查日志 | `tail -f backend/logs/app.log` |
| 换端口 | `SYSTEM_PORT=5001 bash deploy_linux.sh prod` |

### HTTPS（WAF）
服务器跑 HTTP:5000，WAF 回源并挂证书。防火墙把 5000 限制为只允许 WAF + 内网 IP。`.env` 设 `HTTPS_ENABLED=false`（同时支持 HTTP 直连 + WAF HTTPS）。

### 首次上线（登录后台后做 3 件事）
1. **🌐 域配置** → 填域名（DN 自动生成）→ 测试连接 → 🔍 员工账号验证
2. **💬 短信配置** → 填阿里云密钥 → 发送测试
3. **🔑 修改密码** → admin/admin 改成强口令

<details>
<summary>可选：自定义 admin 密码 / PostgreSQL / systemd / DEMO</summary>

```bash
ADMIN_PASSWORD=你的密码 bash deploy_linux.sh prod                    # 自定义 admin 口令
DATABASE_URL=postgresql://user:pwd@host:5432/db bash deploy_linux.sh prod  # PostgreSQL
sudo cp systemd/ad-password-manager.service /etc/systemd/system/ && sudo systemctl enable --now ad-password-manager  # 开机常驻
bash deploy_linux.sh                                                  # DEMO 体验
```
</details>

> AAD 同步由 Entra Connect 自动完成，云服务新密码约 2-3 分钟生效。

## 🔐 安全设计

| 维度 | 实现 |
|---|---|
| 凭据加密 | AD 密码、阿里云 Secret 用 Fernet 加密存库；接口永不回传明文 |
| 强校验 | 邮箱+手机必须与 AD 完全匹配才放行，不匹配直接拒绝 |
| 限流 | 手机/邮箱/IP 三维原子计数（行锁）；验证码 5 分钟有效、错 5 次锁定 |
| IP 锁定 | 身份校验失败 10 次→锁 30 分钟；管理员登录失败 5 次→锁 15 分钟 |
| 改密验证 | 改完后用新密码做 LDAP 绑定确认生效 |
| STARTTLS | 389 端口自动升级加密（AD 改密要求），无需开 636 |
| 注入防护 | LDAP 过滤器转义、ORM 防 SQL 注入、Jinja 防 XSS |
| 会话 | 10 分钟向导超时、一次性授权、session.clear() 防固定 |
| 重置目标 | 仅取自服务端 session，请求体无法越权指定 |
| CSRF | 所有 POST 受 Flask-WTF 保护 |
| 保护名单 | admin/Administrator/域管理员组不可自助重置（后台页面管理） |

## 📁 项目结构

```
ad2/
├── backend/
│   ├── app.py                  # Flask 入口（CSRF、安全头、ProxyFix、DEMO 种子）
│   ├── config.py               # 配置（环境变量驱动 + SQLite 超时）
│   ├── models/models.py        # ORM（Domain/SmsConfig 加密访问器、限流表）
│   ├── routes/
│   │   ├── reset.py            # 公开重置（状态门控 + IP 锁定 + 审计）
│   │   ├── ldap_auth.py        # 管理员登录（限流 + 防固定）
│   │   └── admin.py            # 后台（域/短信/保护名单/改密/验证/日志）
│   ├── services/
│   │   ├── reset_service.py    # 核心（匹配/发码/校验/重置/限流/锁定 并发安全）
│   │   ├── ldap_service.py     # AD 查找 + STARTTLS 改密 + 绑定验证
│   │   ├── sms_service.py      # 阿里云短信
│   │   ├── secret_crypto.py    # Fernet 加密
│   │   └── ldap_filter.py      # LDAP 注入转义
│   ├── templates/reset.html    # 重置页（蛋白背景 + 动画成功页）
│   └── static/                 # logo.png、bg.js（p5 蛋白螺旋）、p5.min.js
├── database/                   # init.sql + 迁移脚本
├── systemd/ · docs/ · wendang/
├── deploy_linux.sh · deploy_windows.bat
└── requirements.txt
```

## 📌 重要约定

- **admin 口令**：公开重置页拦截 admin（保护名单）；后台 🔑 修改密码 页直接改。
- **DEMO_MODE**：生产必须 `false`（部署脚本 prod 模式自动强制）。
- **HTTPS_ENABLED**：`false` = 同时支持 HTTP 直连 + WAF HTTPS；纯 HTTPS 改 `true`。
- **AAD**：依赖 Entra Connect；认证模式变更需重新评估。

## 📝 许可

内部使用。
