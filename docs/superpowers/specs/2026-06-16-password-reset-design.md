# 域控密码自助重置系统 — 设计文档

- **日期**: 2026-06-16
- **状态**: 待评审
- **作者**: 设计 brainstorming 会话产出

---

## 1. 背景与目标

将现有"登录 + MFA + 自助改密"系统，重构为面向**不在内网的员工**的**忘记密码自助重置**系统：用户只需提供邮箱和手机号，系统与 AD 中登记的 `mail` / `mobile` 校验，通过后发短信验证码，验证通过即可重置域控密码。AD 密码改完后由已有的 Microsoft Entra Connect 自动同步到 AAD。

**核心目标**：让忘记密码的远程用户，不依赖内网、不依赖 IT 人工，自助重置域账号密码。

---

## 2. 范围

### 2.1 本次做（In Scope）

- 新增公开（未认证）的 4 步重置向导：身份匹配 → 发码 → 校验 → 重置。
- 后端新蓝图 `reset_bp` + Jinja2 模板页面。
- 邮箱+手机与 AD 比对、短信验证码签发与校验、AD 管理员重置密码。
- 限流、防用户枚举、防 LDAP 注入、CSRF、保护名单、审计、通知短信。
- 移除普通用户的登录与登录后自助改密、移除 TOTP(MFA)。
- 保留管理员后台，但**精简为 4 项**：域配置 / 短信配置 / 保护名单管理 / 日志。移除用户同步、用户管理、大部分系统设置（DB 配置页、密码策略改走 env）。

### 2.2 不做（Out of Scope）

- Microsoft Graph / AAD 直连集成（由 Entra Connect 自动同步，应用不参与）。
- 多 AD 域支持（本部署为单域）。
- 服务端渲染页面之外的 Vue SPA 重写。
- 管理员账号通过公开流程自助恢复（走命令行 `init_admin_password.py`）。
- TOTP/MFA、备用码、CAS、mock_cas 相关功能（移除）。

---

## 3. 关键决策记录（Decisions）

| # | 决策 | 选择 |
|---|---|---|
| D1 | 与现有系统的关系 | 重置成为主入口；砍掉普通用户登录 + 登录后改密；保留管理员登录与后台 |
| D2 | 身份匹配 | 邮箱 = AD `mail`，手机 = AD `mobile`，必须同一用户记录两者都命中 |
| D3 | 匹配失败反馈 | 统一文案"若信息匹配，验证码已发送"，不匹配静默不发（防枚举） |
| D4 | 限流 | 手机 60s 冷却 + 每小时 5 次；验证码 5 分钟有效、错 5 次锁定；IP 每小时 20 次发码 |
| D5 | MFA | 移除 TOTP；重置只靠短信验证码 |
| D6 | 前端载体 | Jinja2 模板文件（不再用内嵌 HTML 字符串） |
| D7 | 授权模型 | 方案 A：服务端 Flask `session` 状态授权（非签名 token） |
| D8 | 重置后是否强制再改 | **否**。新密码直接使用，不设 `pwdLastSet=0`（远程用户直接登录） |
| D9 | AAD 同步 | 依赖已有 Entra Connect（PHS/PTA）自动同步，应用不改 AAD |
| D10 | 域数量 | 单域 |
| D11 | 保护名单 | 新增后台可配"禁止自助重置"名单，admin/域管理员/服务账号默认入内 |
| D12 | 管理员后台范围 | 保留 admin 登录，但**精简为 4 项**：域配置 / 短信配置 / 保护名单 / 日志。移除用户同步、用户管理、大部分系统设置。新流程实时查 AD，不再把用户同步到本地库 |
| D13 | 敏感凭据加密存储 | AD 绑定账号密码、阿里云密钥在 DB 中**加密存储**（对称加密，运行时解密），修复现状明文存储的 P0 隐患 |

---

## 4. 架构总览

