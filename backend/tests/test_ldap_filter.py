from services.ldap_filter import escape_ldap


def test_escapes_special_chars():
    assert escape_ldap('user)(*))') == r'user\29\28\2a\29\29'
    assert escape_ldap('a\\b') == r'a\5cb'
    assert escape_ldap('normal') == 'normal'
    assert escape_ldap('a\x00b') == r'a\00b'


def test_handles_non_string():
    assert escape_ldap(123) == '123'
    assert escape_ldap(None) == ''
