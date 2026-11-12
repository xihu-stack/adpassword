"""公开重置流程（DEMO 模式端到端）+ 输入校验"""
import re


def test_reset_page_renders(anon_client):
    r = anon_client.get('/reset')
    assert r.status_code == 200
    assert '密码自助重置' in r.get_data(as_text=True)


def test_full_reset_flow_demo(anon_client):
    c = anon_client
    d = c.post('/reset/verify-identity', json={'email': 'a@b.com', 'phone': '13800000000'}).get_json()
    assert d['success'] and d.get('demo_code'), d
    assert c.post('/reset/verify-code', json={'code': d['demo_code']}).get_json()['success']
    r = c.post('/reset/do-reset', json={'new_password': 'NewP@ssw0rd9!',
                                        'confirm_password': 'NewP@ssw0rd9!'})
    assert r.get_json()['success'], r.get_json()


def test_identity_mismatch_rejected(anon_client):
    d = anon_client.post('/reset/verify-identity',
                         json={'email': 'a@b.com', 'phone': '13900000000'}).get_json()
    assert not d['success']
    assert '不匹配' in d['message']


def test_oversized_input_rejected(anon_client):
    long_email = 'a' * 300 + '@x.com'
    d = anon_client.post('/reset/verify-identity',
                         json={'email': long_email, 'phone': '13800000000'}).get_json()
    assert not d['success']


def test_password_containing_username_rejected(anon_client):
    c = anon_client
    d = c.post('/reset/verify-identity', json={'email': 'demo@demo.com', 'phone': '13800000000'}).get_json()
    assert d['success'] and d.get('demo_code')
    assert c.post('/reset/verify-code', json={'code': d['demo_code']}).get_json()['success']
    r = c.post('/reset/do-reset', json={'new_password': 'Demo@12345!',
                                        'confirm_password': 'Demo@12345!'})
    d = r.get_json()
    assert not d['success'] and '用户名' in d['message'], d


def _authorized_client(c):
    """走完身份+验证码，返回已授权的客户端（DEMO）"""
    d = c.post('/reset/verify-identity', json={'email': 'demo@demo.com', 'phone': '13800000000'}).get_json()
    assert d['success'] and d.get('demo_code'), d
    assert c.post('/reset/verify-code', json={'code': d['demo_code']}).get_json()['success']
    return c


def test_do_reset_missing_fields_is_400_not_500(anon_client):
    """缺 new_password/confirm_password 应 400 友好提示，而非 None.lower() 抛 500"""
    c = _authorized_client(anon_client)
    r = c.post('/reset/do-reset', json={})
    assert r.status_code == 400, r.status_code
    assert not r.get_json()['success']


def test_do_reset_non_string_password_is_400_not_500(anon_client):
    """JSON 传数字密码（int == int 通过相等检查）同样应 400 而非 500"""
    c = _authorized_client(anon_client)
    r = c.post('/reset/do-reset', json={'new_password': 12345678, 'confirm_password': 12345678})
    assert r.status_code == 400, r.status_code


def test_do_reset_oversized_password_rejected(anon_client):
    """超长密码应提前拒绝（AD 上限 256，超长只会拿到含糊的域策略报错）"""
    c = _authorized_client(anon_client)
    pw = 'Aa1!' + 'x' * 200
    r = c.post('/reset/do-reset', json={'new_password': pw, 'confirm_password': pw})
    assert r.status_code == 400, r.status_code


def test_verify_code_non_string_is_400_not_500(anon_client):
    """验证码传数字应 400，且不消耗已发验证码（随后正确验证码仍通过）"""
    c = anon_client
    d = c.post('/reset/verify-identity', json={'email': 'demo@demo.com', 'phone': '13800000000'}).get_json()
    r = c.post('/reset/verify-code', json={'code': 123456})
    assert r.status_code == 400, r.status_code
    assert c.post('/reset/verify-code', json={'code': d['demo_code']}).get_json()['success']


def test_cleanup_expired_safe(app):
    from services.reset_service import ResetService
    with app.app_context():
        ResetService().cleanup_expired()  # 空库也不应抛异常


def test_rate_limit_key_truncation(app):
    """超长 email 的限流键应被截断且预留/退还对称（不抛异常）"""
    with app.app_context():
        from services.reset_service import ResetService
        svc = ResetService()
        long_email = 'a' * 300 + '@x.com'
        ok, _ = svc._reserve_quota('13811112222', long_email, '1.2.3.4')
        assert ok
        svc._refund_quota('13811112222', long_email, '1.2.3.4')