向导状态全部承载于 Flask `session`，无客户端令牌。实际改密复用 LDAP 管理员绑定 + `unicodePwd` MODIFY_REPLACE。AAD 同步不在应用内。

```
[公开用户] ── HTTP ──> [reset_bp (Flask)]
                          │
                          ├─ verify-identity ─> reset_service.find_user_by_email_phone()
                          │                       └─ LdapService (admin bind) 查 AD
                          ├─ send-code        ─> reset_service.issue_sms_code()
                          │                       └─ SmsService (阿里云)
                          ├─ verify-code      ─> reset_service.verify_sms_code()
                          └─ do-reset         ─> reset_service.perform_reset()
                                                  └─ LdapService.admin_set_password_by_dn()
                                                      (改 AD unicodePwd)
                          [Entra Connect] 自动把新密码同步到 AAD（应用外）
[管理员]  ── 登录 ──> [admin_bp]（域配置/短信配置/保护名单/日志）— 精简后台
```

---

## 5. 流程与状态机

### 5.1 向导步骤

```
[1] 输入邮箱 + 手机
     │ POST /reset/verify-identity
     ▼
[2] reset_service.find_user_by_email_phone(email, phone)
     ├─ AD 无此 mail / mobile 不符 / 禁用账号 / 命中保护名单
     │     → 返回统一文案，静默不发（并做等价 LDAP 往返抹平时差）
     └─ 命中且合规
           → session 写 reset_user_dn / reset_phone / reset_email / reset_started_at
           → issue_sms_code() 发码到 mobile → 步骤 3
[3] 输入验证码
     │ POST /reset/verify-code   (重发: POST /reset/send-code)
     ▼
     ├─ 错误 → fail_count+1（满 5 作废该码），停留步骤 3
     └─ 正确 → session.reset_authorized=True → 步骤 4
[4] 输入新密码（两次）
     │ POST /reset/do-reset
     ▼
     LdapService.admin_set_password_by_dn(reset_user_dn, new_password, domain)
     → 成功：清空所有 reset_* 标记 → 成功页（提示 AAD 2-3 分钟生效）
            + 写 AdminLog + 发"密码已重置"通知短信
     → 失败：友好提示"重置失败，请联系管理员"，记日志，不透传 AD 错误
```

### 5.2 Session 字段

`reset_user_dn`、`reset_phone`、`reset_email`、`reset_started_at`、`reset_authorized`。

### 5.3 状态门控（每个接口入口校验）

| 接口 | 前置要求 | 缺失时 |
|---|---|---|
| `verify-identity` | 无 | — |
| `send-code` | `reset_user_dn` 且未超时 | 回退步骤 1 |
| `verify-code` | `reset_user_dn` 且未超时 | 回退步骤 1 |
| `do-reset` | `reset_authorized` 且未超时 | 回退步骤 1 |

- **整体时效 10 分钟**：入口判断 `reset_started_at`，超时清空全部 `reset_*`。
- **一次性授权**：`do-reset` 成功后立即清空所有 `reset_*`。
- **改密目标用 session 中的 `reset_user_dn`**，**绝不接受请求体传入的 DN/用户名**（防越权）。

---

## 6. 接口设计

### 6.1 新增 `reset_bp`（无 url_prefix，未认证可访问）

统一返回 `{success, message, step}`，`step` 指示当前应停留步骤。

| 方法 | 路径 | 入参 | 作用 |
|---|---|---|---|
| GET | `/reset` | — | 渲染向导模板 |
| POST | `/reset/verify-identity` | email, phone | 匹配 AD，命中则发码 |
| POST | `/reset/send-code` | —（用 session 手机） | 重发验证码（受限流） |
| POST | `/reset/verify-code` | code | 校验，通过则授权 |
| POST | `/reset/do-reset` | new_password, confirm_password | 执行改密 |

### 6.2 改造 / 移除

