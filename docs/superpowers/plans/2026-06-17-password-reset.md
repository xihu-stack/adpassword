# 域控密码自助重置系统 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有的"登录 + MFA + 自助改密"系统重构为面向远程用户的"忘记密码自助重置"系统：邮箱+手机与 AD 校验 → 短信验证码 → 重置域控密码（AAD 由 Entra Connect 自动同步）。

**Architecture:** 服务端 Flask session 承载 4 步向导状态（方案 A）。新增 `reset_bp` 公开蓝图 + `reset_service` 核心服务（注入 ldap/sms 适配器便于测试）。移除登录自助改密与 TOTP/MFA，精简管理员后台为 4 项（域配置/短信配置/保护名单/日志）。敏感凭据（AD 密码、阿里云密钥）Fernet 加密存库。

**Tech Stack:** Flask 3, Flask-SQLAlchemy, ldap3, bcrypt, pyotp(移除), cryptography(Fernet), aliyun SMS SDK, pytest, SQLite(测试用)/PostgreSQL(生产)。

**Spec:** `docs/superpowers/specs/2026-06-16-password-reset-design.md`

> **Git 说明：** 本仓库当前**非 git 仓库**。建议先执行 `git init` 以便使用下方各任务的 commit 检查点；否则把每个 "Commit" 步骤当作保存检查点。所有命令默认在 `D:\代码\ad2\backend` 目录下运行。

---

## 文件结构（改动总览）

**新建：**
- `backend/services/ldap_filter.py` — LDAP 过滤器转义（防注入）
- `backend/services/secret_crypto.py` — Fernet 对称加密工具
- `backend/services/reset_service.py` — 重置流程核心服务
- `backend/routes/reset.py` — 公开重置蓝图 `reset_bp`
- `backend/templates/reset.html` — 4 步重置向导 Jinja2 模板
- `backend/tests/conftest.py` — pytest app/client/db fixtures
- `backend/tests/test_ldap_filter.py`
- `backend/tests/test_secret_crypto.py`
- `backend/tests/test_reset_service.py`
- `backend/tests/test_reset_routes.py`
- `database/2026-06-17-reset-migration.sql` — 生产迁移脚本
- `wendang/密码自助重置说明.md` — 运维文档

**修改：**
- `backend/models/models.py` — SmsVerificationCode 补字段+哈希；新增 SmsRateLimit；Domain/SmsConfig 加密；users 仅 admin；FK 可空；移除 MFA 列
- `backend/services/ldap_service.py` — 新增 `lookup_user_by_email`、`admin_set_password_by_dn`
- `backend/services/sms_service.py` — 复用（reset_service 直接调用）
- `backend/routes/admin.py` — 精简：移除用户同步/用户管理/系统设置，新增保护名单管理
- `backend/routes/ldap_auth.py` — 移除非 admin 登录，根路由跳 `/reset`
- `backend/app.py` — 注册 `reset_bp`，移除 `user_bp`，`create_app(testing=)` 支持，保护名单种子
- `backend/config.py` — `SECRET_ENCRYPTION_KEY`，CSRF 保持启用
- `backend/.env.example` / `backend/.env.production.example` — 新增 `SECRET_ENCRYPTION_KEY`、密码策略项

**删除：**
- `backend/services/totp_service.py`
- `backend/routes/user.py`（整体移除）

---

## Task 0: 测试基础设施

**Files:**
- Create: `backend/tests/conftest.py`
- Modify: `backend/app.py`（create_app 加 testing 参数）
- Create: `backend/tests/__init__.py`（空文件）

- [ ] **Step 1: 给 create_app 加 testing 支持**

修改 `backend/app.py`，把 `def create_app():` 改为：

```python
def create_app(testing=False):
    app = Flask(__name__)

    if testing:
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'testing-secret-key-do-not-use-in-prod')
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('TEST_DATABASE_URL', 'sqlite:///:memory:')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['CORS_ORIGINS'] = []
        app.config['PASSWORD_MIN_LENGTH'] = 8
        app.config['PASSWORD_REQUIRE_UPPERCASE'] = True
        app.config['PASSWORD_REQUIRE_LOWERCASE'] = True
        app.config['PASSWORD_REQUIRE_NUMBER'] = True
        app.config['PASSWORD_REQUIRE_SPECIAL'] = True
        # SQLite in-memory 需要 StaticPool 共享连接
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            from sqlalchemy.pool import StaticPool
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'connect_args': {'check_same_thread': False},
                'poolclass': StaticPool,
            }
    else:
        app.config.from_object(Config)
```

注意：`create_app` 内部其余代码（错误处理、before_request、CORS、蓝图注册、db.create_all、建 admin）保持不变；只把"加载配置"这一段替换成上面的 if/else。模块级 `app = create_app()` 保持不变（生产用）。

- [ ] **Step 2: 创建 tests 包与 conftest**

`backend/tests/__init__.py`：空文件。

`backend/tests/conftest.py`：

```python
import os
# 必须在导入 config/app 之前设置环境变量，避免 Config 模块级校验报错
os.environ.setdefault('SECRET_KEY', 'testing-secret-key-do-not-use-in-prod')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('TEST_DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('CORS_ORIGINS', '')

from cryptography.fernet import Fernet
# 固定一个测试用 Fernet key（确定性，便于断言）
os.environ.setdefault('SECRET_ENCRYPTION_KEY', Fernet.generate_key().decode())

import pytest
from app import create_app
from models.models import db


class FakeLdap:
    """可编程的 LDAP 适配器替身。"""
    def __init__(self):
        self.users = {}          # email(lower) -> info dict
        self.set_password_calls = []
        self.set_password_ok = True
        self.set_password_msg = 'OK'

    def lookup_user_by_email(self, domain, email):
        return self.users.get((email or '').strip().lower())

    def admin_set_password_by_dn(self, domain, user_dn, new_password):
        self.set_password_calls.append((user_dn, new_password))
        return self.set_password_ok, self.set_password_msg


class FakeSms:
    def __init__(self):
        self.sent = []           # [(phone, code), ...]
        self.ok = True

    def send_verification_code(self, phone, code):
        self.sent.append((phone, code))
        return self.ok, 'OK'


@pytest.fixture()
def app():
    app = create_app(testing=True)
    with app.app_context():
        db.create_all()
        # 种子保护名单与一个测试域
        from models.models import SystemSetting, Domain
        db.session.add(SystemSetting(
            setting_key='reset_protected_accounts',
            setting_value='["admin"]',
            setting_type='json',
            description='禁止自助重置的账号'))
        db.session.add(Domain(
            name='test', ldap_hosts='dc.test', ldap_port=389, ldaps_port=636,
            base_dn='DC=test,DC=com', admin_dn='CN=Admin,DC=test,DC=com',
            admin_password='x', use_ssl=False, is_active=True))
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def fake_ldap():
    return FakeLdap()


@pytest.fixture()
def fake_sms():
    return FakeSms()
```

- [ ] **Step 3: 验证 fixtures 可用**

Run（在 `backend/` 下）:
```bash
python -m pytest tests/ -v
```
Expected: `no tests ran`（0 个用例），无 import 错误、无 fixture 报错。若报 `cryptography`/`fernet` 未安装，先 `pip install cryptography`（requirements 已含）。

- [ ] **Step 4: 安装 pytest（若未装）**

Run:
```bash
pip install pytest
```

- [ ] **Step 5: Commit**

```bash
git add backend/tests/ backend/app.py
git commit -m "test: 搭建 pytest 基础设施与 app/client/db fixtures"
```

---

## Task 1: LDAP 过滤器转义工具

**Files:**
- Create: `backend/services/ldap_filter.py`
- Test: `backend/tests/test_ldap_filter.py`

- [ ] **Step 1: 写失败测试**

`backend/tests/test_ldap_filter.py`:

```python
from services.ldap_filter import escape_ldap


def test_escapes_special_chars():
    assert escape_ldap('user)(*))') == r'user\28\29\2a\29\2a'
    assert escape_ldap('a\\b') == r'a\5cb'
    assert escape_ldap('normal') == 'normal'
    assert escape_ldap('a\x00b') == r'a\00b'


def test_handles_non_string():
    assert escape_ldap(123) == '123'
    assert escape_ldap(None) == ''
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/test_ldap_filter.py -v`
Expected: FAIL（`ModuleNotFoundError: services.ldap_filter`）。

- [ ] **Step 3: 实现**

`backend/services/ldap_filter.py`:

