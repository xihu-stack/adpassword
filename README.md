# 华深智药 · 域账号密码自助重置系统

> 面向远程/办公用户的 **忘记密码自助重置** 系统：用户输入邮箱与手机号，与域控（AD）登记信息校验后通过短信验证码重置密码。AD 密码改完后由 **Microsoft Entra Connect** 自动同步到 Azure AD（本系统不直连 AAD）。

![tech](https://img.shields.io/badge/Python-3.10+-blue) ![tech](https://img.shields.io/badge/Flask-3.0-green) ![tech](https://img.shields.io/badge/PostgreSQL-15-blue) ![tech](https://img.shields.io/badge/ldap3-AD/LDAP-orange)

---

## ✨ 功能特性

- **公开 4 步重置向导**（无需登录）：邮箱 + 手机号匹配 AD → 短信验证码 → 设新密码
- **防用户枚举**：匹配/不匹配返回统一文案、静默不发；生产环境短信异步发送抹平时序差
- **三层限流**（原子行锁）：手机号 60s 冷却 + 5 次/小时、邮箱 5 次/小时、IP 20 次/小时
- **安全**：凭据 Fernet 加密存储、CSRF 全量保护、LDAP 注入转义、保护名单（默认挡 admin/Administrator）、禁用账号拒绝、验证码 bcrypt 哈希 + 5 次锁定
- **管理员后台**（精简）：域配置、短信配置、保护名单管理、操作日志
- **品牌化 UI**：华深智药 LOGO + 蛋白分子结构（α-螺旋）动态背景（p5.js 本地化，无外部 CDN）
- **一键部署**：Windows `.bat` / Linux `.sh`，开箱即用的 DEMO 模式

## 🏗 架构

```
[公网用户] ──HTTPS──> [Nginx] ──> [Flask (gunicorn/waitress)]
                                    ├─ /reset        公开重置向导（未认证）
                                    ├─ /login        管理员登录
                                    └─ /admin/*      管理后台（admin_required）
                                          │
                                          ├─ PostgreSQL（用户/域/短信配置/日志/限流）
                                          ├─ AD/LDAP（查 mail+mobile、改 unicodePwd）
                                          └─ 阿里云短信（验证码）
[Microsoft Entra Connect]  自动把新 AD 密码同步到 Azure AD（应用不参与）
```

**技术栈**：Flask 3 · Flask-SQLAlchemy · ldap3 · bcrypt · cryptography(Fernet) · 阿里云短信 SDK · PostgreSQL · p5.js（背景）

## 🚀 快速部署（一条命令）

> **首次启动自动建表，无需手动执行 SQL**（迁移 SQL 仅用于升级旧库）。

**DEMO 模式**（零配置，立即体验；不连真实 AD/短信）：
```bash
bash deploy_linux.sh          # Linux
# 或 Windows: 双击 deploy_windows.bat
```

**生产模式**（默认 SQLite；想用 PostgreSQL 就传入 `DATABASE_URL`）：
```bash
# 最简：本地 SQLite
bash deploy_linux.sh prod

# PostgreSQL（推荐）
DATABASE_URL=postgresql://user:pwd@host:5432/ad_password_db bash deploy_linux.sh prod
```

脚本自动完成：建虚拟环境 → 装依赖 → 生成 `.env`（强随机 `SECRET_KEY` + Fernet 密钥）→ 启动（Linux 自动用 gunicorn）。

启动后：
- 重置页：http://127.0.0.1:5000/reset
- 管理后台：http://127.0.0.1:5000/login（`admin` / `admin`）

> **生产模式上线 3 件事**（登录后台后）：① 配置【域】(AD 绑定账号) ② 配置【阿里云短信】 ③ 改 admin 口令。
> AAD 同步由 Entra Connect 自动完成，云服务新密码约 2-3 分钟生效。

### 可选：systemd + nginx（生产长跑）
- systemd：改 `systemd/ad-password-manager.service` 里的路径 → `systemctl enable --now ad-password-manager`
- nginx：参考 `docs/nginx.conf.example` 做 HTTPS 反代到 127.0.0.1:5000

<details>
<summary>手动部署（不用脚本）</summary>

```bash
git clone <repo> && cd ad2/backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.production.example .env   # 填 SECRET_KEY / SECRET_ENCRYPTION_KEY / DATABASE_URL，DEMO_MODE=false
.venv/bin/python app.py           # 首次启动自动建表；或 gunicorn -b 127.0.0.1:5000 -w4 app:app
```
升级旧库时才需：`psql -f database/2026-06-17-reset-migration.sql`
</details>

## 🔐 安全设计

| 维度 | 实现 |
|---|---|
| 凭据加密 | AD 绑定密码、阿里云 AccessKey Secret 用 Fernet 加密存库；接口永不回传明文 |
| 防枚举 | 统一文案 + 静默不发；短信异步发送抹平时序 |
| 限流 | 手机/邮箱/IP 三维原子计数（行锁）；验证码 5 分钟有效、错 5 次锁定 |
| 注入防护 | LDAP 过滤器转义（`escape_ldap`）；ORM 防 SQL 注入；Jinja 自动转义防 XSS |
| 会话 | 10 分钟向导超时；一次性授权；管理员登录 `session.clear()` 防固定 |
| 重置目标 | 仅取自服务端 session，请求体无法越权指定 |
| CSRF | 所有 POST（重置/登录/admin）受 Flask-WTF 保护 |
| 保护名单 | admin/Administrator/域管理员组不可自助重置 |

## 📁 项目结构

```
ad2/
├── backend/
│   ├── app.py                  # Flask 入口（蓝图注册、CSRF、安全头、ProxyFix）
│   ├── config.py               # 配置（环境变量驱动）
│   ├── models/models.py        # ORM 模型（凭据加密访问器）
│   ├── routes/
│   │   ├── reset.py            # 公开重置向导（状态门控）
│   │   ├── ldap_auth.py        # 管理员登录
│   │   └── admin.py            # 精简管理后台
│   ├── services/
│   │   ├── reset_service.py    # 核心：匹配/发码/校验/重置/限流（并发安全）
│   │   ├── ldap_service.py     # AD 查找 + 按 DN 改密（多主机故障转移）
│   │   ├── sms_service.py      # 阿里云短信
│   │   ├── secret_crypto.py    # Fernet 加密
│   │   └── ldap_filter.py      # LDAP 注入转义
│   ├── templates/reset.html    # 重定向页（蛋白背景）
│   ├── static/                 # logo.png、bg.js（p5 蛋白螺旋）、p5.min.js
│   └── tests/                  # pytest（34 用例）
├── database/                   # init.sql + 迁移脚本
├── systemd/ · nginx/ · docs/ · wendang/
├── deploy_windows.bat · deploy_linux.sh
└── requirements.txt
```

## 🧪 测试

```bash
cd backend && .venv/bin/python -m pytest tests/ -v      # Linux
# 或 Windows: .venv\Scripts\python.exe -m pytest tests/ -v
```
覆盖：限流（预留/退还/冷却）、身份匹配（保护名单/禁用/规整）、发码校验（锁定/过期/重发失效）、重置（策略/AD 失败）、路由门控（越步/越权/一次性）、防枚举时序、加密、CSRF。

## 📌 重要约定

- **admin 口令**：公开重置页拦截 admin（保护名单）；忘记 admin 口令用 `backend/init_admin_password.py` 重置。
- **演示模式** 仅用于体验，生产必须 `DEMO_MODE=false`。
- **AAD** 依赖 Entra Connect；若认证模式变更需重新评估。

## 📝 许可

内部使用。
