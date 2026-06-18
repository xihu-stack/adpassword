from datetime import datetime, timedelta
from models.models import db, SmsVerificationCode
from services.reset_service import ResetService
from services.reset_service import normalize_email, normalize_phone, validate_password


def test_rate_limit_blocks_after_5_per_hour(app, fake_ldap, fake_sms):
    with app.app_context():
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        phone = '13800000000'
        # Simulate 5 prior sends (increment writes the counts)
        for _ in range(5):
            svc._increment_rate(phone, 'a@b.com', '1.2.3.4')
        # 6th request for same phone should be blocked by the hourly cap
        allowed, reason = svc.check_rate_limits(phone, 'a@b.com', '1.2.3.4')
        assert not allowed, reason


def test_rate_limit_cooldown(app, fake_ldap, fake_sms):
    with app.app_context():
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        # A verification code created seconds ago triggers the 60s cooldown
        db.session.add(SmsVerificationCode(
            phone='13800000000', code='x', expires_at=datetime.utcnow() + timedelta(minutes=5)))
        db.session.commit()
        allowed, reason = svc.check_rate_limits('13800000000', 'a@b.com', '1.2.3.4')
        assert not allowed  # cooldown


def test_rate_limit_allows_fresh(app, fake_ldap, fake_sms):
    with app.app_context():
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        allowed, reason = svc.check_rate_limits('13800000000', 'a@b.com', '1.2.3.4')
        assert allowed, reason


def test_normalize_email():
    assert normalize_email('  John@X.COM ') == 'john@x.com'
    assert normalize_email(None) == ''


def test_normalize_phone():
    assert normalize_phone('138 0000 0000') == '13800000000'
    assert normalize_phone('+86-138-0000-0000') == '13800000000'
    assert normalize_phone('8613800000000') == '13800000000'


def test_validate_password_policy(app):
    with app.app_context():
        assert validate_password('Ab@12345', app.config)[0] is True
        assert validate_password('short', app.config)[0] is False
        assert validate_password('alllowercase1!', app.config)[0] is False      # 无大写
        assert validate_password('NOLOWERCASE1!', app.config)[0] is False       # 无小写
        assert validate_password('Abcdefg!', app.config)[0] is False            # 无数字
        assert validate_password('Abcdefg1', app.config)[0] is False            # 无特殊字符