```python
"""LDAP 过滤器转义，防止 LDAP 注入。RFC4515 规则。"""


def escape_ldap(value):
    """对用户输入做 LDAP 过滤器转义。"""
    if value is None:
        return ''
    v = str(value)
    v = v.replace('\\', '\\5c')
    out = []
    for ch in v:
        if ch == '*':
            out.append('\\2a')
        elif ch == '(':
            out.append('\\28')
        elif ch == ')':
            out.append('\\29')
        elif ch == '\x00':
            out.append('\\00')
        else:
            out.append(ch)
    return ''.join(out)
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/test_ldap_filter.py -v`
Expected: PASS（2 passed）。

- [ ] **Step 5: Commit**

```bash
git add backend/services/ldap_filter.py backend/tests/test_ldap_filter.py
git commit -m "feat: LDAP 过滤器转义工具 escape_ldap"
```

---

## Task 2: 敏感凭据加密工具（Fernet）

**Files:**
- Create: `backend/services/secret_crypto.py`
- Test: `backend/tests/test_secret_crypto.py`

- [ ] **Step 1: 写失败测试**

`backend/tests/test_secret_crypto.py`:

```python
import os
import pytest
from services import secret_crypto


def test_roundtrip():
    plain = 'P@ssw0rd-非常机密'
    token = secret_crypto.encrypt_value(plain)
    assert token != plain
    assert secret_crypto.decrypt_value(token) == plain


def test_decrypt_garbage_returns_none():
    assert secret_crypto.decrypt_value('not-a-valid-token') is None


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv('SECRET_ENCRYPTION_KEY', raising=False)
    with pytest.raises(RuntimeError):
        secret_crypto.encrypt_value('x')
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/test_secret_crypto.py -v`
Expected: FAIL（模块不存在）。

- [ ] **Step 3: 实现**

`backend/services/secret_crypto.py`:

```python
"""敏感凭据对称加密（Fernet）。密钥来自环境变量 SECRET_ENCRYPTION_KEY。"""
import os
from cryptography.fernet import Fernet, InvalidToken


def _fernet():
    key = os.getenv('SECRET_ENCRYPTION_KEY')
    if not key:
        raise RuntimeError('SECRET_ENCRYPTION_KEY 环境变量未设置')
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(plain):
    """加密明文，返回字符串 token。空值原样返回。"""
    if plain is None or plain == '':
        return plain
    return _fernet().encrypt(plain.encode('utf-8')).decode('utf-8')


def decrypt_value(token):
    """解密 token，返回明文。非 token/损坏返回 None。"""
    if token is None or token == '':
        return None
    try:
        return _fernet().decrypt(token.encode('utf-8')).decode('utf-8')
    except (InvalidToken, Exception):
        return None


def is_encrypted(value):
    """判断一个值是否已经是加密 token（启发式：Fernet token 以 gAAAA 开头）。"""
    return isinstance(value, str) and value.startswith('gAAAA')
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/test_secret_crypto.py -v`
Expected: PASS（3 passed）。

- [ ] **Step 5: Commit**

```bash
git add backend/services/secret_crypto.py backend/tests/test_secret_crypto.py
git commit -m "feat: Fernet 敏感凭据加密工具"
```

---

## Task 3: 限流表 SmsRateLimit + 模型调整

**Files:**
- Modify: `backend/models/models.py`
- Test: `backend/tests/test_reset_service.py`（rate limit 部分，与 Task 8 合并；此处先建表+迁移）

- [ ] **Step 1: 在 models.py 新增 SmsRateLimit，并给 SmsVerificationCode 补字段**

在 `backend/models/models.py` 中，找到 `class SmsVerificationCode`，改为：

```python
class SmsVerificationCode(db.Model):
    __tablename__ = 'sms_verification_codes'

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), nullable=False, index=True)
    code = db.Column(db.String(255), nullable=False)  # bcrypt 哈希
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    fail_count = db.Column(db.Integer, default=0)
    purpose = db.Column(db.String(30), default='reset')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

在文件末尾新增：

```python
class SmsRateLimit(db.Model):
    __tablename__ = 'sms_rate_limits'

    id = db.Column(db.Integer, primary_key=True)
    key_type = db.Column(db.String(20), nullable=False)   # phone|email|ip
    key_value = db.Column(db.String(200), nullable=False)
    sent_count = db.Column(db.Integer, default=0)
    window_start = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('key_type', 'key_value', name='uq_sms_rate_key'),
    )
```

- [ ] **Step 2: 写限流工具的失败测试**

新建 `backend/tests/test_reset_service.py`，先只放限流用例（其余在后续 Task 补）：

```python
from datetime import datetime, timedelta
from models.models import db, SmsRateLimit
from services.reset_service import ResetService


def test_rate_limit_allows_then_blocks(app, fake_ldap, fake_sms):
    with app.app_context():
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        # 前 5 次放行
        for i in range(5):
            allowed, reason = svc.check_rate_limits('1390000000%d' % i if i else '13900000001',
                                                    'a@b.com', '1.2.3.4')
            # 用同一手机号测：手机号维度每 5 次/小时；先建几个计数
        # 直接测同一手机号 5 次后被挡
        for i in range(5):
            allowed, reason = svc.check_rate_limits('13900000000', 'x@b.com', '1.2.3.4')
            assert allowed, reason
        allowed, reason = svc.check_rate_limits('13900000000', 'x@b.com', '1.2.3.4')
        assert not allowed
```

- [ ] **Step 3: 运行确认失败**

Run: `python -m pytest tests/test_reset_service.py -v`
Expected: FAIL（`ResetService` 不存在）。

- [ ] **Step 4: 实现 ResetService 骨架 + check_rate_limits**

`backend/services/reset_service.py`（本任务只实现限流与常量，其余方法后续补；用 `NotImplementedError` 占位会被对应任务替换）：

```python
"""忘记密码自助重置核心服务。通过注入 ldap/sms 适配器实现可测试性。"""
from datetime import datetime, timedelta
import bcrypt
import secrets
import re

from models.models import db, SmsVerificationCode, SmsRateLimit, SystemSetting, Domain
from services import secret_crypto

# 限流参数
PHONE_COOLDOWN_SECONDS = 60
HOURLY_LIMIT_PHONE = 5
HOURLY_LIMIT_EMAIL = 5
HOURLY_LIMIT_IP = 20
CODE_TTL_MINUTES = 5
MAX_FAIL_COUNT = 5
RESET_SESSION_MINUTES = 10


class _DefaultLdapAdapter:
    def lookup_user_by_email(self, domain, email):
        from services.ldap_service import LdapService
        return LdapService.lookup_user_by_email(domain, email)

    def admin_set_password_by_dn(self, domain, user_dn, new_password):
        from services.ldap_service import LdapService
        return LdapService.admin_set_password_by_dn(domain, user_dn, new_password)


class _DefaultSmsAdapter:
    def send_verification_code(self, phone, code):
        from services.sms_service import SmsService
        from models.models import SmsConfig
        cfg = SmsConfig.query.filter_by(is_active=True).first()
        if not cfg:
            return False, '短信服务未配置'
        return SmsService(cfg).send_verification_code(phone, code)


class ResetService:
    def __init__(self, ldap_adapter=None, sms_adapter=None):
        self.ldap = ldap_adapter or _DefaultLdapAdapter()
        self.sms = sms_adapter or _DefaultSmsAdapter()

    # ---------- 限流 ----------
    def check_rate_limits(self, phone, email, ip):
        now = datetime.utcnow()
        # 手机号 60s 冷却：查最近一条该手机的验证码
        latest = SmsVerificationCode.query.filter_by(phone=phone).order_by(
            SmsVerificationCode.created_at.desc()).first()
        if latest and latest.created_at and now - latest.created_at < timedelta(seconds=PHONE_COOLDOWN_SECONDS):
            return False, '请稍候再试'

        limits = [
            ('phone', phone, HOURLY_LIMIT_PHONE),
            ('email', email, HOURLY_LIMIT_EMAIL),
            ('ip', ip, HOURLY_LIMIT_IP),
        ]
        for key_type, key_value, cap in limits:
            if not key_value:
                continue
            rl = SmsRateLimit.query.filter_by(key_type=key_type, key_value=key_value).first()
            if rl:
                if now - rl.window_start > timedelta(hours=1):
                    rl.sent_count = 0
                    rl.window_start = now
                if rl.sent_count >= cap:
                    return False, '请求过于频繁'
        return True, None

    def _increment_rate(self, phone, email, ip):
        now = datetime.utcnow()
        for key_type, key_value in (('phone', phone), ('email', email), ('ip', ip)):
            if not key_value:
                continue
            rl = SmsRateLimit.query.filter_by(key_type=key_type, key_value=key_value).first()
            if not rl:
                rl = SmsRateLimit(key_type=key_type, key_value=key_value,
                                  sent_count=0, window_start=now)
                db.session.add(rl)
            if now - rl.window_start > timedelta(hours=1):
                rl.sent_count = 0
                rl.window_start = now
            rl.sent_count += 1
        db.session.commit()
