from datetime import datetime, timedelta
from models.models import db, SmsVerificationCode
from services.reset_service import ResetService


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
