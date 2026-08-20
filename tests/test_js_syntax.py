"""JS 语法门禁：渲染全部页面，提取内联 <script> 用 node --check 校验。

背景：域配置页曾因模板字符串内漏写 }); 导致整个脚本块解析失败、
列表恒为空（数据无损）。此测试在 CI 阶段拦截同类回归。
无 node 环境时自动跳过（本机开发可 npm/node 安装）。
"""
import os
import re
import shutil
import subprocess

import pytest

NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(NODE is None, reason='node 不可用，跳过 JS 语法门禁')

SCRIPT_RE = re.compile(r'<script(?![^>]*src=)[^>]*>(.*?)</script>', re.S)

PAGES = [
    ('dashboard', '/admin/dashboard'),
    ('domains', '/admin/domains'),
    ('sms', '/admin/sms'),
    ('logs', '/admin/logs'),
    ('protected', '/admin/protected'),
    ('security', '/admin/security'),
    ('vault', '/admin/vault'),
    ('change_password', '/admin/change-password'),
    ('manual', '/admin/manual'),
    ('login', '/login'),
    ('reset', '/reset'),
]


def test_all_inline_scripts_valid_syntax(admin_client, anon_client, tmp_path):
    checked = 0
    errors = []
    for name, url in PAGES:
        c = anon_client if url in ('/login', '/reset') else admin_client
        r = c.get(url)
        assert r.status_code == 200, (name, r.status_code)
        for i, js in enumerate(s for s in SCRIPT_RE.findall(r.get_data(as_text=True)) if s.strip()):
            f = tmp_path / ('%s_%d.js' % (name, i))
            f.write_text(js, encoding='utf-8')
            p = subprocess.run([NODE, '--check', str(f)], capture_output=True, text=True)
            checked += 1
            if p.returncode != 0:
                errors.append('%s#%d: %s' % (name, i, p.stderr.strip()[:300]))
    assert checked >= 10, '内联脚本数量异常偏少：%d' % checked
    assert not errors, '\n'.join(errors)