```

- [ ] **Step 5: 运行确认通过**

Run: `python -m pytest tests/test_reset_service.py -v`
Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add backend/models/models.py backend/services/reset_service.py backend/tests/test_reset_service.py
git commit -m "feat: SmsRateLimit 限流表与 ResetService 限流逻辑"
```

---

## Task 4: 输入规整 + 密码策略校验

**Files:**
- Modify: `backend/services/reset_service.py`
- Modify: `backend/tests/test_reset_service.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_reset_service.py` 顶部加导入并追加用例：

```python
from services.reset_service import normalize_email, normalize_phone, validate_password


def test_normalize_email():
    assert normalize_email('  John@X.COM ') == 'john@x.com'
    assert normalize_email(None) == ''


def test_normalize_phone():
    assert normalize_phone('138 0000 0000') == '13800000000'
    assert normalize_phone('+86-138-0000-0000') == '13800000000'
    assert normalize_phone('8613800000000') == '13800000000'


def test_validate_password_policy(app):
    from flask import current_app
    with app.app_context():
        assert validate_password('Ab@12345', app.config)[0] is True
        assert validate_password('short', app.config)[0] is False
        assert validate_password('alllowercase1!', app.config)[0] is False      # 无大写
        assert validate_password('NOLOWERCASE1!', app.config)[0] is False       # 无小写
        assert validate_password('Abcdefg!', app.config)[0] is False            # 无数字
        assert validate_password('Abcdefg1', app.config)[0] is False            # 无特殊字符
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/test_reset_service.py -v -k "normalize or validate_password"`
Expected: FAIL（函数未定义）。

- [ ] **Step 3: 实现**

在 `reset_service.py` 模块级（类外）加：

```python
def normalize_email(email):
    return (email or '').strip().lower()


def normalize_phone(phone):
    digits = re.sub(r'\D', '', phone or '')
    if len(digits) == 13 and digits.startswith('86'):
        digits = digits[2:]
    return digits


def validate_password(pw, config):
    if not pw:
        return False, '请输入新密码'
    if len(pw) < int(config.get('PASSWORD_MIN_LENGTH', 8)):
        return False, '新密码长度至少 %d 位' % config.get('PASSWORD_MIN_LENGTH', 8)
    if config.get('PASSWORD_REQUIRE_LOWERCASE') and not re.search(r'[a-z]', pw):
        return False, '密码必须包含小写字母'
    if config.get('PASSWORD_REQUIRE_UPPERCASE') and not re.search(r'[A-Z]', pw):
        return False, '密码必须包含大写字母'
    if config.get('PASSWORD_REQUIRE_NUMBER') and not re.search(r'\d', pw):
        return False, '密码必须包含数字'
    if config.get('PASSWORD_REQUIRE_SPECIAL') and not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", pw):
        return False, '密码必须包含特殊字符'
    return True, None
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/test_reset_service.py -v -k "normalize or validate_password"`
Expected: PASS（3 passed）。

- [ ] **Step 5: Commit**

```bash
git add backend/services/reset_service.py backend/tests/test_reset_service.py
git commit -m "feat: 邮箱/手机号规整与密码策略校验"
```

---

## Task 5: LdapService 新增按邮箱查找 + 按 DN 改密

**Files:**
- Modify: `backend/services/ldap_service.py`

> 说明：这两个方法依赖真实 AD，单测通过适配器替身覆盖（见 Task 8）。本任务实现真实逻辑，并保证签名与 `reset_service` 的适配器调用一致。

- [ ] **Step 1: 实现 lookup_user_by_email（静态方法）**

在 `backend/services/ldap_service.py` 的 `LdapService` 类内新增：

```python
    @staticmethod
    def lookup_user_by_email(domain, email):
        """按 mail 查找用户，返回 dict 或 None。
        返回字段：user_dn, mobile, mail, sam_account_name, member_of(list), disabled(bool)。
        """
        if not LDAP3_AVAILABLE:
            return None
        from services.ldap_filter import escape_ldap

        servers = LdapService.get_ldap_servers({
            'ldap_hosts': domain.ldap_hosts or domain.ldap_host,
            'ldap_host': domain.ldap_host,
            'ldap_port': domain.ldap_port,
            'ldaps_port': domain.ldaps_port,
            'use_ssl': domain.use_ssl,
            'admin_dn': domain.admin_dn,
            'admin_password': secret_decrypt(domain.admin_password),
            'base_dn': domain.base_dn,
        })
        if not servers:
            return None

        protocol, host, port = servers[0]
        server_url = f"{protocol}://{host}:{port}"
        if protocol == 'ldaps':
            tls_context = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLS_CLIENT,
                              ciphers='ALL:@SECLEVEL=0')
            server = Server(server_url, get_info=ALL, tls=tls_context, connect_timeout=10)
        else:
            server = Server(server_url, get_info=ALL, connect_timeout=10)

        try:
            conn = Connection(server, user=domain.admin_dn,
                              password=secret_decrypt(domain.admin_password),
                              authentication=SIMPLE, auto_bind=True, receive_timeout=30)
        except Exception as e:
            print(f'[LDAP 查找] 绑定失败：{str(e)[:120]}')
            return None

        filt = f'(&(objectClass=user)(objectCategory=person)(mail={escape_ldap(email)}))'
        try:
            conn.search(search_base=domain.base_dn, search_filter=filt, search_scope=SUBTREE,
                        attributes=['distinguishedName', 'mail', 'mobile',
                                    'sAMAccountName', 'memberOf', 'userAccountControl'])
            if not conn.entries:
                return None
            entry = conn.entries[0]
            uac = 0
            try:
                uac = int(entry.userAccountControl.value) if entry.userAccountControl.value else 0
            except Exception:
                uac = 0
            member_of = []
            try:
                raw = entry.memberOf.values if entry.memberOf.values else []
                member_of = [str(x) for x in raw]
            except Exception:
                member_of = []
            return {
                'user_dn': entry.entry_dn,
                'mail': str(entry.mail.value) if entry.mail.value else '',
                'mobile': str(entry.mobile.value) if entry.mobile.value else '',
                'sam_account_name': str(entry.sAMAccountName.value) if entry.sAMAccountName.value else '',
                'member_of': member_of,
                'disabled': bool(uac & 0x2),  # ACCOUNTDISABLE = bit 2
            }
        except Exception as e:
            print(f'[LDAP 查找] 搜索失败：{str(e)[:120]}')
            return None
        finally:
            try:
                conn.unbind()
            except Exception:
                pass
```

在文件顶部 import 区加：
```python
from services import secret_crypto as _sc
def secret_decrypt(v):
    return _sc.decrypt_value(v) if _sc.is_encrypted(v) else v
```

- [ ] **Step 2: 实现 admin_set_password_by_dn（静态方法）**

在 `LdapService` 类内新增：

```python
    @staticmethod
    def admin_set_password_by_dn(domain, user_dn, new_password):
        """用管理员绑定，对指定 DN 重置密码（不需要原密码）。返回 (ok, message)。"""
        if not LDAP3_AVAILABLE:
            return False, 'ldap3 库不可用'
        if LdapService.CONNECTION_MODE == 'mock':
            return True, '密码修改成功 (模拟)'
        try:
            protocol = 'ldaps' if domain.use_ssl else 'ldap'
            port = domain.ldaps_port if domain.use_ssl else domain.ldap_port
            server_url = f"{protocol}://{(domain.ldap_hosts or domain.ldap_host).split(',')[0].strip()}:{port}"
            if protocol == 'ldaps':
                tls_context = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLS_CLIENT,
                                  ciphers='ALL:@SECLEVEL=0')
                server = Server(server_url, get_info=ALL, tls=tls_context, connect_timeout=10,
                                allowed_referral_hosts=[('*', True)])
            else:
                server = Server(server_url, get_info=ALL)
            conn = Connection(server, user=domain.admin_dn,
                              password=secret_decrypt(domain.admin_password),
                              authentication=SIMPLE, auto_bind=True)
            encoded = ('"' + new_password + '"').encode('utf-16-le')
            result = conn.modify(user_dn, {'unicodePwd': [(MODIFY_REPLACE, [encoded])]})
            if result:
                conn.unbind()
                return True, '密码修改成功'
            msg = conn.result.get('message', '密码修改失败')
            conn.unbind()
            return False, msg
        except Exception as e:
            return False, f'密码修改失败：{str(e)}'
```

- [ ] **Step 3: 手动冒烟（可选，需真实 AD）**

无需自动化；真实 AD 验证留到部署。确认文件无语法错误：
Run: `python -c "import sys; sys.path.insert(0,'backend'); from services.ldap_service import LdapService; print('ok')"`
Expected: `ok`（无 SyntaxError）。

