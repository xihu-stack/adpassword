"""共享测试夹具：DEMO 模式应用 + 已登录管理员客户端。

运行：项目根目录执行  python -m pytest tests -v
（conftest 自动把 backend 加入 sys.path；使用临时文件 SQLite + WAL，贴近生产行为）
"""
import os
import sys
import tempfile

import pytest

BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault('SECRET_KEY', 'test-key-123')
# 文件库（非 :memory:）：WAL 等生产特性才生效
os.environ.setdefault('DATABASE_URL', 'sqlite:///' + os.path.join(tempfile.mkdtemp(prefix='ad2_test_'), 'test.db').replace('\\', '/'))
os.environ.setdefault('DEMO_MODE', 'true')

from cryptography.fernet import Fernet
os.environ.setdefault('SECRET_ENCRYPTION_KEY', Fernet.generate_key().decode())


@pytest.fixture(scope='session')
def app():
    from app import create_app
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, DEMO_MODE=True)
    return app


@pytest.fixture(autouse=True)
def _clean_volatile_tables(app):
    """每个测试前后清空验证码/限流表：DEMO 模式所有测试共用同一手机号，
    否则 60s 冷却与小时配额会跨用例互踩。"""
    def _clean():
        with app.app_context():
            from models.models import db, SmsVerificationCode, SmsRateLimit
            SmsVerificationCode.query.delete()
            SmsRateLimit.query.delete()
            db.session.commit()
    _clean()
    yield
    _clean()


@pytest.fixture()
def admin_client(app):
    """已登录管理员的测试客户端"""
    c = app.test_client()
    with c.session_transaction() as s:
        s['user_id'] = 1
        s['user_role'] = 'admin'
        s['username'] = 'admin'
    return c


@pytest.fixture()
def anon_client(app):
    return app.test_client()
