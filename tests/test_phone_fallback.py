"""手机号字段回退：AD 里号码常被填进 telephoneNumber（办公室电话）而非 mobile。
lookup_user_by_email 的 mobile 取值用 pick_phone 做 mobile→telephoneNumber 回退，
否则这类用户自助重置会误报"手机号与域控不匹配"。"""


from services.ldap_service import pick_phone


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