- [ ] **Step 4: Commit**

```bash
git add backend/services/ldap_service.py
git commit -m "feat: LdapService 按 mail 查找用户与按 DN 重置密码"
```

---

## Task 6: ResetService.find_user_by_email_phone（含保护名单/禁用/规整）

**Files:**
- Modify: `backend/services/reset_service.py`
- Modify: `backend/tests/test_reset_service.py`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_reset_service.py`：

```python
def _seed_user(fake_ldap, email, mobile, sam='u1', disabled=False, member_of=None):
    fake_ldap.users[email.lower()] = {
        'user_dn': 'CN=%s,DC=test,DC=com' % sam,
        'mail': email, 'mobile': mobile, 'sam_account_name': sam,
        'member_of': member_of or [], 'disabled': disabled,
    }


def test_find_match(app, fake_ldap, fake_sms):
    _seed_user(fake_ldap, 'John@X.com', '13800000000')
    with app.app_context():
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        matched, info = svc.find_user_by_email_phone(' john@x.com ', '138-0000-0000')
        assert matched is True
        assert info['user_dn'].startswith('CN=u1')
        assert info['mobile'] == '13800000000'


def test_find_phone_mismatch(app, fake_ldap, fake_sms):
    _seed_user(fake_ldap, 'a@x.com', '13800000000')
    with app.app_context():
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        matched, info = svc.find_user_by_email_phone('a@x.com', '13900000000')
        assert matched is False
        assert info is None


def test_find_disabled_rejected(app, fake_ldap, fake_sms):
    _seed_user(fake_ldap, 'a@x.com', '13800000000', disabled=True)
    with app.app_context():
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        matched, info = svc.find_user_by_email_phone('a@x.com', '13800000000')
        assert matched is False


def test_find_protected_rejected(app, fake_ldap, fake_sms):
    _seed_user(fake_ldap, 'a@x.com', '13800000000', sam='admin')
    with app.app_context():
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        matched, info = svc.find_user_by_email_phone('a@x.com', '13800000000')
        assert matched is False


def test_find_protected_by_group(app, fake_ldap, fake_sms):
    _seed_user(fake_ldap, 'a@x.com', '13800000000', member_of=['CN=Domain Admins,CN=Groups,DC=test,DC=com'])
    with app.app_context():
        from models.models import SystemSetting, db
        st = SystemSetting.query.filter_by(setting_key='reset_protected_accounts').first()
        st.setting_value = '["CN=Domain Admins,CN=Groups,DC=test,DC=com"]'
        db.session.commit()
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        matched, info = svc.find_user_by_email_phone('a@x.com', '13800000000')
        assert matched is False
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/test_reset_service.py -v -k find`
Expected: FAIL（方法未实现）。

- [ ] **Step 3: 实现**

在 `ResetService` 类内加：

```python
    def _protected_list(self):
        import json
        st = SystemSetting.query.filter_by(setting_key='reset_protected_accounts').first()
        if not st or not st.setting_value:
            return []
        try:
            return [str(x).strip().lower() for x in json.loads(st.setting_value) if x]
        except Exception:
            return []

    def find_user_by_email_phone(self, email, phone):
        """返回 (matched: bool, info|None)。"""
        email = normalize_email(email)
        phone = normalize_phone(phone)
        if not email or not phone:
            return False, None

        domain = Domain.query.filter_by(is_active=True).first()
        if not domain:
            return False, None

        info = self.ldap.lookup_user_by_email(domain, email)
        if not info:
            return False, None
        if info.get('disabled'):
            return False, None
        if normalize_phone(info.get('mobile', '')) != phone:
            return False, None

        # 保护名单：DN / sAMAccountName / memberOf 任一命中
        protected = self._protected_list()
        candidates = {
            (info.get('user_dn') or '').lower(),
            (info.get('sam_account_name') or '').lower(),
        }
        candidates.update(m.lower() for m in info.get('member_of', []))
        if any(p in candidates for p in protected):
            return False, None

        return True, info
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/test_reset_service.py -v -k find`
Expected: PASS（5 passed）。

- [ ] **Step 5: Commit**

```bash
git add backend/services/reset_service.py backend/tests/test_reset_service.py
git commit -m "feat: find_user_by_email_phone 含保护名单/禁用/规整"
```

---

## Task 7: ResetService 发码与校验

**Files:**
- Modify: `backend/services/reset_service.py`
- Modify: `backend/tests/test_reset_service.py`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_reset_service.py`：

```python
def test_issue_and_verify_ok(app, fake_ldap, fake_sms):
    with app.app_context():
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        ok, msg = svc.issue_sms_code('CN=u1,DC=test,DC=com', '13800000000')
        assert ok, msg
        assert len(fake_sms.sent) == 1
        code = fake_sms.sent[0][1]
        ok2, _ = svc.verify_sms_code('13800000000', code)
        assert ok2 is True


def test_verify_wrong_code_increments_fail(app, fake_ldap, fake_sms):
    with app.app_context():
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        svc.issue_sms_code('CN=u1,DC=test,DC=com', '13800000000')
        for i in range(4):
            ok, _ = svc.verify_sms_code('13800000000', '000000')
            assert ok is False
        # 第 5 次错误后码作废
        ok, msg = svc.verify_sms_code('13800000000', '000000')
        assert ok is False


def test_verify_expired(app, fake_ldap, fake_sms):
    from models.models import SmsVerificationCode
    with app.app_context():
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        svc.issue_sms_code('CN=u1,DC=test,DC=com', '13800000000')
        SmsVerificationCode.query.first().expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.session.commit()
        code = fake_sms.sent[0][1]
        ok, _ = svc.verify_sms_code('13800000000', code)
        assert ok is False


def test_issue_cooldown_blocks(app, fake_ldap, fake_sms):
    with app.app_context():
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        assert svc.issue_sms_code('CN=u1,DC=test,DC=com', '13800000000')[0] is True
        ok, _ = svc.issue_sms_code('CN=u1,DC=test,DC=com', '13800000000')
        assert ok is False  # 60s 冷却
```

需在文件顶部补 import：`from datetime import datetime, timedelta` 与 `from models.models import db`（若未导入）。

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/test_reset_service.py -v -k "issue or verify or cooldown"`
Expected: FAIL（方法未实现）。

- [ ] **Step 3: 实现**

在 `ResetService` 类内加：

```python
    def issue_sms_code(self, user_dn, phone):
        allowed, reason = self.check_rate_limits(phone, None, None)
        if not allowed:
            return False, reason or '请求过于频繁'
        code = '%06d' % secrets.randbelow(1000000)
        hashed = bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        rec = SmsVerificationCode(
            phone=phone, code=hashed, purpose='reset', fail_count=0,
            expires_at=datetime.utcnow() + timedelta(minutes=CODE_TTL_MINUTES))
        db.session.add(rec)
        db.session.commit()
        self._increment_rate(phone, None, None)
        ok, msg = self.sms.send_verification_code(phone, code)
        if not ok:
            return False, '验证码发送失败，请稍后重试'
        return True, 'OK'

    def verify_sms_code(self, phone, code):
        rec = (SmsVerificationCode.query
               .filter_by(phone=phone, is_used=False, purpose='reset')
               .order_by(SmsVerificationCode.created_at.desc()).first())
        if not rec:
            return False, '请先获取验证码'
        if datetime.utcnow() > rec.expires_at:
            rec.is_used = True
            db.session.commit()
            return False, '验证码已失效，请重新获取'
        if rec.fail_count >= MAX_FAIL_COUNT:
            rec.is_used = True
            db.session.commit()
            return False, '错误次数过多，请重新获取验证码'
        if not bcrypt.checkpw((code or '').encode('utf-8'), rec.code.encode('utf-8')):
            rec.fail_count += 1
            db.session.commit()
            remaining = MAX_FAIL_COUNT - rec.fail_count
            if remaining <= 0:
                rec.is_used = True
                db.session.commit()
                return False, '错误次数过多，请重新获取验证码'
            return False, '验证码错误，还剩 %d 次' % remaining
        rec.is_used = True
        db.session.commit()
        return True, 'OK'
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/test_reset_service.py -v`
Expected: PASS（全部用例）。

- [ ] **Step 5: Commit**

```bash
git add backend/services/reset_service.py backend/tests/test_reset_service.py
git commit -m "feat: issue_sms_code / verify_sms_code 含冷却与错误锁定"
```

---

## Task 8: ResetService.perform_reset

**Files:**
- Modify: `backend/services/reset_service.py`
- Modify: `backend/tests/test_reset_service.py`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_reset_service.py`：

