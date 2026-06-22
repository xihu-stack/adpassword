def test_protected_accounts_api(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['user_role'] = 'admin'
        sess['username'] = 'admin'
    r = client.get('/admin/api/reset-protected-accounts')
    data = r.get_json()
    assert data['success'] is True
    assert 'admin' in data['data']
    r = client.put('/admin/api/reset-protected-accounts',
                   json={'accounts': ['admin', 'CN=Domain Admins,DC=t,DC=com']})
    data = r.get_json()
    assert data['success'] is True
    assert len(data['data']) == 2
    # GET reflects the update
    r = client.get('/admin/api/reset-protected-accounts')
    assert 'CN=Domain Admins,DC=t,DC=com'.lower() in [x.lower() for x in r.get_json()['data']]