- **移除 `user_bp` 的全部用户自助路由**：`/user/index`、`/user/api/info`、`/user/api/change-password`、`/user/api/bind-phone`、`/user/api/send-sms-code`、`/user/api/mfa/setup|enable|disable`。该蓝图可整体清空或移除（`app.py` 中同步取消注册）。
- **移除**：`services/totp_service.py`；`User` 的 `mfa_secret / mfa_enabled / mfa_bound_at` 列；session 中 `mfa_*` 键。
- **改造 `ldap_auth_bp`**：非 admin 的 LDAP 登录分支移除；未登录根路由跳 `/reset`；admin 仍走本地 bcrypt 认证。
- **精简 `admin_bp`**：保留 域配置 / 短信配置 / 日志；**移除** 用户同步（`/admin/api/admin/users/sync|preview|list`）、用户管理页与接口、系统设置中的 DB 配置/端口/密码策略等（端口/密码策略改由 env 提供）。
- **新增后台**：保护名单管理接口与页面（见 §8.5）。
- 注：新流程实时查 AD，**不再需要**用户同步到本地库，故 `users` 表仅保留 admin 账号。

---

## 7. 数据模型变更（`models/models.py`）

### 7.1 `SmsVerificationCode`（复用，补字段）

- 新增 `fail_count = db.Column(db.Integer, default=0)`
- 新增 `purpose = db.Column(db.String(30), default='reset')`
- `code` 改存 **bcrypt 哈希**（现状明文，顺手修）。
- 其余（`phone / user_id / is_used / expires_at`）不变。

### 7.2 新增 `SmsRateLimit`

```
id, key_type('phone'|'email'|'ip'), key_value(String),
sent_count(Integer), window_start(DateTime)
```
供限流滑动窗口计数。

### 7.3 `SystemSetting` 复用：保护名单