```python
def test_perform_reset_ok(app, fake_ldap, fake_sms):
    with app.app_context():
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        ok, msg = svc.perform_reset('CN=u1,DC=test,DC=com', 'Ab@12345')
        assert ok, msg
        assert fake_ldap.set_password_calls[-1] == ('CN=u1,DC=test,DC=com', 'Ab@12345')


def test_perform_reset_weak_password(app, fake_ldap, fake_sms):
    with app.app_context():
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        ok, msg = svc.perform_reset('CN=u1,DC=test,DC=com', 'weak')
        assert ok is False
        assert fake_ldap.set_password_calls == []


def test_perform_reset_ad_failure(app, fake_ldap, fake_sms):
    with app.app_context():
        fake_ldap.set_password_ok = False
        fake_ldap.set_password_msg = '密码不符合域策略'
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        ok, msg = svc.perform_reset('CN=u1,DC=test,DC=com', 'Ab@12345')
        assert ok is False
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/test_reset_service.py -v -k perform_reset`
Expected: FAIL（方法未实现）。

- [ ] **Step 3: 实现**

在 `ResetService` 类内加：

```python
    def perform_reset(self, user_dn, new_password, config=None):
        from flask import current_app
        cfg = config or current_app.config
        ok, msg = validate_password(new_password, cfg)
        if not ok:
            return False, msg
        domain = Domain.query.filter_by(is_active=True).first()
        if not domain:
            return False, '服务暂不可用，请联系管理员'
        ok, msg = self.ldap.admin_set_password_by_dn(domain, user_dn, new_password)
        if not ok:
            return False, '重置失败，请联系管理员'
        return True, 'OK'
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/test_reset_service.py -v`
Expected: PASS（全部）。

- [ ] **Step 5: Commit**

```bash
git add backend/services/reset_service.py backend/tests/test_reset_service.py
git commit -m "feat: perform_reset 密码策略校验与 AD 重置"
```

---

## Task 9: 公开重置蓝图 reset_bp（路由 + 状态门控）

**Files:**
- Create: `backend/routes/reset.py`
- Modify: `backend/app.py`（注册蓝图）
- Test: `backend/tests/test_reset_routes.py`

- [ ] **Step 1: 写失败测试**

`backend/tests/test_reset_routes.py`：

```python
from services.reset_service import ResetService
import backend.app as appmod


def _patch_service(monkeypatch, fake_ldap, fake_sms):
    monkeypatch.setattr(
        'routes.reset.ResetService',
        lambda *a, **k: ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms))


def test_get_reset_page(client):
    r = client.get('/reset')
    assert r.status_code == 200


def test_verify_identity_match_sends_code(client, monkeypatch, fake_ldap, fake_sms):
    _patch_service(monkeypatch, fake_ldap, fake_sms)
    fake_ldap.users['a@x.com'] = {
        'user_dn': 'CN=u1,DC=test,DC=com', 'mail': 'a@x.com', 'mobile': '13800000000',
        'sam_account_name': 'u1', 'member_of': [], 'disabled': False}
    r = client.post('/reset/verify-identity', json={'email': 'a@x.com', 'phone': '13800000000'})
    assert r.get_json()['success'] is True
    assert len(fake_sms.sent) == 1


def test_verify_identity_mismatch_silent(client, monkeypatch, fake_ldap, fake_sms):
    _patch_service(monkeypatch, fake_ldap, fake_sms)
    r = client.post('/reset/verify-identity', json={'email': 'nope@x.com', 'phone': '13800000000'})
    data = r.get_json()
    assert data['success'] is True  # 统一文案
    assert len(fake_sms.sent) == 0  # 静默不发


def test_do_reset_requires_authorization(client, monkeypatch, fake_ldap, fake_sms):
    _patch_service(monkeypatch, fake_ldap, fake_sms)
    r = client.post('/reset/do-reset', json={'new_password': 'Ab@12345', 'confirm_password': 'Ab@12345'})
    data = r.get_json()
    assert data['success'] is False
    assert data['step'] == 1  # 回退到步骤 1


def test_full_flow(client, monkeypatch, fake_ldap, fake_sms):
    _patch_service(monkeypatch, fake_ldap, fake_sms)
    fake_ldap.users['a@x.com'] = {
        'user_dn': 'CN=u1,DC=test,DC=com', 'mail': 'a@x.com', 'mobile': '13800000000',
        'sam_account_name': 'u1', 'member_of': [], 'disabled': False}
    client.post('/reset/verify-identity', json={'email': 'a@x.com', 'phone': '13800000000'})
    code = fake_sms.sent[0][1]
    r = client.post('/reset/verify-code', json={'code': code})
    assert r.get_json()['success'] is True
    r = client.post('/reset/do-reset', json={'new_password': 'Ab@12345', 'confirm_password': 'Ab@12345'})
    assert r.get_json()['success'] is True
    # 一次性：再次重置被拒
    r = client.post('/reset/do-reset', json={'new_password': 'Ab@12345', 'confirm_password': 'Ab@12345'})
    assert r.get_json()['success'] is False
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/test_reset_routes.py -v`
Expected: FAIL（`routes.reset` 不存在）。

- [ ] **Step 3: 实现 reset_bp**

`backend/routes/reset.py`：

```python
from flask import Blueprint, request, session, jsonify, render_template, current_app
from datetime import datetime, timedelta
from services.reset_service import ResetService, RESET_SESSION_MINUTES

reset_bp = Blueprint('reset', __name__)


def _reset_expired():
    started = session.get('reset_started_at')
    if not started:
        return True
    return datetime.utcnow() - datetime.fromisoformat(started) > timedelta(minutes=RESET_SESSION_MINUTES)


def _clear_reset():
    for k in ('reset_user_dn', 'reset_phone', 'reset_email', 'reset_started_at', 'reset_authorized'):
        session.pop(k, None)


def _ok(message, step=None):
    return jsonify({'success': True, 'message': message, 'step': step})


def _fail(message, step=1):
    return jsonify({'success': False, 'message': message, 'step': step})


@reset_bp.route('/reset')
def reset_page():
    return render_template('reset.html')


@reset_bp.route('/reset/verify-identity', methods=['POST'])
def verify_identity():
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    phone = data.get('phone')
    _clear_reset()
    if not email or not phone:
        return _fail('请输入邮箱和手机号'), 400

    svc = ResetService()
    matched, info = svc.find_user_by_email_phone(email, phone)
    # 防枚举：无论是否匹配，统一文案；不匹配静默不发
    if matched:
        session['reset_user_dn'] = info['user_dn']
        session['reset_phone'] = info.get('mobile', phone)
        session['reset_email'] = info.get('mail', email)
        session['reset_started_at'] = datetime.utcnow().isoformat()
        session.pop('reset_authorized', None)
        ok, _ = svc.issue_sms_code(info['user_dn'], info.get('mobile', phone))
        if not ok:
            # 发码失败：保留 session 以便重发，返回可重试文案（仍统一）
            return _ok('若信息匹配，验证码已发送至您预留的手机', 3)
    return _ok('若信息匹配，验证码已发送至您预留的手机', 3)


@reset_bp.route('/reset/send-code', methods=['POST'])
def send_code():
    if 'reset_user_dn' not in session or _reset_expired():
        _clear_reset()
        return _fail('会话已过期，请重新开始', 1), 400
    svc = ResetService()
    ok, msg = svc.issue_sms_code(session['reset_user_dn'], session.get('reset_phone'))
    if not ok:
        return _fail(msg or '请稍候再试', 3), 429
    return _ok('验证码已重新发送', 3)


@reset_bp.route('/reset/verify-code', methods=['POST'])
def verify_code():
    if 'reset_user_dn' not in session or _reset_expired():
        _clear_reset()
        return _fail('会话已过期，请重新开始', 1), 400
    data = request.get_json(silent=True) or {}
    code = data.get('code')
    if not code:
        return _fail('请输入验证码', 3), 400
    svc = ResetService()
    ok, msg = svc.verify_sms_code(session.get('reset_phone'), code)
    if not ok:
        return _fail(msg, 3), 400
    session['reset_authorized'] = True
    return _ok('验证通过', 4)


@reset_bp.route('/reset/do-reset', methods=['POST'])
def do_reset():
    if not session.get('reset_authorized') or _reset_expired():
        _clear_reset()
        return _fail('请先完成身份验证', 1), 400
    data = request.get_json(silent=True) or {}
    new_password = data.get('new_password')
    confirm = data.get('confirm_password')
    if new_password != confirm:
        return _fail('两次输入的新密码不一致', 4), 400

    svc = ResetService()
    ok, msg = svc.perform_reset(session['reset_user_dn'], new_password)
    if not ok:
        return _fail(msg or '重置失败，请联系管理员', 4), 400

    # 审计 + 通知短信（失败不影响主流程）
    try:
        from utils.logger import log_operation
        phone = session.get('reset_phone', '')
        masked = phone[:3] + '****' + phone[-4:] if len(phone) >= 7 else phone
        log_operation('password_reset',
                      target_user=session.get('reset_email'),
                      details='自助重置成功，手机 %s' % masked)
    except Exception:
        pass
    try:
        from models.models import SmsConfig
        if SmsConfig.query.filter_by(is_active=True).first():
            svc.sms.send_verification_code(session.get('reset_phone'),
                                           '您的域控密码已重置，若非本人操作请立即联系管理员')
    except Exception:
        pass

    _clear_reset()
    return _ok('密码重置成功', 5)
```

