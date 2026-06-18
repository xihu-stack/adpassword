import os
# Must set env BEFORE importing config/app, so Config's module-level validation passes
os.environ.setdefault('SECRET_KEY', 'testing-secret-key-do-not-use-in-prod')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('TEST_DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('CORS_ORIGINS', '')

from cryptography.fernet import Fernet
# A deterministic-enough Fernet key for tests
os.environ.setdefault('SECRET_ENCRYPTION_KEY', Fernet.generate_key().decode())

import pytest
from app import create_app
from models.models import db


class FakeLdap:
    """Programmable LDAP adapter stand-in."""
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