- `setting_key='reset_protected_accounts'`，`setting_type='json'，值为 DNs / sAMAccountName 列表。
- 初始化种子：`['admin']`（域管理员组 DN 由管理员后台按实际补）。

### 7.4 `User` 移除 MFA 字段

`mfa_secret / mfa_enabled / mfa_bound_at` 三列删除（含迁移脚本）。

> 数据库为 PostgreSQL，模型变更需配套迁移 SQL（`database/` 下新增 `remove_mfa_columns.sql`，并在启动迁移流程中执行）。

### 7.5 连带调整（因移除用户同步）

- `users` 表**仅保留 admin 账号**；不再有普通用户的本地记录。
- `SmsVerificationCode.user_id`：改为**可空**（自助重置无本地用户，按 phone + session DN 关联）。
- `AdminLog.admin_id`：改为**可空**（自助重置无 admin 操作者，`action='password_reset'`，记 `target_user` + 用户 IP）。

---

## 8. 服务层（`services/`）

### 8.1 新增 `reset_service.py`（核心，纯逻辑可单测）

封装：
- `find_user_by_email_phone(email, phone)` → `(matched: bool, user_dn, mobile, attrs)`；含输入规整、保护名单判定、禁用账号判定、LDAP 转义。
- `issue_sms_code(user_dn, phone)` → 生成 6 位码、bcrypt 哈希入库、调 `SmsService` 发送。
- `verify_sms_code(code)` → 比对哈希、过期/作废判定、`fail_count` 累加与锁定、成功置 `is_used`。
- `perform_reset(new_password)` → 密码策略校验 + 调 `LdapService.admin_set_password_by_dn`。
- 限流工具 `_check_and_increment(key_type, key_value, limit)`。

### 8.2 新增 `services/ldap_filter.py`

`escape_ldap(value)`：转义 `( ) \ *` 等，供 `verify-identity` 与现有 `authenticate` 复用（顺手修 LDAP 注入）。

### 8.3 `LdapService` 新增方法

- `admin_set_password_by_dn(user_dn, new_password, domain)`：管理员绑定，对 `user_dn` 做 `unicodePwd` MODIFY_REPLACE。**按显式 DN 操作**，不依赖本地 DB 用户、不猜测 CN（修掉 `change_password_by_admin` 的 CN 拼接回退隐患）。
- 保留现有 `change_password_by_admin` 供后台使用（可重构为调用新方法）。

### 8.4 `sms_service.py`

- 基本不变。`user_bp` 中原 `send_sms_code` 空壳不再使用；`reset_service.issue_sms_code` 真正接通 `SmsService.send_verification_code`。
- 新增"密码已重置"通知模板（复用或新增阿里云模板 CODE）。

### 8.5 保护名单管理（后台）

- `admin_bp` 新增：`GET/PUT /admin/api/reset-protected-accounts`，读改 `SystemSetting` JSON。
- 后台"系统设置"页加一区块管理该名单（复用现有 settings 页风格）。

---

## 9. 限流与防滥用

### 9.1 三层限流（`SmsRateLimit` 滑动窗口）

| 维度 | 限制 | 动作 |
|---|---|---|
| 同手机号 | 60s 冷却 | 冷却内 → 统一文案"请稍候再试" |
| 同手机号 | ≤5 次/小时 | 超额 → 静默不发，统一文案 |
| 同邮箱 | ≤5 次/小时 | 同上 |
| 同 IP | ≤20 次发码/小时 | 超额 → 429 |

窗口超 1 小时计数归零。

### 9.2 验证码生命周期

- 6 位数字，bcrypt 哈希入库；明文仅经短信发出，不入库不入日志。
- 有效期 5 分钟。
- 错 5 次作废该码（`is_used=True`），需重发。
- 成功即 `is_used=True`，写 `reset_authorized`。
- 重发：先作废旧码再发新，同样受限流。

---

## 10. 安全细节

1. **防用户枚举**：`verify-identity` 匹配/不匹配均返回同一文案；不匹配静默不发。
2. **时序攻击加固**：不匹配路径也做一次等价 LDAP 往返，抹平响应时差。
3. **LDAP 注入**：`mail` 等用户输入经 `escape_ldap` 后入过滤器。
4. **保护名单**：命中（admin/域管理员组/服务账号等）→ 拒绝（统一文案 + 高危日志）。匹配语义：保护名单为标识列表（DN、`sAMAccountName`、或组 DN）；AD 查询返回用户的 DN、`sAMAccountName`、`memberOf`，当任一受保护标识等于用户 DN / `sAMAccountName`，或出现在 `memberOf` 中即视为命中。
5. **禁用账号拒绝**：`userAccountControl` 含 `ACCOUNTDISABLE`(bit 2) → 拒绝。
6. **改密目标不可被前端指定**：`do-reset` 只用 session `reset_user_dn`。
7. **密码策略**：≥8 位、大小写+数字+特殊字符（读 `Config.PASSWORD_*`），集中在校验函数。
8. **CSRF**：reset 四个 POST 接入 Flask-WTF CSRF；模板渲染 `{{ csrf_token() }}`。
9. **日志脱敏**：探测失败不记邮箱/手机原文，只记 IP+计数；通知短信手机号 `138****1234`。
10. **会话**：Flask session 签名 cookie；**验证码/密码等机密不入 session**（只入 DB）；`reset_*` 仅存 DN/手机/邮箱/时间/授权位（这些是用户自己的信息，非机密）。
11. **AD 改密失败**：友好提示，不透传内部错误。
12. **敏感凭据加密存储（D13）**：`domains.admin_password`、`domains.ldap_password`、`sms_configs.access_secret`（及 `access_key`）在 DB 中以对称加密（如 Fernet，密钥来自 env）存储，运行时解密；`to_dict()` 永不回传明文/完整密钥到前端。修复现状明文存储隐患。

---

## 11. AAD 同步说明

- **应用不直连 AAD**。改 AD `unicodePwd` 后，已有 **Microsoft Entra Connect（PHS/PTA）** 自动同步到 AAD。
- **传播延迟**：按 **PHS（密码哈希同步）** 取保守值——云服务（M365/邮箱等）新密码可能 **2–3 分钟** 生效。成功页用此文案提示，避免误判失败。若实际为 **PTA / Federation**，密码实时对 AD 校验、近即时生效，部署时可把文案改为"即时生效"。
- **前提**：依赖 PHS/PTA 保持为认证方式；若日后变更，本假设失效，需重新评估（写入运维文档）。
- 因不集成 Graph，**无需管理 Azure 应用凭据**，安全面更小。

---

## 12. 错误处理矩阵

| 场景 | 对用户 | 后端 |
|---|---|---|
| 邮箱/手机不匹配或不存在 | 统一文案 | 不发码；记 IP+计数（不记原文）；等价 LDAP 往返 |
| 限流（冷却/超额） | 统一文案或 429 | 不发码；计数自增 |
| 验证码错误 | "验证码错误，还剩 N 次" | fail_count+1；满 5 作废 |
| 验证码过期/作废 | "验证码已失效，请重新获取" | 清前置 |
| 命中保护名单 / 禁用账号 | 统一文案 | 记高危日志 |
| AD 改密失败（策略/连接） | "重置失败，请联系管理员" | 记详细日志 |
| SMS 配置缺失 / LDAP 不可用 | "服务暂不可用，请联系管理员" | 入口前置检测拦截 |
| 越步 / 超时 / 缺前置标记 | 回退步骤 1 | 清空 reset_* |
| 输入手机与登记不符（合法用户） | 页面常驻提示"若手机号与登记不一致请联系 IT/管理员" | — |

---

## 13. 测试策略

### 13.1 单元测试（`reset_service.py`）

- 输入规整（邮箱大小写、手机去空格/横线/`+86`、长度校验）
- 限流窗口（手机冷却、每小时上限、IP 上限）
- 验证码：生成/校验/失败计数/锁定/过期/重发失效旧码
- 保护名单：命中拒绝、放行
- 禁用账号：拒绝
- 密码策略：各分支

### 13.2 LDAP 适配

- `reset_service` 注入可替换 lookup/reset 适配器；测试用 mock，不依赖真实 AD。
- 复用 `CONNECTION_MODE='mock'` 思路。

### 13.3 路由 / 集成测试（Flask test client）

- 正常路径全通（4 步）
- 越步访问被拒
- 越权：请求体塞他人 DN 被忽略
- 重置后 `reset_*` 被清空
- 重放：旧码、旧授权失效

### 13.4 安全专项

- 防枚举：匹配/不匹配响应与时间一致
- LDAP 注入：邮箱含 `)(` 等 payload 被转义
- CSRF：无 token 请求被拒

---

## 14. 验收清单

- [ ] 正常重置一条龙通过，密码可直接用于 AD 与云登录
- [ ] 不匹配静默不发短信，响应/时序一致
- [ ] 限流三层生效
- [ ] 验证码哈希存储、5 次错误锁定、5 分钟过期
- [ ] 保护名单拦截 admin/敏感账号
- [ ] 禁用账号拒绝
- [ ] AD 拒绝（域策略）时友好提示
- [ ] 成功通知短信发出、日志脱敏
- [ ] 越步/越权/重放全部被拒
- [ ] 成功页提示 AAD 2-3 分钟生效
- [ ] MFA/TOTP 及相关路由、字段、服务已移除
- [ ] 普通用户登录与登录后改密已移除
- [ ] 管理员后台精简为 域配置/短信配置/保护名单/日志；用户同步、用户管理、系统设置(DB/端口/策略) 已移除
- [ ] AD 绑定密码与阿里云密钥在 DB 中加密存储，前端不回传明文

---

## 15. 文档与运维

- 在 `wendang/` 增补：重置流程说明、单域前提、AAD 同步前提、admin 锁死恢复路径（`init_admin_password.py`）。
- 保护名单的初始配置建议写入部署指南。

---

## 16. 待评审问题（需用户确认后进入实施计划）

无（所有关键决策已记录于 §3）。
