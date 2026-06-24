from services.reset_service import ResetService


def _patch_service(monkeypatch, fake_ldap, fake_sms):
    monkeypatch.setattr(
        'routes.reset.ResetService',
        lambda *a, **k: ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms))


def test_get_reset_page(client):
    r = client.get('/reset')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert '密码自助重置' in body
    assert 'id="step1"' in body and 'id="step4"' in body


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


def test_mismatch_still_queries_ldap(client, monkeypatch, fake_ldap, fake_sms):
    # Even on a non-matching identity, the LDAP lookup must still happen
    # (timing equalization) and NO sms is sent.
    monkeypatch.setattr('routes.reset.ResetService',
        lambda *a, **k: ResetService(ldap_adapter=fake_ldap, sms_adapter=fake_sms))
    calls = {'n': 0}
    orig = fake_ldap.lookup_user_by_email
    def counting(domain, email):
        calls['n'] += 1
        return orig(domain, email)
    fake_ldap.lookup_user_by_email = counting
    r = client.post('/reset/verify-identity', json={'email': 'nope@x.com', 'phone': '13800000000'})
    assert r.get_json()['success'] is True   # unified message (anti-enumeration)
    assert calls['n'] == 1                    # LDAP query happened on mismatch
    assert len(fake_sms.sent) == 0            # no SMS sent on mismatch