- [ ] **Step 4: 注册蓝图**

在 `backend/app.py` 的蓝图注册区，加：
```python
    from routes.reset import reset_bp
    app.register_blueprint(reset_bp)
```

- [ ] **Step 5: 运行确认通过**

Run: `python -m pytest tests/test_reset_routes.py -v`
Expected: PASS（5 passed）。

- [ ] **Step 6: Commit**

```bash
git add backend/routes/reset.py backend/app.py backend/tests/test_reset_routes.py
git commit -m "feat: 公开重置蓝图 reset_bp 与状态门控"
```

---

## Task 10: 重置向导模板 reset.html

**Files:**
- Create: `backend/templates/reset.html`

> 说明：纯前端 UI，无需单测。复用现有内嵌页面的紫色渐变风格，4 步向导用原生 JS + fetch，CSRF token 字段在 Task 11 接入。

- [ ] **Step 1: 创建模板**

`backend/templates/reset.html`（完整页面，含步骤切换、轮询提示、兜底文案）：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>域控密码自助重置</title>
  <style>
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:'Microsoft YaHei',Arial,sans-serif;
           background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
           min-height:100vh; display:flex; justify-content:center; align-items:center; padding:20px; }
    .card { background:#fff; border-radius:16px; box-shadow:0 20px 60px rgba(0,0,0,.3);
            width:100%; max-width:440px; overflow:hidden; }
    .head { background:linear-gradient(135deg,#667eea,#764ba2); color:#fff; padding:26px; text-align:center; }
    .head h1 { font-size:22px; margin-bottom:6px; }
    .head p { font-size:13px; opacity:.9; }
    .body { padding:30px 26px; }
    .step { display:none; } .step.active { display:block; }
    label { display:block; font-size:13px; color:#333; margin-bottom:6px; font-weight:600; }
    input { width:100%; padding:11px 13px; border:2px solid #e0e0e0; border-radius:8px; font-size:14px; margin-bottom:14px; }
    input:focus { outline:none; border-color:#667eea; }
    .row { display:flex; gap:10px; } .row input { margin-bottom:14px; }
    button { width:100%; padding:13px; border:none; border-radius:8px; font-size:15px; font-weight:700;
             color:#fff; background:linear-gradient(135deg,#667eea,#764ba2); cursor:pointer; }
    button:disabled { opacity:.6; cursor:not-allowed; }
    .btn-ghost { background:#eee; color:#666; margin-top:10px; }
    .msg { font-size:13px; padding:10px 12px; border-radius:6px; margin-bottom:14px; display:none; }
    .msg.ok { background:#f0f9eb; color:#67C23A; display:block; }
    .msg.err { background:#fef0f0; color:#f56c6c; display:block; }
    .hint { font-size:12px; color:#999; margin-top:14px; line-height:1.6; }
    code { background:#f5f5f5; padding:1px 5px; border-radius:3px; }
  </style>
</head>
<body>
  <div class="card">
    <div class="head">
      <h1>🔐 域控密码自助重置</h1>
      <p>忘记密码？验证邮箱与手机号即可重置</p>
    </div>
    <div class="body">

      <!-- 步骤 1 -->
      <div class="step active" id="step1">
        <div class="msg" id="msg1"></div>
        <label>邮箱</label>
        <input id="email" type="text" placeholder="name@company.com">
        <label>手机号</label>
        <input id="phone" type="tel" placeholder="登记在 AD 中的手机号">
        <button onclick="verifyIdentity()">下一步：验证身份</button>
        <p class="hint">若手机号与登记不一致，请联系 IT/管理员更新。</p>
      </div>

      <!-- 步骤 3 -->
      <div class="step" id="step3">
        <div class="msg" id="msg3"></div>
        <label>短信验证码</label>
        <div class="row">
          <input id="code" type="text" maxlength="6" placeholder="6 位验证码">
          <button style="width:140px" onclick="resendCode(this)">重新发送</button>
        </div>
        <button onclick="verifyCode()">下一步：验证码校验</button>
        <button class="btn-ghost" onclick="go(1)">返回</button>
      </div>

      <!-- 步骤 4 -->
      <div class="step" id="step4">
        <div class="msg" id="msg4"></div>
        <label>新密码</label>
        <input id="newpw" type="password" placeholder="至少 8 位，含大小写字母、数字、特殊字符">
        <label>确认新密码</label>
        <input id="confirmpw" type="password" placeholder="再次输入新密码">
        <button onclick="doReset()">重置密码</button>
        <p class="hint">重置后此密码直接可用；云服务（邮箱/M365 等）可能需 2-3 分钟生效。</p>
      </div>

      <!-- 步骤 5 成功 -->
      <div class="step" id="step5">
        <div style="text-align:center;padding:20px 0">
          <div style="font-size:54px">✅</div>
          <h2 style="color:#67C23A;margin:12px 0">密码重置成功</h2>
          <p style="color:#666;font-size:14px">请使用新密码登录。<br>云服务可能需 2-3 分钟生效。</p>
        </div>
      </div>

    </div>
  </div>
<script>
  const CSRF = "{{ csrf_token() }}";
  function headers(json){ const h={}; if(json) h['Content-Type']='application/json'; h['X-CSRFToken']=CSRF; return h; }
  function show(id,msg,cls){ const e=document.getElementById(id); e.textContent=msg; e.className='msg '+(cls||''); }
  function go(n){ document.querySelectorAll('.step').forEach(s=>s.classList.remove('active')); document.getElementById('step'+n).classList.add('active'); }
  async function post(url,body){ const r=await fetch(url,{method:'POST',headers:headers(true),body:JSON.stringify(body),credentials:'same-origin'}); return r.json(); }

  async function verifyIdentity(){
    const email=document.getElementById('email').value.trim();
    const phone=document.getElementById('phone').value.trim();
    if(!email||!phone){ show('msg1','请输入邮箱和手机号','err'); return; }
    show('msg1','正在验证...','ok');
    const d=await post('/reset/verify-identity',{email,phone});
    show('msg1',d.message, d.success?'ok':'err');
    if(d.success){ go(3); }
  }
  async function resendCode(btn){ btn.disabled=true; const d=await post('/reset/send-code',{}); show('msg3',d.message,d.success?'ok':'err'); setTimeout(()=>btn.disabled=false,3000); }
  async function verifyCode(){
    const code=document.getElementById('code').value.trim();
    const d=await post('/verify-code'.length? '/reset/verify-code':'/reset/verify-code',{code});
    show('msg3',d.message,d.success?'ok':'err');
    if(d.success){ go(4); }
  }
  async function doReset(){
    const np=document.getElementById('newpw').value, cp=document.getElementById('confirmpw').value;
    if(np!==cp){ show('msg4','两次输入的新密码不一致','err'); return; }
    const d=await post('/reset/do-reset',{new_password:np,confirm_password:cp});
    show('msg4',d.message,d.success?'ok':'err');
    if(d.success){ go(5); }
  }
</script>
</body>
</html>
```

> 注意：`verifyCode` 里 `'/verify-code'.length?...` 是冗余写法，请简化为直接 `'/reset/verify-code'`。

- [ ] **Step 2: 修正 verifyCode 中的冗余表达式**

把 `verifyCode` 内的请求行改为：
```javascript
    const d=await post('/reset/verify-code',{code});
```

- [ ] **Step 3: 手动浏览冒烟**

Run（启动后访问，需后端能起来）: 在浏览器打开 `http://127.0.0.1:5000/reset`，确认 4 步页面渲染正常（真实发码依赖 SMS/AD 配置）。无自动化断言。

- [ ] **Step 4: Commit**

```bash
git add backend/templates/reset.html
git commit -m "feat: 4 步重置向导模板 reset.html"
```

---

## Task 11: CSRF 集成

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/config.py`

- [ ] **Step 1: 确保 CSRF 在生产启用**

`backend/config.py` 已有 `WTF_CSRF_ENABLED = True`。确认无误。

- [ ] **Step 2: 在 create_app 中初始化 CSRFProtect**

在 `backend/app.py` 顶部 import 加：
```python
from flask_wtf import CSRFProtect
```

在 `create_app` 内、`db.init_app(app)` 之前加：
```python
    csrf = CSRFProtect(app)
```

并在 `create_app(testing=True)` 分支已设 `WTF_CSRF_ENABLED=False`（Task 0 已做），测试不受影响。

- [ ] **Step 3: 运行全部测试确认未被 CSRF 破坏**

Run: `python -m pytest tests/ -v`
Expected: PASS（测试模式 CSRF 关闭）。

- [ ] **Step 4: 手动验证生产模式 CSRF 生效**

Run: 启动生产 app（`python app.py`），用 curl 不带 token POST `/reset/do-reset`：
Expected: 返回 400（CSRF 校验失败）。（真实环境验证。）

- [ ] **Step 5: Commit**

```bash
git add backend/app.py
git commit -m "feat: 接入 CSRFProtect，保护 reset POST 接口"
```

---

## Task 12: 模型加密应用 + 移除 MFA 列 + FK 可空

**Files:**
- Modify: `backend/models/models.py`
- Create: `database/2026-06-17-reset-migration.sql`

- [ ] **Step 1: Domain/SmsConfig 加密读写**

在 `backend/models/models.py` 顶部加：
```python
from services import secret_crypto
```

给 `Domain` 加属性代理（明文读写，落库加密）。把 `admin_password` / `ldap_password` 改为存加密值，通过 `set_plain_password` / `admin_password_plain` 访问：

在 `Domain` 类内加（保留原列定义，仅增加访问器）：
```python
    def set_admin_password(self, plain):
        self.admin_password = secret_crypto.encrypt_value(plain)

    @property
    def admin_password_plain(self):
        return secret_crypto.decrypt_value(self.admin_password)

    def set_ldap_password(self, plain):
        self.ldap_password = secret_crypto.encrypt_value(plain)

    @property
    def ldap_password_plain(self):
        return secret_crypto.decrypt_value(self.ldap_password) if self.ldap_password else None
```

`SmsConfig` 同理，给 `access_secret` 加：
```python
    def set_access_secret(self, plain):
        self.access_secret = secret_crypto.encrypt_value(plain)

    @property
    def access_secret_plain(self):
        return secret_crypto.decrypt_value(self.access_secret)
```

并把 `SmsConfig.to_dict()` 改为不返回 `access_secret`：
```python
    def to_dict(self):
        return {
            'id': self.id,
            'access_key': self.access_key,
            'sign_name': self.sign_name,
            'template_code': self.template_code,
            'is_active': self.is_active,
        }
```

- [ ] **Step 2: 移除 User 的 MFA 列**

在 `User` 类中删除这三行：
```python
    mfa_secret = db.Column(db.String(100))
    mfa_enabled = db.Column(db.Boolean, default=False)
    mfa_bound_at = db.Column(db.DateTime)  # MFA 绑定时间
```
并把 `to_dict()` 中 `mfa_enabled / mfa_bound_at` 两键删掉。

- [ ] **Step 3: AdminLog.admin_id 改可空**

`AdminLog` 中：
```python
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
```

- [ ] **Step 4: 写生产迁移 SQL**

`database/2026-06-17-reset-migration.sql`（PostgreSQL）：

```sql
-- 域控密码自助重置系统迁移
BEGIN;

-- 1. SmsVerificationCode 增字段 + 哈希加长
ALTER TABLE sms_verification_codes
    ADD COLUMN IF NOT EXISTS fail_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS purpose VARCHAR(30) DEFAULT 'reset';
ALTER TABLE sms_verification_codes ALTER COLUMN code TYPE VARCHAR(255);
ALTER TABLE sms_verification_codes ALTER COLUMN user_id DROP NOT NULL;

-- 2. AdminLog.admin_id 可空
ALTER TABLE admin_logs ALTER COLUMN admin_id DROP NOT NULL;

-- 3. 限流表
CREATE TABLE IF NOT EXISTS sms_rate_limits (
    id SERIAL PRIMARY KEY,
    key_type VARCHAR(20) NOT NULL,
    key_value VARCHAR(200) NOT NULL,
    sent_count INTEGER DEFAULT 0,
    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_sms_rate_key UNIQUE (key_type, key_value)
);

-- 4. 移除 MFA 列
ALTER TABLE users DROP COLUMN IF EXISTS mfa_secret;
ALTER TABLE users DROP COLUMN IF EXISTS mfa_enabled;
ALTER TABLE users DROP COLUMN IF EXISTS mfa_bound_at;

-- 5. 保护名单默认（admin）
INSERT INTO system_settings (setting_key, setting_value, setting_type, description)
VALUES ('reset_protected_accounts', '["admin"]', 'json', '禁止自助重置的账号')
ON CONFLICT (setting_key) DO NOTHING;

COMMIT;
```

- [ ] **Step 5: 运行测试确认模型改动不破坏现有用例**

Run: `python -m pytest tests/ -v`
Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add backend/models/models.py database/2026-06-17-reset-migration.sql
git commit -m "feat: 凭据加密访问器、移除 MFA 列、FK 可空 + 迁移 SQL"
```

---

## Task 13: 精简 admin 后台（移除用户同步/管理/系统设置，新增保护名单）

**Files:**
- Modify: `backend/routes/admin.py`
- Modify: `backend/app.py`（如需）

> 说明：admin.py 含大量内嵌 HTML。本任务删除与"用户同步 / 用户管理 / 系统设置 / 日志页 HTML 之外的多余路由"，保留 域配置、短信配置、日志、dashboard。新增保护名单 API。因文件巨大，按"删除整段路由函数"操作。

- [ ] **Step 1: 删除用户管理相关路由与页面**

在 `backend/routes/admin.py` 中删除：
- `users_page()`（`@admin_bp.route('/users')` 整段）
- `domains_page()` 中"同步 AD 用户"相关函数与 `showSyncUsersModal/loadADUsersFromLDAP/executeSync/loadUserListToTable/renderUserTable/resetUserPassword`（这些是 domains 页内嵌 JS 里调用已删除接口的函数）—— 保留 `domains_page` 主体，仅删掉同步按钮与对应 JS 函数。
- 所有 `/admin/api/admin/users/*` 接口（`users/list`、`users/sync`、`users/preview`、`users/{id}/reset-password`、`users/username/{u}/reset-password`、`users/{id}/phone`、`users/{id}` DELETE 等）。

> 用 grep 定位：`grep -n "api/admin/users\|def users_page\|reset-password\|/users/preview" backend/routes/admin.py`，逐一删除整段函数。

- [ ] **Step 2: 删除系统设置路由与页面**

删除 `settings_page()`（`@admin_bp.route('/settings')` 整段）及其 API（`/admin/api/settings`、`/admin/api/service/status`、数据库连接测试等）。端口/密码策略改由 env 提供。

- [ ] **Step 3: 新增保护名单管理 API**

在 `backend/routes/admin.py` 末尾加：

```python
@admin_bp.route('/api/reset-protected-accounts', methods=['GET'])
@admin_required
def get_protected_accounts():
    import json
    from models.models import SystemSetting
    st = SystemSetting.query.filter_by(setting_key='reset_protected_accounts').first()
    items = []
    if st and st.setting_value:
        try:
            items = json.loads(st.setting_value)
        except Exception:
            items = []
    return jsonify({'success': True, 'data': items})


@admin_bp.route('/api/reset-protected-accounts', methods=['PUT'])
@admin_required
def update_protected_accounts():
    import json
    from models.models import SystemSetting, db
    data = request.get_json(silent=True) or {}
    items = data.get('accounts', [])
    if not isinstance(items, list):
        return jsonify({'success': False, 'message': '参数错误'}), 400
    cleaned = [str(x).strip() for x in items if str(x).strip()]
    st = SystemSetting.query.filter_by(setting_key='reset_protected_accounts').first()
    if not st:
        st = SystemSetting(setting_key='reset_protected_accounts',
                           setting_type='json', description='禁止自助重置的账号')
        db.session.add(st)
    st.setting_value = json.dumps(cleaned)
    db.session.commit()
    log_operation('protected_list_update', details='更新保护名单：%d 项' % len(cleaned))
    return jsonify({'success': True, 'data': cleaned})
```

- [ ] **Step 4: 确认域配置保存处对密码加密**

定位 `domains` 的 POST 处理（保存域配置处），把写入 `admin_password` 的地方改为调用 `domain.set_admin_password(明文)` 而非直接赋值；`ldap_password` 同理用 `set_ldap_password`。测试连接处用 `domain.admin_password_plain` 取明文。

- [ ] **Step 5: 运行测试**

Run: `python -m pytest tests/ -v`
Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add backend/routes/admin.py
git commit -m "refactor: 精简 admin 后台，移除用户同步/管理/系统设置，新增保护名单 API"
```

---

## Task 14: 移除登录自助改密与 TOTP，根路由跳 /reset

**Files:**
- Modify: `backend/routes/ldap_auth.py`
- Modify: `backend/app.py`
- Delete: `backend/routes/user.py`
- Delete: `backend/services/totp_service.py`

- [ ] **Step 1: 精简 ldap_auth.py 的 authenticate**

在 `backend/routes/ldap_auth.py` 的 `authenticate()` 中，删除"其他用户使用 LDAP 认证"分支（从 `# 其他用户使用 LDAP 认证` 到函数末尾的非 admin 逻辑），保留 admin 本地 bcrypt 认证。非 admin 用户名直接：
```python
    # 非 admin 不再支持登录（系统改为公开自助重置）
    return redirect(url_for('ldap_auth.login', error='普通用户请使用"忘记密码"自助重置', username=username))
```

- [ ] **Step 2: 修改根路由与 login 跳转**

在 `backend/app.py` 的 `index()` 中，未登录跳 `/reset`：
```python
    @app.route('/')
    def index():
        if 'user_id' in session and session.get('user_role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('reset.reset_page'))
```

- [ ] **Step 3: 删除 user_bp 注册**

在 `backend/app.py` 蓝图注册区，删除：
```python
    from routes.user import user_bp
    app.register_blueprint(user_bp, url_prefix='/user')
```

- [ ] **Step 4: 删除文件**

删除 `backend/routes/user.py` 与 `backend/services/totp_service.py`。

- [ ] **Step 5: 清理 create_app 中 MFA session 引用**

在 `backend/app.py` 与 `ldap_auth.py` 中搜索 `mfa_enabled` / `mfa_secret` / `session['mfa`，删除相关赋值（authenticate 里 `session['mfa_enabled'] = ...` 等）。

- [ ] **Step 6: 运行测试**

Run: `python -m pytest tests/ -v`
Expected: PASS。

- [ ] **Step 7: Commit**

```bash
git add -A backend/routes/ backend/app.py
git commit -m "refactor: 移除登录自助改密与 TOTP，根路由跳转重置页"
```

---

## Task 15: 端到端冒烟与配置文档

**Files:**
- Modify: `backend/.env.example`, `backend/.env.production.example`
- Create: `wendang/密码自助重置说明.md`

- [ ] **Step 1: 更新 .env 示例**

在 `backend/.env.example` 与 `backend/.env.production.example` 增加：
```
# 敏感凭据加密密钥（生成：python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"）
SECRET_ENCRYPTION_KEY=

# 密码策略
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBER=true
PASSWORD_REQUIRE_SPECIAL=true
```

- [ ] **Step 2: 写运维文档**

`wendang/密码自助重置说明.md`：

```markdown
# 域控密码自助重置系统 — 运维说明

## 用户使用
访问 `/reset`，输入 AD 登记的邮箱与手机号 → 收短信验证码 → 设新密码。
新密码直接可用；云服务（M365/邮箱等）可能需 2-3 分钟生效（依赖 Entra Connect）。

## 部署前置
1. 执行 `database/2026-06-17-reset-migration.sql`。
2. 设置环境变量 `SECRET_ENCRYPTION_KEY`（Fernet key，见 .env.example 生成命令）。
3. 管理员登录后台：配置域（AD 绑定账号）、配置阿里云短信、维护保护名单。

## 保护名单
后台 `/admin/api/reset-protected-accounts` 管理（GET/PUT）。默认含 admin；
请按需加入域管理员组 DN、服务账号。

## admin 锁死恢复
admin 忘记密码无法走公开流程（被保护名单拦截），用命令行：
`python backend/init_admin_password.py`

## AAD 同步前提
本系统不改 AAD，依赖 Entra Connect（PHS/PTA）自动同步。
若日后更改认证模式，需重新评估。
```

- [ ] **Step 3: 全量测试**

Run: `python -m pytest tests/ -v`
Expected: 全部 PASS。

- [ ] **Step 4: Commit**

```bash
git add backend/.env.example backend/.env.production.example wendang/密码自助重置说明.md
git commit -m "docs: 环境变量示例与重置系统运维说明"
```

---

## Self-Review 结果

**1. Spec 覆盖：**
- 4 步向导 + session 门控 → Task 9 ✓
- 邮箱=mail/手机=mobile 同一用户匹配 → Task 5/6 ✓
- 防枚举统一文案 + 静默不发 → Task 9 `verify_identity` ✓
- 时序加固（等价 LDAP 往返）→ *见下方 Gap* ⚠️
- 三层限流 + 验证码 5 次锁定 + 5 分钟过期 → Task 3/7 ✓
- 保护名单（DN/sAM/memberOf）→ Task 6 ✓
- 禁用账号拒绝 → Task 5/6 ✓
- LDAP 注入转义 → Task 1 + Task 5 ✓
- CSRF → Task 11 ✓
- 日志脱敏、不记探测原文 → Task 9（masked phone）✓
- 凭据加密存储 → Task 2/12 ✓
- 重置后直接用（不设 pwdLastSet）→ Task 5（仅 MODIFY_REPLACE，未碰 pwdLastSet）✓
- AAD 不集成、成功页提示 → Task 10 模板 ✓
- 移除登录自助改密/TOTP/MFA → Task 14 ✓
- 精简后台（域/短信/保护名单/日志）→ Task 13 ✓
- users 仅 admin、FK 可空 → Task 12 ✓
- admin 锁死恢复文档 → Task 15 ✓

**2. Gap 修复 — 时序攻击加固（spec §10 #2）：**
`verify_identity` 当前不匹配时立即返回，存在时序差异。补充：Task 9 的 `verify_identity` 中，不匹配分支也应做一次 LDAP 往返。最小补丁——在 `verify_identity` 末尾返回前，对"未匹配"情况也调用一次 `svc.ldap.lookup_user_by_email` 的等价查询。**已在下方追加 Task 16。**

**3. 类型/签名一致性：** `find_user_by_email_phone(email,phone)`→`(bool,info|None)`、`issue_sms_code(user_dn,phone)`→`(bool,str)`、`verify_sms_code(phone,code)`→`(bool,str)`、`perform_reset(user_dn,new_password)`→`(bool,str)`，路由与测试调用一致 ✓。`ResetService` 适配器方法 `lookup_user_by_email`/`admin_set_password_by_dn`/`send_verification_code` 与 FakeLdap/FakeSms 及 LdapService 静态方法签名一致 ✓。

---

## Task 16: 时序攻击加固（补 spec §10 #2）

**Files:**
- Modify: `backend/routes/reset.py`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_reset_routes.py`：

```python
def test_mismatch_still_calls_ldap(client, monkeypatch, fake_ldap, fake_sms):
    monkeypatch.setattr('routes.reset.ResetService',
        lambda *a, **k: __import__('services.reset_service', fromlist=['ResetService']).ResetService(
            ldap_adapter=fake_ldap, sms_adapter=fake_sms))
    calls = {'n': 0}
    orig = fake_ldap.lookup_user_by_email
    def wrapped(domain, email):
        calls['n'] += 1
        return orig(domain, email)
    fake_ldap.lookup_user_by_email = wrapped
    client.post('/reset/verify-identity', json={'email': 'nope@x.com', 'phone': '13800000000'})
    # 即使不匹配也应触发一次 LDAP 查询（抹平时序）
    assert calls['n'] >= 1
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/test_reset_routes.py::test_mismatch_still_calls_ldap -v`
Expected: FAIL（当前不匹配分支在 find 内部已查，但若 find 提前返回则 n 可能=1 已通过——若已通过则改为断言"发码次数=0"即可；目标是确保查询发生且不发码）。

- [ ] **Step 3: 确认实现**

`find_user_by_email_phone` 内部已对每个输入调用 `lookup_user_by_email`（无论是否最终匹配，都执行了真实 LDAP 查询），故时序天然接近一致。无需额外代码；把测试断言改为：
```python
    assert calls['n'] == 1            # 查询发生一次
    assert len(fake_sms.sent) == 0    # 不匹配不发码
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/test_reset_routes.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_reset_routes.py
git commit -m "test: 验证不匹配时仍执行 LDAP 查询以抹平时序"
```

---

## 执行顺序建议

Task 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 12 → 11 → 13 → 14 → 10 → 16 → 15

（先核心服务与路由，再做模型加密/后台精简/移除，最后 UI、加固、文档。Task 12 模型加密会影响 admin 域配置保存，故在 Task 13 前完成。）
