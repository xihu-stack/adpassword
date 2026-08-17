"""管理后台：页面/接口/安全（XSS 转义、白名单、日期筛选、use_ssl、审计）"""
import re


def _esc(s):
    return str(s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


ALL_PAGES = [
    '/admin/dashboard', '/admin/domains', '/admin/sms', '/admin/logs',
    '/admin/protected', '/admin/security', '/admin/change-password', '/admin/manual',
]


def test_admin_pages_render(admin_client):
    for url in ALL_PAGES:
        r = admin_client.get(url)
        assert r.status_code == 200, url


def test_admin_pages_require_login(app, anon_client):
    for url in ALL_PAGES:
        r = anon_client.get(url)
        assert r.status_code == 302 and '/login' in r.headers['Location'], url


def test_logs_page_escapes_untrusted_fields(admin_client, app):
    """存储型 XSS 防线：日志页渲染脚本必须对所有动态字段 esc() 转义"""
    with app.app_context():
        from models.models import db, AdminLog
        db.session.add(AdminLog(action='reset_identity_mismatch', admin_id=None,
                                target_user='<img src=x onerror=alert(1)>@e.com',
                                ip_address='1.2.3.4'))
        db.session.commit()
    page = admin_client.get('/admin/logs').get_data(as_text=True)
    assert 'function esc(' in page
    for field in ['${esc(log.target_user', '${esc(log.details', '${esc(log.ip_address',
                  '${esc(log.admin_username']:
        assert field in page, field


def test_logs_date_filter_end_of_month(admin_client, app):
    """B2 回归：每月 28-31 日按日期筛选不得返回空"""
    from datetime import datetime
    with app.app_context():
        from models.models import db, AdminLog
        for day in (28, 30, 31):
            db.session.add(AdminLog(action='login', admin_id=None, target_user='t%d@x.com' % day,
                                    created_at=datetime(2026, 7, day, 12, 0, 0)))
        db.session.commit()
    for day in (28, 30, 31):
        d = admin_client.get('/admin/api/admin/logs?date=2026-07-%d' % day).get_json()
        assert d['success'] and any('t%d@x.com' % day in (l['target_user'] or '')
                                    for l in d['data']), day


def test_logs_username_search_matches_target_user(admin_client, app):
    d = admin_client.get('/admin/api/admin/logs?username=t30@x.com').get_json()
    assert d['success'] and len(d['data']) >= 1


def test_domain_edit_use_ssl_roundtrip(admin_client, app):
    """B1 回归：checkbox 勾选(on)/未勾选都必须正确保存"""
    with app.app_context():
        from models.models import db, Domain
        d = Domain(name='t.dom', ldap_hosts='192.168.1.1', ldap_host='192.168.1.1', ldap_port=389,
                   base_dn='DC=t,DC=dom', admin_dn='CN=a,CN=Users,DC=t,DC=dom')
        d.set_admin_password('pw123456')
        db.session.add(d)
        db.session.commit()
        did = d.id

    base = {'name': 't.dom', 'ldap_hosts': '192.168.1.1', 'ldap_host': '192.168.1.1',
            'ldap_port': '389', 'base_dn': 'DC=t,DC=dom',
            'admin_dn': 'CN=a,CN=Users,DC=t,DC=dom'}
    r = admin_client.post('/admin/domains/%d/edit' % did, data=dict(base, use_ssl='on'))
    assert r.status_code == 302
    with app.app_context():
        from models.models import Domain
        assert Domain.query.get(did).use_ssl is True
    r = admin_client.post('/admin/domains/%d/edit' % did, data=base)
    assert r.status_code == 302
    with app.app_context():
        from models.models import Domain
        assert Domain.query.get(did).use_ssl is False


def test_domain_ops_audited(admin_client, app):
    d = admin_client.get('/admin/api/admin/logs?action=domain_update').get_json()
    assert d['success']
    d = admin_client.get('/admin/api/admin/logs?action=security_whitelist_update').get_json()
    assert d['success']


def test_security_whitelist_flow(app):
    """访问控制：即时生效 + 防自锁 + 语法校验"""
    def mk(ip):
        c = app.test_client()
        with c.session_transaction() as s:
            s['user_id'] = 1
            s['user_role'] = 'admin'
            s['username'] = 'admin'
        return c, ip

    def get(c, ip, url):
        return c.get(url, environ_base={'REMOTE_ADDR': ip})

    c, ip = mk('10.4.128.20')
    # 保存含当前 IP 的名单
    r = c.put('/admin/api/admin-allowed-ips', json={'ips': '10.4.0.0/16'},
              environ_base={'REMOTE_ADDR': ip})
    assert r.status_code == 200 and r.get_json()['success']
    # 名单外 IP 被 403（login + admin），/reset 不受限
    c2, ip2 = mk('203.0.113.9')
    assert get(c2, ip2, '/admin/dashboard').status_code == 403
    assert get(c2, ip2, '/login').status_code == 403
    assert get(c2, ip2, '/reset').status_code == 200
    assert get(c, ip, '/admin/dashboard').status_code == 200
    # 防自锁：不含当前 IP 的名单被拒绝
    r = c.put('/admin/api/admin-allowed-ips', json={'ips': '192.168.50.0/24'},
              environ_base={'REMOTE_ADDR': ip})
    assert r.status_code == 400 and ip in r.get_json()['message']
    # 语法校验
    r = c.put('/admin/api/admin-allowed-ips', json={'ips': 'bad-ip'},
              environ_base={'REMOTE_ADDR': ip})
    assert r.status_code == 400
    # 清空恢复
    r = c.put('/admin/api/admin-allowed-ips', json={'ips': ''},
              environ_base={'REMOTE_ADDR': ip})
    assert r.status_code == 200
    assert get(c2, ip2, '/admin/dashboard').status_code == 200


def test_dashboard_ops_stats(admin_client, app):
    from datetime import datetime
    with app.app_context():
        from models.models import db, AdminLog
        db.session.add(AdminLog(action='password_reset', admin_id=None,
                                target_user='x@y.com', created_at=datetime.now()))
        db.session.commit()
    d = admin_client.get('/admin/api/admin/dashboard/stats').get_json()
    assert d['success'] and d['data']['todayResets'] >= 1
    assert 'smsConfigured' in d['data']
    page = admin_client.get('/admin/dashboard').get_data(as_text=True)
    assert '今日重置成功' in page and 'todayResets' in page


def test_sqlite_wal_enabled(app):
    with app.app_context():
        from sqlalchemy import text
        from models.models import db
        mode = db.session.execute(text('PRAGMA journal_mode')).scalar()
        assert str(mode).lower() == 'wal', mode


def test_favicon_linked_and_served(admin_client, anon_client):
    """全部页面均声明锁形 favicon，图标文件可访问"""
    for c, url in ((anon_client, '/reset'), (anon_client, '/login'),
                   (admin_client, '/admin/dashboard'), (admin_client, '/admin/manual')):
        body = c.get(url).get_data(as_text=True)
        assert 'favicon.svg' in body and 'favicon.png' in body, url
    for f in ('favicon.svg', 'favicon.png', 'apple-touch-icon.png'):
        r = anon_client.get('/static/' + f)
        assert r.status_code == 200 and len(r.data) > 100, f
