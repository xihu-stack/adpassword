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
    d = c.post('/reset/verify-identity', json={'email': 'huxi@helixon.com', 'phone': '13800000000'}).get_json()
    assert d['success'] and d.get('demo_code')
    assert c.post('/reset/verify-code', json={'code': d['demo_code']}).get_json()['success']
    r = c.post('/reset/do-reset', json={'new_password': 'Huxi@12345!',
                                        'confirm_password': 'Huxi@12345!'})
    d = r.get_json()
    assert not d['success'] and '用户名' in d['message'], d


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
