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
    _seed_user(fake_ldap, 'a@x.com', '13800000000',
               member_of=['CN=Domain Admins,CN=Groups,DC=test,DC=com'])
    with app.app_context():
        from models.models import SystemSetting, db
        st = SystemSetting.query.filter_by(setting_key='reset_protected_accounts').first()
        st.setting_value = '["CN=Domain Admins,CN=Groups,DC=test,DC=com"]'
        db.session.commit()
        svc = ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms)
        matched, info = svc.find_user_by_email_phone('a@x.com', '13800000000')
        assert matched is False


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
