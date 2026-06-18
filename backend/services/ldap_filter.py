"""LDAP 过滤器转义，防止 LDAP 注入。RFC4515 规则。"""


def escape_ldap(value):
    """对用户输入做 LDAP 过滤器转义。"""
    if value is None:
        return ''
    v = str(value)
    v = v.replace('\\', '\\5c')
    out = []
    for ch in v:
        if ch == '*':
            out.append('\\2a')
        elif ch == '(':
            out.append('\\28')
        elif ch == ')':
            out.append('\\29')
        elif ch == '\x00':
            out.append('\\00')
        else:
            out.append(ch)
    return ''.join(out)
