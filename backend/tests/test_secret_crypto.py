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


def test_domain_password_accessors(app):
    from models.models import Domain
    with app.app_context():
        d = Domain.query.first()
        d.set_admin_password('secret123')
        assert d.admin_password != 'secret123'          # stored encrypted
        assert d.admin_password_plain == 'secret123'    # decrypts back


def test_smsconfig_accessors(app):
    from models.models import SmsConfig
    with app.app_context():
        c = SmsConfig(access_key='ak', sign_name='s', template_code='tc', is_active=True)
        c.set_access_secret('topsecret')
        assert c.access_secret != 'topsecret'
        assert c.access_secret_plain == 'topsecret'
        assert 'access_secret' not in c.to_dict()       # never leaked via to_dict
