"""查找字段回退：AD 用户属性经常漏填/填错位置——
手机号常被填进 telephoneNumber（办公室电话）而非 mobile；邮箱 mail 属性漏填但
userPrincipalName（登录名）已填。lookup_user_by_email 用 pick_phone/pick_email
做回退，否则这类用户自助重置会被误报"与域控不匹配/未找到用户"。"""


from services.ldap_service import pick_phone, pick_email


def test_pick_phone_prefers_mobile():
    assert pick_phone('13800138000', '0101234567') == '13800138000'


def test_pick_phone_falls_back_to_telephone():
    assert pick_phone('', '19912345678') == '19912345678'
    assert pick_phone(None, '19912345678') == '19912345678'


def test_pick_phone_strips_whitespace():
    assert pick_phone('  13800138000  ', '') == '13800138000'
    assert pick_phone(' ', ' 15712345678 ') == '15712345678'


def test_pick_phone_both_empty():
    assert pick_phone('', '') == ''
    assert pick_phone(None, None) == ''


def test_lookup_attrs_include_telephone_number():
    """查询属性必须包含 telephoneNumber，否则回退永远取不到值。"""
    import inspect
    from services import ldap_service
    src = inspect.getsource(ldap_service.LdapService.lookup_user_by_email)
    assert 'telephoneNumber' in src


def test_pick_email_prefers_mail():
    assert pick_email('user@demo.com', 'upn@demo.com') == 'user@demo.com'


def test_pick_email_falls_back_to_upn():
    assert pick_email('', 'user@demo.com') == 'user@demo.com'
    assert pick_email(None, 'user@demo.com') == 'user@demo.com'


def test_pick_email_both_empty():
    assert pick_email('', '') == ''
    assert pick_email(None, None) == ''


def test_lookup_filter_includes_upn():
    """查找过滤器必须同时匹配 mail 和 userPrincipalName。"""
    import inspect
    from services import ldap_service
    src = inspect.getsource(ldap_service.LdapService.lookup_user_by_email)
    assert 'userPrincipalName' in src
