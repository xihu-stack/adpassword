from flask import Blueprint, request, jsonify, session, current_app, render_template_string
from services.ldap_service import LdapService
from utils.decorators import admin_required, login_required
from datetime import datetime

admin_bp = Blueprint('admin', __name__)


def _alert_back(message):
    """返回 alert+返回上一页 的响应；消息经 JSON 编码，防 JS/HTML 注入。"""
    import json
    safe = json.dumps(str(message), ensure_ascii=False).replace('<', '\\u003c')
    return '<script>alert(%s); window.history.back();</script>' % safe


def _domain_bind_password(domain):
    """取域控绑定密码。返回 (password, None) 或 (None, 错误消息)。
    解密失败（密钥变更/丢失）时给出明确指引，避免误判为密码错误。"""
    from services.ldap_service import secret_decrypt
    raw = domain.ldap_password or domain.admin_password
    if not raw:
        return None, '域控管理员密码未配置，请先在域配置中录入'
    try:
        return secret_decrypt(raw), None
    except RuntimeError as e:
        return None, str(e)


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """管理后台首页 - HTML 页面"""
    username = session.get('username', '管理员')
    
    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>管理后台 - 华深智药</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                background: #f5f7fa;
                min-height: 100vh;
            }
            .header {
                background: linear-gradient(135deg, #15376b 0%, #1f5fa8 100%);
                color: white;
                padding: 20px 40px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .header h1 { font-size: 24px; }
            .user-info {
                display: flex;
                align-items: center;
                gap: 15px;
            }
            .logout-btn {
                background: rgba(255,255,255,0.2);
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                text-decoration: none;
            }
            .logout-btn:hover { background: rgba(255,255,255,0.3); }
            .container { max-width: 1400px; margin: 0 auto; padding: 30px; }
            .welcome-card {
                background: white;
                border-radius: 10px;
                padding: 40px;
                margin-bottom: 30px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }
            .welcome-card h2 {
                color: #333;
                margin-bottom: 10px;
            }
            .welcome-card p {
                color: #666;
                line-height: 1.6;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }
            .stat-card {
                background: linear-gradient(135deg, #15376b 0%, #1f5fa8 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }
            .stat-card h3 {
                font-size: 36px;
                margin-bottom: 10px;
            }
            .stat-card p {
                font-size: 14px;
                opacity: 0.9;
            }
            .menu-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }
            .menu-item {
                background: white;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
                text-decoration: none;
                color: #333;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                transition: transform 0.2s;
            }
            .menu-item:hover {
                transform: translateY(-5px);
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            }
            .menu-icon {
                font-size: 48px;
                margin-bottom: 15px;
            }
            .menu-title {
                font-size: 16px;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
<script>const CSRF_TOKEN="{{ csrf_token() }}";(function(){var f=window.fetch;window.fetch=function(u,o){o=o||{};o.headers=o.headers||{};if(!o.headers['X-CSRFToken']){o.headers['X-CSRFToken']=CSRF_TOKEN;}return f(u,o);};})();</script>
        <div class="header">
            <div style="display:flex;align-items:center;gap:12px;">
                <img src="{{ url_for('static', filename='logo.png') }}" alt="华深智药" style="height:34px;filter:drop-shadow(0 1px 4px rgba(0,0,0,.25));">
                <h1>华深智药 · 管理后台</h1>
            </div>
            <div class="user-info">
                <span>欢迎，{{ username }}</span>
                <a href="/logout" class="logout-btn">退出登录</a>
            </div>
        </div>
        
        <div class="container">
            <div class="welcome-card">
                <h2>欢迎回来，{{ username }}！</h2>
                <p>这是 华深智药的管理后台。您可以在这里管理域配置、用户信息、短信设置等。</p>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3 id="domainCount">-</h3>
                        <p>域配置数量</p>
                    </div>
                    <div class="stat-card">
                        <h3 id="userCount">-</h3>
                        <p>用户总数</p>
                    </div>
                    <div class="stat-card">
                        <h3 id="activeUserCount">-</h3>
                        <p>活跃用户</p>
                    </div>
                    <div class="stat-card" style="background: linear-gradient(135deg, #67C23A 0%, #4CAF50 100%);">
                        <h3 id="systemStatus">正常</h3>
                        <p>系统状态</p>
                    </div>
                </div>
            </div>
            
            <h2 style="margin-bottom: 20px;">管理功能</h2>
            <div class="menu-grid">
                <a href="/admin/domains" class="menu-item">
                    <div class="menu-icon">🌐</div>
                    <div class="menu-title">域配置管理</div>
                </a>
                <a href="/admin/sms" class="menu-item">
                    <div class="menu-icon">💬</div>
                    <div class="menu-title">短信配置</div>
                </a>
                <a href="/admin/logs" class="menu-item">
                    <div class="menu-icon">📊</div>
                    <div class="menu-title">操作日志</div>
                </a>
                <a href="/admin/protected" class="menu-item">
                    <div class="menu-icon">🛡️</div>
                    <div class="menu-title">保护名单</div>
                </a>
                <a href="/admin/change-password" class="menu-item">
                    <div class="menu-icon">🔑</div>
                    <div class="menu-title">修改密码</div>
                </a>
                <a href="/reset" class="menu-item">
                    <div class="menu-icon">🏠</div>
                    <div class="menu-title">重置页</div>
                </a>
                <a href="/admin/manual" class="menu-item">
                    <div class="menu-icon">📖</div>
                    <div class="menu-title">运维手册</div>
                </a>
            </div>
        </div>
        
        <script>
            // 页面加载时加载统计数据
            document.addEventListener('DOMContentLoaded', function() {
                loadDashboardStats();
            });
            
            // 加载后台统计数据
            function loadDashboardStats() {
                fetch('/admin/api/admin/dashboard/stats')
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            document.getElementById('domainCount').textContent = data.data.domainCount || 0;
                            document.getElementById('userCount').textContent = data.data.userCount || 0;
                            document.getElementById('activeUserCount').textContent = data.data.activeUserCount || data.data.userCount || 0;
                            
                            // 系统状态判断
                            if (data.data.domainCount > 0 && data.data.userCount > 0) {
                                document.getElementById('systemStatus').textContent = '正常';
                                document.getElementById('systemStatus').parentElement.style.background = 'linear-gradient(135deg, #67C23A 0%, #4CAF50 100%)';
                            } else {
                                document.getElementById('systemStatus').textContent = '待配置';
                                document.getElementById('systemStatus').parentElement.style.background = 'linear-gradient(135deg, #E6A23C 0%, #F5A623 100%)';
                            }
                        }
                    })
                    .catch(err => {
                        console.error('加载统计数据失败:', err);
                        document.getElementById('systemStatus').textContent = '异常';
                        document.getElementById('systemStatus').parentElement.style.background = 'linear-gradient(135deg, #F56C6C 0%, #E74C3C 100%)';
                    });
            }
        </script>
    </body>
    </html>
    '''
    
    return render_template_string(html, username=username)


# ==================== 管理页面 API ====================
# 注意：这些 API 供前端 Vue 应用调用，返回 JSON 数据

@admin_bp.route('/api/admin/dashboard/stats')
@admin_required
def dashboard_stats():
    """管理后台统计数据"""
    from models.models import Domain, User
    
    try:
        domain_count = Domain.query.count()
        user_count = User.query.count()
        active_user_count = User.query.filter_by(is_active=True).count()
        
        return jsonify({
            'success': True,
            'data': {
                'domainCount': domain_count,
                'userCount': user_count,
                'activeUserCount': active_user_count,
            }
        })
    except Exception as e:
        print(f'[ERROR] 获取统计数据失败：{str(e)}')
        return jsonify({
            'success': False,
            'data': {
                'domainCount': 0,
                'userCount': 0,
                'activeUserCount': 0,
            }
        })


# ==================== 管理页面 HTML 路由（直接访问） ====================

@admin_bp.route('/domains')
@admin_required
def domains_page():
    """域配置管理页面"""
    username = session.get('username', '管理员')
    
    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>域配置管理 - 华深智药</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f5f7fa; }
            .header {
                background: linear-gradient(135deg, #15376b 0%, #1f5fa8 100%);
                color: white;
                padding: 20px 40px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header h1 { font-size: 24px; }
            .logout-btn {
                background: rgba(255,255,255,0.2);
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                text-decoration: none;
            }
            .container { max-width: 1400px; margin: 0 auto; padding: 30px; }
            .back-btn {
                display: inline-block;
                margin-bottom: 20px;
                padding: 10px 20px;
                background: white;
                color: #15376b;
                text-decoration: none;
                border-radius: 4px;
            }
            .card {
                background: white;
                border-radius: 10px;
                padding: 30px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }
            .empty-state {
                text-align: center;
                padding: 60px 20px;
                color: #999;
            }
            .empty-state-icon { font-size: 64px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
<script>const CSRF_TOKEN="{{ csrf_token() }}";(function(){var f=window.fetch;window.fetch=function(u,o){o=o||{};o.headers=o.headers||{};if(!o.headers['X-CSRFToken']){o.headers['X-CSRFToken']=CSRF_TOKEN;}return f(u,o);};})();</script>
        <div class="header">
            <h1>🌐 域配置管理</h1>
            <div>
                <span style="margin-right: 15px;">{{ username }}</span>
                <a href="/logout" class="logout-btn">退出登录</a>
            </div>
        </div>
        
        <div class="container">
            <a href="/admin/dashboard" class="back-btn">← 返回管理后台</a>
            
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 style="margin: 0; font-size: 18px;">域配置列表</h3>
                    <div style="display: flex; gap: 10px;">
                        <button onclick="showAddForm()" style="padding: 8px 16px; background: #409EFF; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block;">添加域配置</button>
                    </div>
                </div>
                
                <!-- 域配置列表 -->
                <div id="domainList" style="display: none;">
                    <div id="domainsContainer"></div>
                </div>
                
                <!-- 空状态 -->
                <div class="empty-state" style="padding: 40px 20px;">
                    <div class="empty-state-icon">🌐</div>
                    <h2>暂无域配置</h2>
                    <p>请点击上方按钮添加第一个域配置</p>
                </div>
                
                <!-- 添加域配置表单 -->
                <div id="addForm" style="display: none; margin-top: 30px;">
                    <h3 style="margin-bottom: 20px;">添加域配置</h3>
                    <form method="POST" action="/admin/domains" style="max-width: 600px;">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">域名（填这个就行，下面自动生成）</label>
                            <input type="text" name="name" id="domainName" oninput="autoFillDN()" placeholder="例如：helixon.com" required style="width: 100%; padding: 10px; border: 2px solid #409EFF; border-radius: 4px;">
                            <small style="color: #999; display: block; margin-top: 5px;">💡 填域名后，基础 DN 和管理员 DN 会自动生成，可手动修改</small>
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">LDAP 主机</label>
                            <input type="text" name="ldap_host" placeholder="例如：192.168.1.100 或 dc.helixon.com" required style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">LDAP 端口</label>
                            <input type="number" name="ldap_port" id="ldap_port" value="389" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                                    <div style="margin-top: 12px;">
                                        <label class="checkbox-label" style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                            <input type="checkbox" id="use_ssl" name="use_ssl" onchange="onSSLChanged()" style="width: 16px; height: 16px; cursor: pointer;">
                                            <span>🔒 启用 LDAPS (SSL 加密连接)</span>
                                        </label>
                                <small style="color: #999; display: block; margin-top: 5px;">启用后会自动切换到 LDAPS 端口（636），需要服务器支持 SSL。普通 LDAP 端口：389，LDAPS 端口：636</small>
                            </div>
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">管理员账号名（用于自动生成 DN）</label>
                            <input type="text" id="adminCN" value="Administrator" oninput="autoFillDN()" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                            <small style="color: #999;">默认 Administrator，可改成服务账号名</small>
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">基础 DN（自动生成）</label>
                            <input type="text" name="base_dn" id="base_dn" placeholder="填域名后自动生成" required style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; background: #f8f9fa;">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">管理员 DN（自动生成）</label>
                            <input type="text" name="admin_dn" id="admin_dn" placeholder="填域名后自动生成" required style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; background: #f8f9fa;">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">管理员密码</label>
                            <input type="password" name="admin_password" id="admin_password" placeholder="AD 管理员密码" required style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div style="margin-top: 20px;">
                            <button type="button" onclick="testConnection()" style="padding: 12px 24px; background: #E6A23C; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px;">🔗 测试连接</button>
                            <button type="submit" id="saveBtn" style="padding: 12px 24px; background: #67C23A; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px;" disabled>保存配置</button>
                            <button type="button" onclick="hideAddForm()" style="padding: 12px 24px; background: #909399; color: white; border: none; border-radius: 4px; cursor: pointer;">取消</button>
                        </div>
                        <div id="testResult" style="margin-top: 15px; padding: 10px; border-radius: 4px; display: none;"></div>
                    </form>
                </div>

                <div class="card" style="margin-top:20px">
                    <h3 style="margin-bottom:8px">🔍 员工域账号验证</h3>
                    <p style="color:#666;font-size:13px;margin-bottom:15px">输入员工邮箱和密码，验证域控连接和账号密码是否正确</p>
                    <input type="text" id="verifyEmail" placeholder="员工邮箱（如 zhangsan@helixon.com）" style="width:100%;padding:10px;border:1px solid #ddd;border-radius:6px;margin-bottom:10px">
                    <div style="display:flex;gap:10px">
                        <input type="password" id="verifyPassword" placeholder="员工密码" style="flex:1;padding:10px;border:1px solid #ddd;border-radius:6px">
                        <button type="button" onclick="verifyUser()" style="padding:10px 24px;background:#409EFF;color:#fff;border:none;border-radius:6px;cursor:pointer;white-space:nowrap">验证</button>
                    </div>
                    <div id="verifyResult" style="display:none;padding:12px;border-radius:6px;font-size:13px;word-break:break-all;margin-top:12px"></div>
                </div>
            </div>
        </div>

        <script>
            // 页面加载时获取域配置列表
            document.addEventListener('DOMContentLoaded', function() {
                loadDomainList();
            });
            
            // 填域名后自动生成 Base DN 和 Admin DN
            function autoFillDN() {
                var name = document.getElementById('domainName').value.trim();
                var cn = document.getElementById('adminCN').value.trim() || 'Administrator';
                var baseInput = document.getElementById('base_dn');
                var adminInput = document.getElementById('admin_dn');
                if (!name) { baseInput.value=''; adminInput.value=''; return; }
                var parts = name.split('.').filter(function(p){return p.trim();});
                var baseDN = parts.map(function(p){return 'DC=' + p.trim();}).join(',');
                baseInput.value = baseDN;
                adminInput.value = 'CN=' + cn + ',CN=Users,' + baseDN;
            }

            function showAddForm() {
                document.querySelector('.empty-state').style.display = 'none';
                document.getElementById('addForm').style.display = 'block';
            }
            
            function hideAddForm() {
                document.getElementById('addForm').style.display = 'none';
                document.querySelector('.empty-state').style.display = 'block';
            }

            // 员工域账号验证
            function verifyUser() {
                const email = document.getElementById('verifyEmail').value.trim();
                const password = document.getElementById('verifyPassword').value.trim();
                if (!email || !password) { alert('请输入邮箱和密码'); return; }
                const div = document.getElementById('verifyResult');
                div.style.display = 'block';
                div.style.background = '#f0f0f0';
                div.style.color = '#666';
                div.textContent = '⏳ 正在验证...';
                fetch('/admin/api/admin/domains/verify-user', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: email, password: password})
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        div.style.background = '#f0f9eb';
                        div.style.color = '#67C23A';
                    } else {
                        div.style.background = '#fef0f0';
                        div.style.color = '#f56c6c';
                    }
                    div.textContent = data.message;
                })
                .catch(err => {
                    div.style.background = '#fef0f0';
                    div.style.color = '#f56c6c';
                    div.textContent = '❌ 请求失败：' + err;
                });
            }
            
            // SSL 切换时自动更新端口
            function onSSLChanged() {
                const useSSL = document.getElementById('use_ssl').checked;
                const portInput = document.getElementById('ldap_port');
                
                if (useSSL) {
                    // 启用 LDAPS，切换到 636 端口
                    portInput.value = '636';
                } else {
                    // 禁用 LDAPS，切换到 389 端口
                    portInput.value = '389';
                }
            }
            
            // 加载域配置列表
            function loadDomainList() {
                fetch('/admin/api/admin/domains/list')
                    .then(response => response.json())
                    .then(data => {
                        if (data.success && data.data && data.data.length > 0) {
                            // 有域配置，显示列表
                            document.querySelector('.empty-state').style.display = 'none';
                            document.getElementById('domainList').style.display = 'block';
                            renderDomainList(data.data);
                        } else {
                            // 无域配置，显示空状态
                            document.querySelector('.empty-state').style.display = 'block';
                            document.getElementById('domainList').style.display = 'none';
                        }
                    })
                    .catch(error => {
                        console.error('加载域配置失败:', error);
                        document.querySelector('.empty-state').style.display = 'block';
                        document.getElementById('domainList').style.display = 'none';
                    });
            }
            
            // 渲染域配置列表（字段为管理员录入，渲染前统一转义）
            function esc(s){ return String(s == null ? '' : s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
            function renderDomainList(domains) {
                const container = document.getElementById('domainsContainer');
                let html = '';

                domains.forEach(domain => {
                    const isConnected = domain.is_connected || false;
                    const statusColor = isConnected ? '#67C23A' : '#F56C6C';
                    const statusText = isConnected ? '连接成功' : '连接失败';
                    const statusIcon = isConnected ? '✅' : '❌';

                    html += `
                    <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 15px; background: #fafafa;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px;">
                            <div style="display: flex; gap: 15px;">
                                <div style="font-size: 32px;">🌐</div>
                                <div>
                                    <h4 style="margin: 0 0 5px 0; color: #333; font-size: 16px;">${esc(domain.name)}</h4>
                                    <p style="margin: 0; color: #666; font-size: 14px;">${esc(domain.ldap_hosts || domain.ldap_host)}:${esc(domain.ldap_port)}</p>
                                </div>
                            </div>
                            <div style="display: flex; gap: 10px; align-items: center;">
                                <button onclick="editDomain(${domain.id})" style="padding: 6px 12px; background: #409EFF; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">编辑</button>
                                <span style="padding: 6px 12px; background: ${statusColor}; color: white; border-radius: 4px; font-size: 12px;">
                                    ${statusIcon} ${statusText}
                                </span>
                                <button onclick="testDomainConnection(${domain.id})" style="padding: 6px 12px; background: #E6A23C; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">🔗 测试连接</button>
                                <button onclick="deleteDomain(${domain.id})" style="padding: 6px 12px; background: #F56C6C; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">🗑️ 删除</button>
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; font-size: 14px; margin-top: 15px; padding-top: 15px; border-top: 1px solid #e0e0e0;">
                            <div>
                                <span style="color: #999;">基础 DN:</span>
                                <span style="color: #333; margin-left: 10px;">${esc(domain.base_dn)}</span>
                            </div>
                            <div>
                                <span style="color: #999;">管理员 DN:</span>
                                <span style="color: #333; margin-left: 10px;">${esc(domain.admin_dn || '-')}</span>
                            </div>
                            <div>
                                <span style="color: #999;">创建时间:</span>
                                <span style="color: #333; margin-left: 10px;">${esc(domain.created_at || '-')}</span>
                            </div>
                            <div>
                                <span style="color: #999;">状态:</span>
                                <span style="color: ${domain.is_active ? '#67C23A' : '#999'}; margin-left: 10px;">
                                    ${domain.is_active ? '✅ 启用' : '⚪ 禁用'}
                                </span>
                            </div>
                        </div>
                    </div>
                    `;
                });

                container.innerHTML = html;
            }
            
            // 测试单个域连接
            function testDomainConnection(domainId) {
                const testBtn = event.target;
                const originalText = testBtn.innerHTML;
                testBtn.innerHTML = '⏳ 测试中...';
                testBtn.disabled = true;
                
                fetch(`/admin/api/admin/domains/${domainId}/test`, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        testBtn.innerHTML = '✅ 成功';
                        testBtn.style.background = '#67C23A';
                        // 测试成功后，刷新整个列表以更新状态
                        setTimeout(() => {
                            location.reload(); // 刷新页面以显示最新状态
                        }, 1000);
                    } else {
                        testBtn.innerHTML = '❌ 失败';
                        testBtn.style.background = '#F56C6C';
                        alert('连接测试失败：' + data.message);
                    }
                })
                .catch(error => {
                    testBtn.innerHTML = '❌ 错误';
                    testBtn.style.background = '#F56C6C';
                    alert('测试出错：' + error);
                })
                .finally(() => {
                    setTimeout(() => {
                        testBtn.innerHTML = originalText;
                        testBtn.disabled = false;
                        testBtn.style.background = '#E6A23C';
                    }, 2000);
                });
            }
            
            // 删除域配置
            function deleteDomain(domainId) {
                if (!confirm('确定要删除此域配置吗？')) {
                    return;
                }
                
                fetch(`/admin/api/admin/domains/${domainId}`, {
                    method: 'DELETE'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('删除成功');
                        loadDomainList();
                    } else {
                        alert('删除失败：' + data.message);
                    }
                })
                .catch(error => {
                    alert('删除出错：' + error);
                });
            }
            
            // 编辑域配置
            function editDomain(domainId) {
                // 跳转到编辑页面
                window.location.href = `/admin/domains/${domainId}/edit`;
            }
            
            function testConnection() {
                const ldapHost = document.querySelector('input[name="ldap_host"]').value;
                const ldapPort = document.querySelector('input[name="ldap_port"]').value || 389;
                const baseDn = document.querySelector('input[name="base_dn"]').value;
                const adminDn = document.querySelector('input[name="admin_dn"]').value;
                const adminPassword = document.getElementById('admin_password').value;
                const useSSL = document.getElementById('use_ssl') ? document.getElementById('use_ssl').checked : false;
                
                if (!ldapHost || !baseDn || !adminDn || !adminPassword) {
                    alert('请先填写 LDAP 主机、基础 DN、管理员 DN 和管理员密码！');
                    return;
                }
                
                const testResultDiv = document.getElementById('testResult');
                testResultDiv.style.display = 'block';
                testResultDiv.style.background = '#f0f0f0';
                testResultDiv.innerHTML = '⏳ 正在测试连接...';
                
                fetch('/admin/domains/test-connection', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        ldap_host: ldapHost,
                        ldap_port: parseInt(ldapPort),
                        base_dn: baseDn,
                        admin_dn: adminDn,
                        admin_password: adminPassword,
                        use_ssl: useSSL
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        testResultDiv.style.background = '#d4edda';
                        testResultDiv.innerHTML = '✅ ' + data.message;
                        document.getElementById('saveBtn').disabled = false;
                    } else {
                        testResultDiv.style.background = '#f8d7da';
                        testResultDiv.innerHTML = '❌ 连接失败：' + data.message;
                        document.getElementById('saveBtn').disabled = true;
                    }
                })
                .catch(error => {
                    testResultDiv.style.background = '#f8d7da';
                    testResultDiv.innerHTML = '❌ 测试出错：' + error;
                    document.getElementById('saveBtn').disabled = true;
                });
            }
        </script>
    </body>
    </html>
    '''
    
    return render_template_string(html, username=username)


@admin_bp.route('/sms')
@admin_required
def sms_page():
    """短信配置页面"""
    username = session.get('username', '管理员')
    
    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>短信配置 - 华深智药</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f5f7fa; }
            .header {
                background: linear-gradient(135deg, #15376b 0%, #1f5fa8 100%);
                color: white;
                padding: 20px 40px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .container { max-width: 1000px; margin: 0 auto; padding: 30px; }
            .back-btn { display: inline-block; margin-bottom: 20px; padding: 10px 20px; background: white; color: #15376b; text-decoration: none; border-radius: 4px; }
            .card { background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
            .card-title { font-size: 20px; color: #333; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #eee; }
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 8px; color: #333; font-weight: 500; }
            .form-group input { width: 100%; padding: 12px 15px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
            .form-group input:focus { outline: none; border-color: #15376b; }
            .form-group small { display: block; margin-top: 5px; color: #999; font-size: 12px; }
            .btn { padding: 12px 30px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }
            .btn-primary { background: linear-gradient(135deg, #15376b 0%, #1f5fa8 100%); color: white; }
            .btn-primary:hover { opacity: 0.9; }
            .btn-test { background: #67C23A; color: white; margin-left: 10px; }
            .form-actions { margin-top: 30px; text-align: right; }
            .status-badge { display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 12px; margin-left: 10px; }
            .status-active { background: #67C23A; color: white; }
            .status-inactive { background: #909399; color: white; }
        </style>
    </head>
    <body>
<script>const CSRF_TOKEN="{{ csrf_token() }}";(function(){var f=window.fetch;window.fetch=function(u,o){o=o||{};o.headers=o.headers||{};if(!o.headers['X-CSRFToken']){o.headers['X-CSRFToken']=CSRF_TOKEN;}return f(u,o);};})();</script>
        <div class="header">
            <h1>💬 短信配置</h1>
            <div>
                <span style="margin-right: 15px;">{{ username }}</span>
                <a href="/logout" class="logout-btn">退出登录</a>
            </div>
        </div>
        
        <div class="container">
            <a href="/admin/dashboard" class="back-btn">← 返回管理后台</a>
            
            <div class="card">
                <h2 class="card-title">📱 阿里云短信服务配置</h2>
                
                <form id="smsConfigForm" onsubmit="saveSmsConfig(); return false;">
                    <div class="form-group">
                        <label for="accessKey">Access Key ID <span id="accessKeyStatus" class="status-badge status-inactive">未配置</span></label>
                        <input type="text" id="accessKey" name="access_key" required placeholder="请输入阿里云 AccessKey ID">
                        <small>阿里云账号的 AccessKey ID，用于身份认证</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="accessSecret">Access Key Secret <span id="accessSecretStatus" class="status-badge status-inactive">未配置</span></label>
                        <input type="password" id="accessSecret" name="access_secret" required placeholder="请输入阿里云 AccessKey Secret">
                        <small>阿里云账号的 AccessKey Secret，用于签名请求</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="signName">短信签名 <span id="signNameStatus" class="status-badge status-inactive">未配置</span></label>
                        <input type="text" id="signName" name="sign_name" required placeholder="请输入短信签名，如：华深智药">
                        <small>短信签名会显示在短信内容开头，需提前在阿里云控制台申请</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="templateCode">短信模板 CODE <span id="templateCodeStatus" class="status-badge status-inactive">未配置</span></label>
                        <input type="text" id="templateCode" name="template_code" required placeholder="请输入短信模板 CODE，如：SMS_123456789">
                        <small>短信模板 CODE，需在阿里云控制台申请验证码模板</small>
                    </div>
                    
                    <div class="form-group">
                        <label>测试手机号</label>
                        <div style="display: flex; gap: 10px;">
                            <input type="text" id="testPhone" placeholder="请输入测试手机号，用于发送测试短信" style="flex: 1;">
                            <button type="button" class="btn btn-test" onclick="sendTestSms()">发送测试</button>
                        </div>
                        <small>配置完成后，可发送测试短信验证配置是否正确</small>
                    </div>
                    
                    <div class="form-actions">
                        <button type="button" class="btn" onclick="loadSmsConfig()" style="margin-right: 10px;">加载配置</button>
                        <button type="submit" class="btn btn-primary">保存配置</button>
                    </div>
                </form>
            </div>
        </div>
        
        <script>
            // 页面加载时加载配置
            document.addEventListener('DOMContentLoaded', function() {
                loadSmsConfig();
            });
            
            // 加载短信配置
            function loadSmsConfig() {
                fetch('/admin/api/sms-config')
                    .then(r => r.json())
                    .then(data => {
                        if (data.success && data.data) {
                            document.getElementById('accessKey').value = data.data.access_key || '';
                            document.getElementById('accessSecret').value = '';
                            document.getElementById('signName').value = data.data.sign_name || '';
                            document.getElementById('templateCode').value = data.data.template_code || '';

                            // 更新状态徽章
                            updateStatus('accessKeyStatus', data.data.access_key);
                            // access_secret 不回传，用 access_secret_configured 判断
                            if (data.data.access_secret_configured) {
                                updateStatus('accessSecretStatus', 'configured');
                                document.getElementById('accessSecret').placeholder = '已配置（如需修改请输入新值）';
                            } else {
                                updateStatus('accessSecretStatus', '');
                            }
                            updateStatus('signNameStatus', data.data.sign_name);
                            updateStatus('templateCodeStatus', data.data.template_code);
                        }
                    })
                    .catch(err => console.error('加载配置失败:', err));
            }
            
            // 更新状态徽章
            function updateStatus(elementId, value) {
                const el = document.getElementById(elementId);
                if (value && value.trim()) {
                    el.textContent = '已配置';
                    el.className = 'status-badge status-active';
                } else {
                    el.textContent = '未配置';
                    el.className = 'status-badge status-inactive';
                }
            }
            
            // 保存短信配置
            function saveSmsConfig() {
                const formData = {
                    access_key: document.getElementById('accessKey').value.trim(),
                    access_secret: document.getElementById('accessSecret').value.trim(),
                    sign_name: document.getElementById('signName').value.trim(),
                    template_code: document.getElementById('templateCode').value.trim()
                };
                
                // 验证必填项（Secret 已配置时可留空，保持原值）
                if (!formData.access_key || !formData.sign_name || !formData.template_code) {
                    alert('请填写完整的配置信息！');
                    return;
                }
                
                fetch('/admin/api/sms-config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(formData)
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        alert('✅ 配置保存成功！');
                        loadSmsConfig();
                    } else {
                        alert('❌ ' + data.message);
                    }
                })
                .catch(err => alert('❌ 请求失败：' + err));
            }
            
            // 发送测试短信
            function sendTestSms() {
                const phone = document.getElementById('testPhone').value.trim();
                if (!phone) {
                    alert('请输入测试手机号！');
                    return;
                }
                
                if (!confirm('确定要发送测试短信到 ' + phone + ' 吗？\\n注意：发送测试短信会产生费用。')) {
                    return;
                }
                
                fetch('/admin/api/sms-test', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({phone: phone})
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        alert('✅ 测试短信已发送！\\n' + (data.message || ''));
                    } else {
                        alert('❌ 发送失败：' + data.message);
                    }
                })
                .catch(err => alert('❌ 请求失败：' + err));
            }
        </script>
    </body>
    </html>
    '''
    
    return render_template_string(html, username=username)


@admin_bp.route('/logs')
@admin_required
def logs_page():
    """操作日志页面"""
    username = session.get('username', '管理员')
    
    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>操作日志 - 华深智药</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f5f7fa; }
            .header {
                background: linear-gradient(135deg, #15376b 0%, #1f5fa8 100%);
                color: white;
                padding: 20px 40px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .container { max-width: 1400px; margin: 0 auto; padding: 30px; }
            .back-btn { display: inline-block; margin-bottom: 20px; padding: 10px 20px; background: white; color: #15376b; text-decoration: none; border-radius: 4px; }
            .card { background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
            .card-title { font-size: 20px; color: #333; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
            .table-container { overflow-x: auto; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
            th { background: #f8f9fa; color: #333; font-weight: 600; }
            tr:hover { background: #f8f9fa; }
            .badge { display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 12px; }
            .badge-login { background: #e6f7ff; color: #1890ff; }
            .badge-password { background: #fff7e6; color: #fa8c16; }
            .badge-user { background: #f6ffed; color: #52c41a; }
            .badge-system { background: #f0f5ff; color: #2f54eb; }
            .badge-danger { background: #fff1f0; color: #f5222d; }
            .pagination { display: flex; justify-content: center; gap: 8px; margin-top: 20px; }
            .pagination button { padding: 8px 15px; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer; }
            .pagination button.active { background: #15376b; color: white; border-color: #15376b; }
            .pagination button:disabled { background: #f5f5f5; cursor: not-allowed; }
            .filter-form { display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }
            .filter-form select, .filter-form input { padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; }
            .btn { padding: 8px 15px; border: none; border-radius: 4px; cursor: pointer; }
            .btn-primary { background: #15376b; color: white; }
            .empty-state { text-align: center; padding: 60px 20px; color: #999; }
            .empty-state-icon { font-size: 64px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
<script>const CSRF_TOKEN="{{ csrf_token() }}";(function(){var f=window.fetch;window.fetch=function(u,o){o=o||{};o.headers=o.headers||{};if(!o.headers['X-CSRFToken']){o.headers['X-CSRFToken']=CSRF_TOKEN;}return f(u,o);};})();</script>
        <div class="header">
            <h1>📊 操作日志</h1>
            <div>
                <span style="margin-right: 15px;">{{ username }}</span>
                <a href="/logout" class="logout-btn">退出登录</a>
            </div>
        </div>
        
        <div class="container">
            <a href="/admin/dashboard" class="back-btn">← 返回管理后台</a>
            
            <div class="card">
                <h2 class="card-title">
                    <span>管理员操作记录</span>
                    <button class="btn btn-primary" onclick="loadLogs(1); return false;">🔄 刷新</button>
                </h2>
                
                <div class="filter-form">
                    <select id="filterAction" onchange="loadLogs(1)">
                        <option value="">全部操作类型</option>
                        <option value="login">登录成功</option>
                        <option value="login_failed">登录失败</option>
                        <option value="password_reset">重置成功</option>
                        <option value="password_reset_failed">重置失败</option>
                        <option value="reset_identity_ok">身份校验通过</option>
                        <option value="reset_identity_mismatch">身份校验未通过</option>
                        <option value="reset_code_failed">验证码错误</option>
                        <option value="sms_send_failed">短信发送失败</option>
                        <option value="admin_password_change">管理员改密</option>
                        <option value="protected_list_update">保护名单更新</option>
                        <option value="domain_create">域创建</option>
                        <option value="domain_update">域更新</option>
                        <option value="domain_delete">域删除</option>
                        <option value="sms_config">短信配置</option>
                    </select>
                    <input type="text" id="filterUser" placeholder="搜索用户名" onkeydown="if(event.keyCode===13) loadLogs(1)">
                    <input type="date" id="filterDate">
                    <button class="btn btn-primary" onclick="loadLogs(1)">查询</button>
                </div>
                
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>时间</th>
                                <th>管理员</th>
                                <th>操作类型</th>
                                <th>目标用户</th>
                                <th>详情</th>
                                <th>IP 地址</th>
                            </tr>
                        </thead>
                        <tbody id="logsTableBody">
                            <tr>
                                <td colspan="6" style="text-align:center; padding: 40px; color: #999;">加载中...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                <div class="pagination" id="pagination"></div>
            </div>
        </div>
        
        <script>
            let currentPage = 1;
            let totalPages = 1;
            
            // 页面加载时加载日志
            document.addEventListener('DOMContentLoaded', function() {
                console.log('[日志页面] 页面加载完成，开始加载日志...');
                loadLogs(1);
            });
            
            // 加载日志
            window.loadLogs = function(page = 1) {
                console.log(`[日志页面] 加载第 ${page} 页日志...`);
                currentPage = page;
                
                const filterAction = document.getElementById('filterAction');
                const filterUser = document.getElementById('filterUser');
                const filterDate = document.getElementById('filterDate');
                
                if (!filterAction || !filterUser || !filterDate) {
                    console.error('[日志页面] 找不到筛选元素');
                    return;
                }
                
                const filters = {
                    action: filterAction.value || '',
                    username: filterUser.value || '',
                    date: filterDate.value || ''
                };
                
                console.log('[日志页面] 筛选条件:', filters);
                
                const params = new URLSearchParams({
                    page: page.toString(),
                    ...filters
                });
                
                const url = '/admin/api/admin/logs?' + params.toString();
                console.log('[日志页面] 请求 URL:', url);
                
                fetch(url)
                    .then(r => {
                        console.log('[日志页面] 响应状态:', r.status);
                        return r.json();
                    })
                    .then(data => {
                        console.log('[日志页面] 响应数据:', data);
                        if (data.success) {
                            renderLogs(data.data, data.total, data.pages, page);
                        } else {
                            document.getElementById('logsTableBody').innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 40px; color: #f5222d;">加载失败：' + data.message + '</td></tr>';
                        }
                    })
                    .catch(err => {
                        console.error('[日志页面] 加载错误:', err);
                        document.getElementById('logsTableBody').innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 40px; color: #f5222d;">加载失败，请查看浏览器控制台</td></tr>';
                    });
            };
            
            // 渲染日志表格
            // 安全：target_user/details 来自不可信输入（公开重置页的邮箱等），
            // innerHTML 渲染前必须转义，否则构成存储型 XSS
            function esc(s){ return String(s == null ? '' : s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
            function renderLogs(logs, total, pages, page) {
                const tbody = document.getElementById('logsTableBody');

                if (!logs || logs.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 40px; color: #999;">暂无日志记录</td></tr>';
                } else {
                    let html = '';
                    logs.forEach(log => {
                        const badgeClass = getBadgeClass(log.action);
                        const time = new Date(log.created_at).toLocaleString('zh-CN');
                        html += `
                            <tr>
                                <td>${esc(time)}</td>
                                <td>${esc(log.admin_username || '-')}</td>
                                <td><span class="badge ${badgeClass}">${esc(formatAction(log.action))}</span></td>
                                <td>${esc(log.target_user || '-')}</td>
                                <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${esc(log.details || '-')}</td>
                                <td>${esc(log.ip_address || '-')}</td>
                            </tr>
                        `;
                    });
                    tbody.innerHTML = html;
                }
                
                // 渲染分页
                renderPagination(pages, page);
            }
            
            // 获取徽章样式
            function getBadgeClass(action) {
                const classes = {
                    'login': 'badge-login',
                    'login_failed': 'badge-danger',
                    'password_reset': 'badge-password',
                    'password_reset_failed': 'badge-danger',
                    'reset_identity_ok': 'badge-login',
                    'reset_identity_mismatch': 'badge-danger',
                    'reset_code_failed': 'badge-danger',
                    'sms_send_failed': 'badge-danger',
                    'admin_password_change': 'badge-password',
                    'user_sync': 'badge-system',
                    'user_create': 'badge-user',
                    'user_update': 'badge-user',
                    'user_delete': 'badge-danger',
                    'domain_create': 'badge-system',
                    'domain_update': 'badge-system',
                    'domain_delete': 'badge-danger',
                    'sms_config': 'badge-system',
                    'protected_list_update': 'badge-system'
                };
                return classes[action] || 'badge-system';
            }

            // 格式化操作类型
            function formatAction(action) {
                const names = {
                    'login': '登录成功',
                    'login_failed': '登录失败',
                    'password_reset': '重置成功',
                    'password_reset_failed': '重置失败',
                    'reset_identity_ok': '身份校验通过',
                    'reset_identity_mismatch': '身份校验未通过',
                    'reset_code_failed': '验证码错误',
                    'sms_send_failed': '短信发送失败',
                    'admin_password_change': '管理员改密',
                    'user_sync': '用户同步',
                    'user_create': '用户创建',
                    'user_update': '用户更新',
                    'user_delete': '用户删除',
                    'domain_create': '域创建',
                    'domain_update': '域更新',
                    'domain_delete': '域删除',
                    'sms_config': '短信配置',
                    'protected_list_update': '保护名单更新'
                };
                return names[action] || action;
            }
            
            // 渲染分页
            function renderPagination(totalPages, currentPage) {
                const pagination = document.getElementById('pagination');
                if (totalPages <= 1) {
                    pagination.innerHTML = '';
                    return;
                }
                
                let html = '';
                
                // 上一页
                html += `<button ${currentPage === 1 ? 'disabled' : ''} onclick="loadLogs(${currentPage - 1})">上一页</button>`;
                
                // 页码
                for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
                    html += `<button class="${i === currentPage ? 'active' : ''}" onclick="loadLogs(${i})">${i}</button>`;
                }
                
                // 下一页
                html += `<button ${currentPage === totalPages ? 'disabled' : ''} onclick="loadLogs(${currentPage + 1})">下一页</button>`;
                
                pagination.innerHTML = html;
            }
        </script>
    </body>
    </html>
    '''
    
    return render_template_string(html, username=username)



@admin_bp.route('/domains/<int:domain_id>/edit')
@admin_required
def edit_domain_page(domain_id):
    """编辑域配置页面"""
    from models.models import Domain
    
    domain = Domain.query.get_or_404(domain_id)
    username = session.get('username', '管理员')
    
    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>编辑域配置 - 华深智药</title>
        <style>
            body {
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                background: #f5f7fa;
                margin: 0;
                padding: 0;
            }
            .header {
                background: linear-gradient(135deg, #15376b 0%, #1f5fa8 100%);
                color: white;
                padding: 20px 40px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header h1 {
                margin: 0;
                font-size: 24px;
            }
            .logout-btn {
                color: white;
                text-decoration: none;
                padding: 8px 16px;
                border-radius: 4px;
                background: rgba(255,255,255,0.2);
                transition: background 0.3s;
            }
            .logout-btn:hover {
                background: rgba(255,255,255,0.3);
            }
            .container {
                max-width: 1200px;
                margin: 20px auto;
                padding: 0 40px;
            }
            .back-btn {
                display: inline-block;
                padding: 10px 20px;
                background: #15376b;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                margin-bottom: 20px;
                transition: background 0.3s;
            }
            .back-btn:hover {
                background: #5568d3;
            }
            .card {
                background: white;
                border-radius: 8px;
                padding: 30px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.1);
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 8px;
                font-weight: bold;
                color: #333;
            }
            .form-group input {
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
                box-sizing: border-box;
            }
            /* Checkbox group styling */
            .checkbox-group {
                display: flex;
                flex-direction: column;
                gap: 8px;
                padding: 12px 16px;
                background: #f8f9fa;
                border-radius: 8px;
                border: 1px solid #e8ecef;
            }
            .checkbox-label {
                display: flex;
                align-items: center;
                gap: 10px;
                cursor: pointer;
                font-weight: 500;
                color: #333;
            }
            .checkbox-label input[type="checkbox"] {
                width: auto;
                cursor: pointer;
                accent-color: #15376b;
            }
            .checkbox-description {
                color: #666;
                font-size: 13px;
                margin-left: 28px;
                line-height: 1.5;
            }
            .form-group input:focus {
                outline: none;
                border-color: #15376b;
            }
            .form-actions {
                margin-top: 30px;
                display: flex;
                gap: 10px;
            }
            .btn {
                padding: 12px 24px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.3s;
            }
            .btn-primary {
                background: #67C23A;
                color: white;
            }
            .btn-primary:hover {
                background: #55a832;
            }
            .btn-secondary {
                background: #909399;
                color: white;
            }
            .btn-secondary:hover {
                background: #7d8085;
            }
            .test-btn {
                background: #E6A23C;
                color: white;
            }
            .test-btn:hover {
                background: #d9962e;
            }
            .test-result {
                margin-top: 15px;
                padding: 10px;
                border-radius: 4px;
                display: none;
            }
            .connection-status {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 10px 15px;
                border-radius: 4px;
                margin-bottom: 15px;
                font-size: 14px;
            }
            .connection-status.success {
                background: #d4edda;
                border: 1px solid #c3e6cb;
                color: #155724;
            }
            .connection-status.error {
                background: #f8d7da;
                border: 1px solid #f5c6cb;
                color: #721c24;
            }
            .connection-status.warning {
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                color: #856404;
            }
            .status-icon {
                font-size: 16px;
            }
            .btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            .btn-primary:disabled {
                background: #a0cfff;
            }
        </style>
    </head>
    <body>
<script>const CSRF_TOKEN="{{ csrf_token() }}";(function(){var f=window.fetch;window.fetch=function(u,o){o=o||{};o.headers=o.headers||{};if(!o.headers['X-CSRFToken']){o.headers['X-CSRFToken']=CSRF_TOKEN;}return f(u,o);};})();</script>
        <div class="header">
            <h1>✏️ 编辑域配置</h1>
            <div>
                <span>{{ username }}</span>
                <a href="/logout" class="logout-btn" style="margin-left: 15px;">退出登录</a>
            </div>
        </div>
        
        <div class="container">
            <a href="/admin/domains" class="back-btn">← 返回域配置列表</a>
            
            <div class="card">
                <h2 style="margin-top: 0; color: #333;">编辑域配置：{{ domain.name }}</h2>
                
                <!-- 连接状态提示 -->
                <div id="connectionStatus" class="connection-status warning" style="display: none;">
                    <span class="status-icon">⚠️</span>
                    <span id="connectionStatusText">连接状态未知，请先测试连接</span>
                </div>
                
                <form method="POST" action="/admin/domains/{{ domain.id }}/edit" id="editForm">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <input type="hidden" name="domain_id" value="{{ domain.id }}">
                    
                    <div class="form-group">
                        <label>域名称</label>
                        <input type="text" name="name" value="{{ domain.name }}" required>
                    </div>
                    
                    <div class="form-group">
                        <label>LDAP 主机</label>
                        <input type="text" name="ldap_host" id="ldap_host" value="{{ domain.ldap_host }}" required onchange="onFieldChanged()">
                    </div>
                    
                    <div class="form-group">
                        <label style="margin-bottom: 10px;">LDAP 端口设置</label>
                        <div class="checkbox-group">
                            <label class="checkbox-label">
                                <input type="checkbox" name="use_ssl" id="use_ssl" onchange="onSSLChanged()" {% if domain.use_ssl %}checked{% endif %}>
                                <span>🔒 启用 LDAPS (SSL 加密连接)</span>
                            </label>
                            <small class="checkbox-description">启用后会自动切换到 LDAPS 端口（636），需要服务器支持 SSL。普通 LDAP 端口：389，LDAPS 端口：636</small>
                        </div>
                        <input type="number" name="ldap_port" id="ldap_port" value="{{ domain.ldap_port }}" onchange="onFieldChanged()" style="margin-top: 12px;">
                    </div>
                    
                    <div class="form-group">
                        <label>基础 DN</label>
                        <input type="text" name="base_dn" value="{{ domain.base_dn }}" required onchange="onFieldChanged()">
                    </div>
                    
                    <div class="form-group">
                        <label>管理员 DN</label>
                        <input type="text" name="admin_dn" id="admin_dn" value="{{ domain.admin_dn }}" required onchange="onFieldChanged()">
                        <small style="color: #999;">格式示例：CN=Administrator,CN=Users,DC=helixon,DC=com 或 CN=Administrator,CN=huashen,DC=helixon,DC=com</small>
                    </div>
                    
                    <div class="form-group">
                        <label>管理员密码（留空则不修改）</label>
                        <input type="password" name="admin_password" id="admin_password" placeholder="请输入 LDAP 管理员明文密码">
                        <small style="color: #999;">用于连接 LDAP 服务器的明文密码，不会明文保存</small>
                    </div>
                    
                    <div class="form-actions">
                        <button type="button" class="btn test-btn" id="testBtn" onclick="testConnection()">🔗 测试连接</button>
                        <button type="submit" class="btn btn-primary" id="saveBtn" disabled title="请先测试连接，成功后才能保存">💾 保存修改</button>
                        <button type="button" class="btn btn-secondary" onclick="window.location.href='/admin/domains'">取消</button>
                    </div>
                    
                    <div id="testResult" class="test-result"></div>
                </form>
            </div>
        </div>
        
        <script>
            let connectionTested = false;
            
            // 页面加载时自动测试一次
            document.addEventListener('DOMContentLoaded', function() {
                // 延迟 1 秒后自动测试
                setTimeout(() => {
                    testConnection();
                }, 1000);
            });
            
            // 字段变更时重置状态
            function onFieldChanged() {
                connectionTested = false;
                updateConnectionStatus('warning', '⚠️', '配置已修改，请重新测试连接');
                document.getElementById('saveBtn').disabled = true;
            }
            
            // SSL 切换时自动更新端口
            function onSSLChanged() {
                const useSSL = document.getElementById('use_ssl').checked;
                const portInput = document.getElementById('ldap_port');
                
                if (useSSL) {
                    // 启用 LDAPS，切换到 636 端口
                    portInput.value = '636';
                } else {
                    // 禁用 LDAPS，切换到 389 端口
                    portInput.value = '389';
                }
                
                onFieldChanged();
            }
            
            // 更新连接状态显示
            function updateConnectionStatus(status, icon, text) {
                const statusDiv = document.getElementById('connectionStatus');
                const statusText = document.getElementById('connectionStatusText');
                
                statusDiv.className = 'connection-status ' + status;
                statusDiv.querySelector('.status-icon').textContent = icon;
                statusText.textContent = text;
                statusDiv.style.display = 'flex';
            }
            
            function testConnection() {
                const ldapHost = document.getElementById('ldap_host').value;
                const ldapPort = document.getElementById('ldap_port').value || 389;
                const baseDn = document.querySelector('input[name="base_dn"]').value;
                const adminDn = document.getElementById('admin_dn').value;
                const adminPassword = document.getElementById('admin_password').value;
                const useSSL = document.getElementById('use_ssl').checked;
                
                if (!ldapHost || !baseDn || !adminDn) {
                    alert('请先填写 LDAP 主机、基础 DN 和管理员 DN！');
                    return;
                }
                
                const testBtn = document.getElementById('testBtn');
                const saveBtn = document.getElementById('saveBtn');
                const testResultDiv = document.getElementById('testResult');
                
                // 禁用按钮，显示加载中
                testBtn.disabled = true;
                testBtn.innerHTML = '⏳ 测试中...';
                testResultDiv.style.display = 'block';
                testResultDiv.style.background = '#f0f0f0';
                testResultDiv.innerHTML = '⏳ 正在测试连接...';
                
                fetch('/admin/domains/test-connection', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        ldap_host: ldapHost,
                        ldap_port: parseInt(ldapPort),
                        base_dn: baseDn,
                        admin_dn: adminDn,
                        admin_password: adminPassword,
                        use_ssl: useSSL
                    })
                })
                .then(response => response.json())
                .then(data => {
                    testBtn.disabled = false;
                    testBtn.innerHTML = '🔗 测试连接';
                    
                    if (data.success) {
                        testResultDiv.style.background = '#d4edda';
                        testResultDiv.innerHTML = '✅ ' + data.message;
                        
                        // 连接成功：启用保存按钮
                        connectionTested = true;
                        saveBtn.disabled = false;
                        saveBtn.title = '连接测试成功，可以保存配置';
                        updateConnectionStatus('success', '✅', 'LDAP 连接测试成功！可以保存配置');
                    } else {
                        testResultDiv.style.background = '#f8d7da';
                        testResultDiv.innerHTML = '❌ 连接失败：' + data.message;
                        
                        // 连接失败：禁用保存按钮
                        connectionTested = false;
                        saveBtn.disabled = true;
                        saveBtn.title = 'LDAP 连接失败，无法保存配置';
                        updateConnectionStatus('error', '❌', 'LDAP 连接失败，请检查配置后重试');
                    }
                })
                .catch(error => {
                    testBtn.disabled = false;
                    testBtn.innerHTML = '🔗 测试连接';
                    
                    testResultDiv.style.background = '#f8d7da';
                    testResultDiv.innerHTML = '❌ 测试出错：' + error;
                    
                    // 测试出错：禁用保存按钮
                    connectionTested = false;
                    saveBtn.disabled = true;
                    saveBtn.title = '测试出错，无法保存配置';
                    updateConnectionStatus('error', '❌', '测试连接时出错，请检查网络或服务器配置');
                });
            }
            
            // 阻止未测试连接的表单提交
            document.getElementById('editForm').addEventListener('submit', function(e) {
                if (!connectionTested) {
                    e.preventDefault();
                    alert('请先测试 LDAP 连接，成功后才能保存配置！');
                    testConnection();
                }
            });
        </script>
    </body>
    </html>
    '''
    
    return render_template_string(html, username=username, domain=domain)


@admin_bp.route('/domains/<int:domain_id>/edit', methods=['POST'])
@admin_required
def update_domain_page(domain_id):
    """更新域配置 - HTML 表单提交"""
    from models.models import Domain, db
    import bcrypt
    
    try:
        domain = Domain.query.get_or_404(domain_id)
        
        # 获取表单数据
        name = request.form.get('name')
        ldap_hosts = request.form.get('ldap_hosts')  # 多主机支持
        ldap_host = request.form.get('ldap_host')  # 兼容旧字段
        ldap_port = request.form.get('ldap_port', 389, type=int)
        base_dn = request.form.get('base_dn')
        admin_dn = request.form.get('admin_dn')
        admin_password = request.form.get('admin_password')  # LDAP 密码
        # checkbox 勾选时提交 "on"、未勾选不提交——必须用 bool() 判断
        use_ssl = bool(request.form.get('use_ssl'))
        
        # 优先使用 ldap_hosts，如果没有则使用 ldap_host
        if not ldap_hosts:
            ldap_hosts = ldap_host
        
        # 验证必填字段
        if not all([name, ldap_hosts, base_dn, admin_dn]):
            return _alert_back('请填写所有必填字段！')

        # 更新域配置
        domain.name = name
        domain.ldap_hosts = ldap_hosts  # 新字段：多主机
        domain.ldap_host = ldap_host  # 保留旧字段以兼容
        domain.ldap_port = ldap_port
        domain.base_dn = base_dn
        domain.admin_dn = admin_dn
        domain.use_ssl = use_ssl

        # 如果提供了 LDAP 密码，则更新（加密存储）
        if admin_password:
            domain.set_ldap_password(admin_password)
            domain.set_admin_password(admin_password)

        # 如果没有密码但数据库中有，则保留原密码
        if not admin_password and domain.ldap_password:
            pass  # 保持原密码不变
        elif not admin_password and not domain.ldap_password:
            # 都没有，报错
            return _alert_back('首次配置必须输入 LDAP 管理员密码！')

        # 保存到数据库
        db.session.commit()

        # 审计（不记录密码）
        from utils.logger import log_operation
        log_operation('domain_update', target_user=name,
                      details='更新域配置：%s（%s，SSL=%s）' % (name, ldap_hosts, use_ssl))

        # 重定向到域列表页面
        from flask import redirect, url_for
        return redirect(url_for('admin.domains_page'))

    except Exception as e:
        db.session.rollback()
        return _alert_back('保存失败：%s' % e)


# ==================== API 路由 ====================
@admin_bp.route('/api/admin/domains/list', methods=['GET'])
@admin_required
def get_domains_list():
    """获取域配置列表 - API"""
    from models.models import Domain
    
    try:
        domains = Domain.query.all()
        domain_list = [{
            'id': d.id,
            'name': d.name,
            'ldap_hosts': d.ldap_hosts if hasattr(d, 'ldap_hosts') else d.ldap_host,
            'ldap_host': d.ldap_host,
            'ldap_port': d.ldap_port,
            'ldaps_port': d.ldaps_port if hasattr(d, 'ldaps_port') else 636,
            'base_dn': d.base_dn,
            'admin_dn': d.admin_dn,
            'use_ssl': d.use_ssl if hasattr(d, 'use_ssl') else False,
            'is_active': d.is_active,
            'is_connected': d.is_connected,
            'created_at': d.created_at.strftime('%Y-%m-%d %H:%M:%S') if d.created_at else '-',
        } for d in domains]
        
        return jsonify({
            'success': True,
            'data': domain_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'data': []
        })


@admin_bp.route('/api/admin/domains/<int:domain_id>/test', methods=['POST'])
@admin_required
def test_domain_connection(domain_id):
    """测试域配置连接 - 使用数据库中的配置"""
    from models.models import Domain, db
    
    try:
        domain = Domain.query.get(domain_id)
        if not domain:
            return jsonify({
                'success': False,
                'message': '域配置不存在'
            }), 404
        
        # 使用 LDAP 服务测试连接
        from services.ldap_service import LdapService

        bind_pwd, pwd_err = _domain_bind_password(domain)
        if pwd_err:
            return jsonify({'success': False, 'message': pwd_err}), 200

        # 测试连接（传入字典参数）
        result, message = LdapService.test_connection({
            'ldap_hosts': domain.ldap_hosts,
            'ldap_host': domain.ldap_host,
            'ldap_port': domain.ldap_port,
            'ldaps_port': domain.ldaps_port,
            'base_dn': domain.base_dn,
            'admin_dn': domain.admin_dn,
            'admin_password': bind_pwd,
            'use_ssl': domain.use_ssl
        })
        
        if result:
            # 更新数据库中的连接状态
            domain.is_connected = True
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            # 更新连接状态为失败
            domain.is_connected = False
            db.session.commit()
            
            return jsonify({
                'success': False,
                'message': message
            }), 200
            
    except Exception as e:
        db.session.rollback()
        # 更新连接状态为失败
        if domain:
            domain.is_connected = False
            db.session.commit()
        
        return jsonify({
            'success': False,
            'message': f'测试失败：{str(e)}'
        }), 200


@admin_bp.route('/api/admin/domains/<int:domain_id>/diagnose', methods=['POST'])
@admin_required
def diagnose_domain_connection(domain_id):
    """诊断域连接问题 - 智能分析 LDAP/LDAPS 切换问题"""
    from models.models import Domain, db
    
    try:
        domain = Domain.query.get(domain_id)
        if not domain:
            return jsonify({
                'success': False,
                'message': '域配置不存在'
            }), 404
        
        # 导入诊断工具
        from services.ldap_service import build_tls_context
        from ldap3 import Server, Connection, SIMPLE, ALL

        diagnosis_result = {
            'success': False,
            'ldap_port_status': False,
            'ldaps_port_status': False,
            'ldap_connection': False,
            'ldaps_connection': False,
            'issues': [],
            'suggestions': []
        }

        # 凭据解密失败时直接给出明确指引（否则会误判为连接问题）
        bind_pwd, pwd_err = _domain_bind_password(domain)
        if pwd_err:
            diagnosis_result['issues'].append(pwd_err)
            diagnosis_result['suggestions'].append('在管理后台重新录入域控管理员密码')
            return jsonify(diagnosis_result)
        
        # 1. 测试端口连通性
        import socket
        
        def test_port(host, port):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                sock.close()
                return result == 0
            except:
                return False
        
        diagnosis_result['ldap_port_status'] = test_port(domain.ldap_host, domain.ldap_port or 389)
        diagnosis_result['ldaps_port_status'] = test_port(domain.ldap_host, domain.ldaps_port or 636)
        
        # 2. 测试 LDAP 连接（389 先升级 STARTTLS 再绑定，避免凭据明文传输）
        try:
            server = Server(f"ldap://{domain.ldap_host}:{domain.ldap_port or 389}", get_info=ALL, tls=build_tls_context(), connect_timeout=10)
            conn = Connection(server, user=domain.admin_dn, password=bind_pwd, authentication=SIMPLE, auto_bind=False)
            conn.open()
            conn.start_tls()

            if conn.bind():
                diagnosis_result['ldap_connection'] = True
                conn.unbind()
        except Exception as e:
            pass

        # 3. 测试 LDAPS 连接
        try:
            server = Server(f"ldaps://{domain.ldap_host}:{domain.ldaps_port or 636}", get_info=ALL, tls=build_tls_context(), connect_timeout=10)
            conn = Connection(server, user=domain.admin_dn, password=bind_pwd, authentication=SIMPLE, auto_bind=False)

            if conn.bind():
                diagnosis_result['ldaps_connection'] = True
                conn.unbind()
        except Exception as e:
            pass
        
        # 4. 分析结果
        if diagnosis_result['ldap_connection'] and diagnosis_result['ldaps_connection']:
            diagnosis_result['success'] = True
            diagnosis_result['message'] = 'LDAP 和 LDAPS 连接都正常'
            diagnosis_result['issues'].append('无')
            diagnosis_result['suggestions'].append('配置正确，可以正常使用')
        
        elif not diagnosis_result['ldap_connection'] and not diagnosis_result['ldaps_connection']:
            diagnosis_result['issues'].append('LDAP 和 LDAPS 连接都失败 - 密码错误或 DN 不正确')
            diagnosis_result['suggestions'].append('在 AD 服务器上重置 Administrator 密码')
            diagnosis_result['suggestions'].append('验证管理员 DN 路径是否正确')
            diagnosis_result['suggestions'].append('检查账号状态 (是否被禁用/锁定)')
            diagnosis_result['suggestions'].append('运行命令：python fix_ldaps_switch.py')
        
        elif diagnosis_result['ldap_connection'] and not diagnosis_result['ldaps_connection']:
            diagnosis_result['issues'].append('LDAP 成功但 LDAPS 失败 - LDAPS 配置问题')
            diagnosis_result['suggestions'].append('检查 AD 服务器上的 LDAPS 证书')
            diagnosis_result['suggestions'].append('在 AD 服务器上运行：netstat -an | findstr 636')
            diagnosis_result['suggestions'].append('检查防火墙规则是否允许 636 端口')
            diagnosis_result['suggestions'].append('或者继续使用 LDAP (端口 389)')
        
        elif not diagnosis_result['ldap_connection'] and diagnosis_result['ldaps_connection']:
            diagnosis_result['issues'].append('LDAP 失败但 LDAPS 成功 - LDAP 服务问题')
            diagnosis_result['suggestions'].append('检查 LDAP 服务状态')
            diagnosis_result['suggestions'].append('检查防火墙规则是否允许 389 端口')
            diagnosis_result['suggestions'].append('建议继续使用 LDAPS (更安全)')
        
        # 5. 端口状态检查
        if not diagnosis_result['ldap_port_status']:
            diagnosis_result['issues'].append(f'LDAP 端口 {domain.ldap_port or 389} 未开放')
        
        if not diagnosis_result['ldaps_port_status']:
            diagnosis_result['issues'].append(f'LDAPS 端口 {domain.ldaps_port or 636} 未开放')
        
        return jsonify(diagnosis_result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'诊断失败：{str(e)}',
            'issues': [str(e)],
            'suggestions': ['请查看后端日志获取详细信息']
        }), 200


@admin_bp.route('/api/admin/domains/<int:domain_id>', methods=['DELETE'])
@admin_required
def delete_domain(domain_id):
    """删除域配置"""
    from models.models import Domain, db
    
    try:
        domain = Domain.query.get(domain_id)
        if not domain:
            return jsonify({
                'success': False,
                'message': '域配置不存在'
            }), 404
        
        db.session.delete(domain)
        db.session.commit()

        # 审计：删除域配置属破坏性操作，必须留痕
        from utils.logger import log_operation
        log_operation('domain_delete', target_user=domain.name,
                      details='删除域配置：%s（%s）' % (domain.name, domain.ldap_hosts or domain.ldap_host))

        return jsonify({
            'success': True,
            'message': '删除成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'删除失败：{str(e)}'
        }), 500


@admin_bp.route('/domains', methods=['POST'])
@admin_required
def create_domain_html():
    """创建域配置 - HTML 表单提交"""
    from models.models import Domain, db
    import bcrypt
    
    try:
        # 获取表单数据
        name = request.form.get('name')
        ldap_host = request.form.get('ldap_host')
        ldap_port = request.form.get('ldap_port', 389, type=int)
        base_dn = request.form.get('base_dn')
        admin_dn = request.form.get('admin_dn')
        admin_password = request.form.get('admin_password')
        
        # 验证必填字段
        if not all([name, ldap_host, base_dn, admin_dn, admin_password]):
            return _alert_back('请填写所有必填字段！')

        # 创建域配置对象
        domain = Domain(
            name=name,
            ldap_hosts=ldap_host,
            ldap_host=ldap_host,
            ldap_port=ldap_port,
            base_dn=base_dn,
            admin_dn=admin_dn,
            use_ssl=bool(request.form.get('use_ssl')),
            is_active=True
        )

        # 保存密码 (加密存储，LDAP 连接时按需解密)
        domain.set_admin_password(admin_password)
        domain.set_ldap_password(admin_password)

        # 保存到数据库
        db.session.add(domain)
        db.session.commit()

        # 审计（不记录密码）
        from utils.logger import log_operation
        log_operation('domain_create', target_user=name,
                      details='添加域配置：%s（%s:%s，SSL=%s）' % (name, ldap_host, ldap_port,
                                                                bool(request.form.get('use_ssl'))))

        # 重定向到域列表页面
        from flask import redirect, url_for
        return redirect(url_for('admin.domains_page'))

    except Exception as e:
        db.session.rollback()
        return _alert_back('保存失败：%s' % e)


@admin_bp.route('/domains/test-connection', methods=['POST'])
@admin_required
def test_connection():
    """测试 LDAP 连接 - 新添加域配置时"""
    try:
        data = request.get_json()
        ldap_host = data.get('ldap_host')
        ldap_port = data.get('ldap_port', 389)
        base_dn = data.get('base_dn')
        admin_dn = data.get('admin_dn')
        admin_password = data.get('admin_password')
        use_ssl = data.get('use_ssl', False)
        
        # 验证必填字段
        if not all([ldap_host, base_dn, admin_dn, admin_password]):
            return jsonify({
                'success': False,
                'message': '缺少必填参数'
            }), 400
        
        # 尝试使用 LDAP 服务测试连接
        from services.ldap_service import LdapService
        
        # 测试连接（传入字典参数）
        result, message = LdapService.test_connection({
            'ldap_host': ldap_host,
            'ldap_port': ldap_port,
            'ldaps_port': 636,  # 默认 SSL 端口
            'base_dn': base_dn,
            'admin_dn': admin_dn,
            'admin_password': admin_password,
            'use_ssl': use_ssl  # 使用前端传递的 SSL 设置
        })
        
        if result:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 200
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'测试失败：{str(e)}'
        }), 200


@admin_bp.route('/api/admin/domains', methods=['POST'])
@admin_required
def create_domain():
    """创建域配置 - API"""
    from models.models import Domain, db
    import bcrypt
    
    data = request.json
    
    # 验证必填字段
    required_fields = ['name', 'ldap_host', 'base_dn', 'admin_dn', 'admin_password']
    for field in required_fields:
        if field not in data:
            return jsonify({'success': False, 'message': f'缺少必填字段：{field}'}), 400
    
    try:
        # 创建域配置对象
        domain = Domain(
            name=data['name'],
            ldap_host=data['ldap_host'],
            ldap_port=data.get('ldap_port', 389),
            base_dn=data['base_dn'],
            admin_dn=data['admin_dn'],
            use_ssl=data.get('use_ssl', False),
            is_active=data.get('is_active', True)
        )
        
        # 存储密码 (加密保存，连接时按需解密)
        admin_password = data['admin_password']
        domain.set_admin_password(admin_password)
        domain.set_ldap_password(admin_password)
        
        # 保存到数据库
        db.session.add(domain)
        db.session.commit()

        from utils.logger import log_operation
        log_operation('domain_create', target_user=data['name'],
                      details='添加域配置(API)：%s（%s，SSL=%s）' % (data['name'], data['ldap_host'],
                                                                   data.get('use_ssl', False)))

        return jsonify({
            'success': True,
            'message': '域配置创建成功',
            'data': {
                'id': domain.id,
                'name': domain.name,
                'ldap_host': domain.ldap_host,
                'ldap_port': domain.ldap_port,
                'base_dn': domain.base_dn,
                'admin_dn': domain.admin_dn,
                'is_active': domain.is_active
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'创建失败：{str(e)}'}), 500


@admin_bp.route('/api/admin/domains/<int:domain_id>', methods=['PUT'])
@admin_required
def update_domain(domain_id):
    """更新域配置"""
    from models.models import Domain, db
    
    data = request.json
    
    # 获取域配置
    domain = Domain.query.get(domain_id)
    if not domain:
        return jsonify({'success': False, 'message': '域配置不存在'}), 404
    
    # 更新配置
    if 'name' in data:
        domain.name = data['name']
    
    # 多主机支持
    if 'ldap_hosts' in data:
        domain.ldap_hosts = data['ldap_hosts']
    if 'ldap_host' in data:
        domain.ldap_host = data['ldap_host']
    
    if 'ldap_port' in data:
        domain.ldap_port = data['ldap_port']
    
    if 'ldaps_port' in data:
        domain.ldaps_port = data['ldaps_port']
    
    if 'base_dn' in data:
        domain.base_dn = data['base_dn']
    
    if 'admin_dn' in data:
        domain.admin_dn = data['admin_dn']
    
    if 'admin_password' in data and data['admin_password'].strip():
        domain.set_admin_password(data['admin_password'])
        domain.set_ldap_password(data['admin_password'])
    
    if 'use_ssl' in data:
        domain.use_ssl = data['use_ssl']
    
    if 'is_active' in data:
        domain.is_active = data['is_active']
    
    # 提交更改
    db.session.commit()

    from utils.logger import log_operation
    log_operation('domain_update', target_user=domain.name,
                  details='更新域配置(API)：%s（%s，SSL=%s）' % (domain.name, domain.ldap_hosts or domain.ldap_host,
                                                                domain.use_ssl))

    return jsonify({'success': True, 'message': '域配置更新成功'})




@admin_bp.route('/api/sms-config', methods=['GET'])
@login_required
def get_sms_config():
    """获取短信配置"""
    from models.models import SmsConfig, db
    
    if session.get('user_role') != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    # 获取配置
    config = SmsConfig.query.first()
    
    if config:
        return jsonify({
            'success': True,
            'data': {
                'access_key': config.access_key,
                'access_secret': '',  # 永不回传密钥到前端；用 access_secret_configured 表示是否已配置
                'access_secret_configured': bool(config.access_secret_plain),
                'sign_name': config.sign_name,
                'template_code': config.template_code,
                'is_active': config.is_active
            }
        })
    else:
        return jsonify({'success': True, 'data': None})


@admin_bp.route('/api/sms-config', methods=['POST'])
@admin_required
def save_sms_config():
    """保存短信配置"""
    from models.models import SmsConfig, db
    from utils.logger import log_operation
    
    data = request.json

    access_key = data.get('access_key')
    access_secret = data.get('access_secret')
    sign_name = data.get('sign_name')
    template_code = data.get('template_code')

    config = SmsConfig.query.first()

    # 验证：新建必须全部填；更新时 Secret 可留空（保持原值）
    required = [access_key, sign_name, template_code]
    if config is None:
        required.append(access_secret)
    if not all(required):
        msg = '请填写完整的配置信息' + ('（含 AccessKey Secret）' if config is None else '')
        return jsonify({'success': False, 'message': msg}), 400

    if config:
        config.access_key = access_key
        if access_secret:
            config.set_access_secret(access_secret)
        config.sign_name = sign_name
        config.template_code = template_code
        config.is_active = True
        action = 'sms_config_update'
        details = f'更新短信配置：签名={sign_name}, 模板={template_code}'
    else:
        config = SmsConfig(
            access_key=access_key,
            sign_name=sign_name,
            template_code=template_code,
            is_active=True
        )
        config.set_access_secret(access_secret)
        db.session.add(config)
        action = 'sms_config_create'
        details = f'创建短信配置：签名={sign_name}, 模板={template_code}'

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'短信配置保存失败: {str(e)}')
        return jsonify({'success': False, 'message': f'保存失败: {str(e)}'}), 500

    # 记录操作日志
    log_operation(action, details=details)

    return jsonify({'success': True, 'message': '短信配置保存成功'})


@admin_bp.route('/api/sms-test', methods=['POST'])
@admin_required
def send_test_sms():
    """发送测试短信"""
    from models.models import SmsConfig, db
    from services.sms_service import SmsService
    
    data = request.json
    phone = data.get('phone')
    
    if not phone:
        return jsonify({'success': False, 'message': '请输入手机号'}), 400
    
    # 获取配置
    config = SmsConfig.query.first()
    
    if not config or not config.is_active:
        return jsonify({'success': False, 'message': '短信配置未设置或已禁用'}), 400
    
    try:
        # 发送测试短信
        sms = SmsService(config)
        import secrets
        code = '%06d' % secrets.randbelow(1000000)

        ok, msg = sms.send_verification_code(phone, code)

        if ok:
            return jsonify({
                'success': True,
                'message': f'测试短信已发送到 {phone}，验证码：{code}'
            })
        else:
            return jsonify({'success': False, 'message': f'发送失败：{msg}'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'发送失败：{str(e)}'}), 500


@admin_bp.route('/api/admin/logs', methods=['GET'])
@admin_required
def get_admin_logs():
    """获取管理日志"""
    from models.models import AdminLog, User, db
    from sqlalchemy.orm import joinedload
    from datetime import datetime, timedelta

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    action_filter = request.args.get('action', '')
    username_filter = request.args.get('username', '')
    date_filter = request.args.get('date', '')

    # 构建查询（joinedload 预取管理员用户名，避免逐行 N+1）
    query = AdminLog.query.options(joinedload(AdminLog.admin))

    if action_filter:
        query = query.filter(AdminLog.action == action_filter)

    if username_filter:
        # outerjoin 保留 admin_id 为空的公开事件（重置/身份校验等），
        # 同时匹配操作管理员与目标用户
        like = '%{}%'.format(username_filter)
        query = (query.outerjoin(User, AdminLog.admin_id == User.id)
                 .filter(db.or_(User.username.ilike(like), AdminLog.target_user.ilike(like))))

    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d')
            # +1 天而不是 replace(day=day+1)：原写法在每月 28-31 日会得到空区间
            next_day = date_obj + timedelta(days=1)
            query = query.filter(AdminLog.created_at >= date_obj,
                                 AdminLog.created_at < next_day)
        except ValueError:
            pass

    # 分页排序
    pagination = query.order_by(AdminLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    logs = []
    for log in pagination.items:
        logs.append({
            'id': log.id,
            'admin_id': log.admin_id,
            'admin_username': log.admin.username if log.admin else 'system',
            'action': log.action,
            'target_user': log.target_user,
            'details': log.details,
            'ip_address': log.ip_address,
            'created_at': log.created_at.isoformat() if log.created_at else None
        })

    return jsonify({
        'success': True,
        'data': logs,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@admin_bp.route('/api/log', methods=['POST'])
@admin_required
def log_operation_api():
    """记录操作日志的 API"""
    from utils.logger import log_operation
    
    try:
        data = request.get_json()
        action = data.get('action', 'unknown')
        details = data.get('details', '')
        
        log_operation(action, details=details)
        
        return jsonify({
            'success': True
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@admin_bp.route('/api/admin/domains/verify-user', methods=['POST'])
@admin_required
def verify_user_credentials():
    """验证员工域账号密码：管理员绑定查找用户 DN，再用员工凭据绑定验证。"""
    from models.models import Domain
    from services.ldap_service import LdapService

    data = request.get_json()
    email_or_username = data.get('username', '')
    password = data.get('password', '')

    if not email_or_username or not password:
        return jsonify({'success': False, 'message': '请输入员工账号和密码'}), 400

    domain = Domain.query.filter_by(is_active=True).order_by(Domain.id).first()
    if not domain:
        return jsonify({'success': False, 'message': '未配置域，请先添加域配置'}), 400

    # 凭据解密失败时给出明确指引（否则会误报为"未找到用户"）
    _, pwd_err = _domain_bind_password(domain)
    if pwd_err:
        return jsonify({'success': False, 'message': pwd_err}), 200

    # 用管理员绑定查找用户
    user_info = LdapService.lookup_user_by_email(domain, email_or_username)
    if not user_info:
        return jsonify({'success': False, 'message': f'未找到用户 {email_or_username}（检查邮箱是否正确）'}), 404

    # 用员工的 DN + 密码做绑定验证
    ok, msg = LdapService.verify_user_bind(domain, user_info['user_dn'], password)

    # 返回用户信息 + 验证结果
    phone = user_info.get('mobile', '')
    masked = phone[:3] + '****' + phone[-4:] if len(phone) >= 7 else phone
    info = f'用户：{user_info.get("sam_account_name", email_or_username)} | 邮箱：{user_info.get("mail","")} | 手机：{masked} | DN：{user_info.get("user_dn","")}'

    if ok:
        return jsonify({'success': True, 'message': f'✅ 验证成功！{info}'})
    else:
        return jsonify({'success': False, 'message': f'❌ {msg}。{info}'})


@admin_bp.route('/change-password', methods=['GET', 'POST'])
@admin_required
def change_password_page():
    """管理员在后台修改自己的登录密码（无需脚本）。"""
    from models.models import User, db
    from services.reset_service import validate_password
    from utils.logger import log_operation
    import bcrypt as _bcrypt

    msg = None
    msg_cls = None
    if request.method == 'POST':
        current = request.form.get('current_password', '')
        new = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')
        admin = User.query.get(session.get('user_id'))
        if not admin or not admin.password_hash:
            msg, msg_cls = '账号异常，请联系系统管理员', 'err'
        elif not _bcrypt.checkpw(current.encode('utf-8'), admin.password_hash.encode('utf-8')):
            msg, msg_cls = '当前密码错误', 'err'
        elif new != confirm:
            msg, msg_cls = '两次输入的新密码不一致', 'err'
        elif not current.strip() or not new.strip():
            msg, msg_cls = '密码不能为空', 'err'
        else:
            ok, why = validate_password(new, current_app.config)
            if not ok:
                msg, msg_cls = why, 'err'
            else:
                admin.password_hash = _bcrypt.hashpw(new.encode('utf-8'), _bcrypt.gensalt()).decode('utf-8')
                db.session.commit()
                log_operation('admin_password_change', target_user=admin.username,
                              details='管理员在后台修改了自己的登录口令')
                msg, msg_cls = '密码修改成功，下次登录请使用新密码', 'ok'

    username = session.get('username', '管理员')
    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>修改密码 - 华深智药</title>
        <style>
            * { margin:0; padding:0; box-sizing:border-box; }
            body { font-family:'Microsoft YaHei',Arial,sans-serif; background:#f5f7fa; }
            .header { background:linear-gradient(135deg,#15376b 0%,#1f5fa8 100%); color:#fff; padding:20px 40px; display:flex; justify-content:space-between; align-items:center; }
            .header h1 { font-size:22px; }
            .logout-btn { background:rgba(255,255,255,.2); color:#fff; border:none; padding:8px 16px; border-radius:4px; text-decoration:none; }
            .container { max-width:480px; margin:0 auto; padding:30px; }
            .back-btn { display:inline-block; margin-bottom:20px; padding:8px 20px; background:#fff; color:#15376b; text-decoration:none; border-radius:4px; }
            .card { background:#fff; border-radius:10px; padding:30px; box-shadow:0 2px 10px rgba(0,0,0,.05); }
            .card h2 { color:#333; margin-bottom:8px; }
            .sub { color:#999; font-size:12px; margin-bottom:20px; line-height:1.6; }
            label { display:block; font-size:13px; color:#333; margin:14px 0 6px; font-weight:600; }
            input { width:100%; padding:11px 13px; border:2px solid #e0e0e0; border-radius:8px; font-size:14px; }
            input:focus { outline:none; border-color:#1f5fa8; }
            button { width:100%; margin-top:20px; padding:13px; border:none; border-radius:8px; font-size:15px; font-weight:700; color:#fff; background:linear-gradient(135deg,#15376b,#1f5fa8); cursor:pointer; }
            .msg { font-size:13px; padding:11px 13px; border-radius:6px; margin-bottom:16px; }
            .msg.ok { background:#f0f9eb; color:#67C23A; }
            .msg.err { background:#fef0f0; color:#f56c6c; }
        </style>
    </head>
    <body>
        <div class="header">
            <div style="display:flex;align-items:center;gap:12px;">
                <img src="{{ url_for('static', filename='logo.png') }}" alt="华深智药" style="height:30px;filter:drop-shadow(0 1px 4px rgba(0,0,0,.25));">
                <h1>🔑 修改登录密码</h1>
            </div>
            <div>
                <span style="margin-right:15px;">{{ username }}</span>
                <a href="/logout" class="logout-btn">退出登录</a>
            </div>
        </div>
        <div class="container">
            <a href="/admin/dashboard" class="back-btn">← 返回管理后台</a>
            <div class="card">
                <h2>修改管理员登录密码</h2>
                <p class="sub">需先验证当前密码。新密码要求：至少 8 位，含大小写字母、数字和特殊字符。</p>
                {% if msg %}
                <div class="msg {{ msg_cls }}">{{ msg }}</div>
                {% endif %}
                <form method="POST" action="/admin/change-password">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <label>当前密码</label>
                    <input type="password" name="current_password" required autocomplete="current-password">
                    <label>新密码</label>
                    <input type="password" name="new_password" required autocomplete="new-password" placeholder="至少 8 位，含大小写字母、数字、特殊字符">
                    <label>确认新密码</label>
                    <input type="password" name="confirm_password" required autocomplete="new-password">
                    <button type="submit">确认修改</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, username=username, msg=msg, msg_cls=msg_cls)


@admin_bp.route('/protected')
@admin_required
def protected_page():
    """保护名单管理页面"""
    username = session.get('username', '管理员')
    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>保护名单 - 华深智药</title>
        <style>
            * { margin:0; padding:0; box-sizing:border-box; }
            body { font-family:'Microsoft YaHei',Arial,sans-serif; background:#f5f7fa; }
            .header { background:linear-gradient(135deg,#15376b 0%,#1f5fa8 100%); color:#fff; padding:20px 40px; display:flex; justify-content:space-between; align-items:center; }
            .header h1 { font-size:22px; }
            .logout-btn { background:rgba(255,255,255,.2); color:#fff; border:none; padding:8px 16px; border-radius:4px; text-decoration:none; }
            .container { max-width:760px; margin:0 auto; padding:30px; }
            .back-btn { display:inline-block; margin-bottom:20px; padding:8px 20px; background:#fff; color:#15376b; text-decoration:none; border-radius:4px; }
            .card { background:#fff; border-radius:10px; padding:30px; box-shadow:0 2px 10px rgba(0,0,0,.05); }
            .card h2 { color:#333; margin-bottom:10px; }
            .desc { color:#666; font-size:13px; line-height:1.7; margin-bottom:20px; }
            .add-row { display:flex; gap:10px; margin-bottom:20px; }
            .add-row input { flex:1; padding:10px; border:1px solid #ddd; border-radius:6px; font-size:14px; }
            .add-row button { padding:10px 20px; border:none; background:linear-gradient(135deg,#15376b,#1f5fa8); color:#fff; border-radius:6px; cursor:pointer; font-size:14px; }
            ul { list-style:none; }
            li { display:flex; justify-content:space-between; align-items:center; gap:10px; padding:10px 14px; background:#f8faff; border:1px solid #e6eef9; border-radius:6px; margin-bottom:8px; font-size:14px; word-break:break-all; }
            li .del { background:#fef0f0; color:#f56c6c; border:none; padding:4px 10px; border-radius:4px; cursor:pointer; font-size:12px; white-space:nowrap; }
            .empty { color:#999; text-align:center; padding:24px; }
            .msg { font-size:13px; padding:10px 12px; border-radius:6px; margin-bottom:16px; display:none; }
            .msg.ok { background:#f0f9eb; color:#67C23A; display:block; }
            .msg.err { background:#fef0f0; color:#f56c6c; display:block; }
            .save-bar { margin-top:20px; text-align:right; }
            .save { padding:12px 28px; border:none; background:linear-gradient(135deg,#67C23A,#4CAF50); color:#fff; border-radius:6px; cursor:pointer; font-size:15px; font-weight:bold; }
        </style>
    </head>
    <body>
<script>const CSRF_TOKEN="{{ csrf_token() }}";(function(){var f=window.fetch;window.fetch=function(u,o){o=o||{};o.headers=o.headers||{};if(!o.headers['X-CSRFToken']){o.headers['X-CSRFToken']=CSRF_TOKEN;}return f(u,o);};})();</script>
        <div class="header">
            <div style="display:flex;align-items:center;gap:12px;">
                <img src="{{ url_for('static', filename='logo.png') }}" alt="华深智药" style="height:30px;filter:drop-shadow(0 1px 4px rgba(0,0,0,.25));">
                <h1>🛡️ 保护名单管理</h1>
            </div>
            <div>
                <span style="margin-right:15px;">{{ username }}</span>
                <a href="/logout" class="logout-btn">退出登录</a>
            </div>
        </div>
        <div class="container">
            <a href="/admin/dashboard" class="back-btn">← 返回管理后台</a>
            <div class="card">
                <h2>禁止自助重置的账号</h2>
                <p class="desc">名单中的账号（按 <b>DN / sAMAccountName / memberOf 组</b> 匹配，不区分大小写）<b>无法</b>通过公开 /reset 重置密码，必须由 IT 管理员线下处理。默认含 admin / Administrator。建议加入域管理员组 DN、服务账号。</p>
                <div class="msg" id="msg"></div>
                <div class="add-row">
                    <input id="newItem" placeholder="输入账号名、DN 或组 DN（如 CN=Domain Admins,CN=Groups,DC=x,DC=com），回车添加">
                    <button onclick="addItem()">添加</button>
                </div>
                <ul id="list"></ul>
                <div class="save-bar">
                    <button class="save" onclick="save()">💾 保存名单</button>
                </div>
            </div>
        </div>
        <script>
            let items = [];
            function show(m, cls){ const e=document.getElementById('msg'); e.textContent=m; e.className='msg '+(cls||''); }
            function esc(s){ return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
            function render(){
                const ul=document.getElementById('list');
                if(!items.length){ ul.innerHTML='<div class="empty">名单为空（所有账号都可自助重置，不推荐）</div>'; return; }
                ul.innerHTML = items.map((it,i)=>'<li><span>'+esc(it)+'</span><button class="del" onclick="delItem('+i+')">删除</button></li>').join('');
            }
            function addItem(){
                const inp=document.getElementById('newItem'); const v=inp.value.trim();
                if(!v) return;
                if(items.indexOf(v)>=0){ show('该条目已存在','err'); return; }
                items.push(v); inp.value=''; render(); show('已添加（需点保存生效）','ok');
            }
            function delItem(i){ items.splice(i,1); render(); show('已移除（需点保存生效）','ok'); }
            async function load(){
                try{
                    const d = await (await fetch('/admin/api/reset-protected-accounts')).json();
                    items = (d&&d.data)? d.data.slice() : [];
                    render();
                }catch(e){ show('加载失败：'+e,'err'); }
            }
            async function save(){
                if(!confirm('确认保存？共 '+items.length+' 条')) return;
                try{
                    const r = await fetch('/admin/api/reset-protected-accounts',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({accounts:items})});
                    const d = await r.json();
                    if(d.success){ items = d.data.slice(); render(); show('已保存（共 '+items.length+' 条）','ok'); }
                    else { show('保存失败：'+(d.message||''),'err'); }
                }catch(e){ show('保存失败：'+e,'err'); }
            }
            document.getElementById('newItem').addEventListener('keydown',e=>{ if(e.key==='Enter'){ e.preventDefault(); addItem(); }});
            load();
        </script>
    </body>
    </html>
    '''
    return render_template_string(html, username=username)


@admin_bp.route('/manual')
@admin_required
def manual_page():
    """运维操作使用手册页面"""
    username = session.get('username', '管理员')
    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>运维操作手册 - 华深智药</title>
        <style>
            * { margin:0; padding:0; box-sizing:border-box; }
            body { font-family:'Microsoft YaHei',Arial,sans-serif; background:#f5f7fa; color:#333; }
            .header { background:linear-gradient(135deg,#15376b 0%,#1f5fa8 100%); color:#fff; padding:20px 40px; display:flex; justify-content:space-between; align-items:center; position:sticky; top:0; z-index:100; box-shadow:0 2px 10px rgba(0,0,0,.15); }
            .header h1 { font-size:22px; }
            .logout-btn { background:rgba(255,255,255,.2); color:#fff; border:none; padding:8px 16px; border-radius:4px; cursor:pointer; text-decoration:none; }
            .logout-btn:hover { background:rgba(255,255,255,.3); }
            .layout { max-width:1400px; margin:0 auto; padding:30px 20px; display:flex; gap:24px; align-items:flex-start; }
            .toc { width:230px; flex-shrink:0; position:sticky; top:96px; background:#fff; border-radius:10px; padding:20px 0; box-shadow:0 2px 10px rgba(0,0,0,.05); max-height:calc(100vh - 130px); overflow-y:auto; }
            .toc a { display:block; padding:9px 20px; color:#555; text-decoration:none; font-size:13px; border-left:3px solid transparent; }
            .toc a:hover { color:#1f5fa8; background:#f0f6ff; border-left-color:#1f5fa8; }
            .toc .toc-sub a { padding-left:34px; font-size:12px; color:#888; }
            .content { flex:1; min-width:0; }
            .back-btn { display:inline-block; margin-bottom:20px; padding:8px 20px; background:#fff; color:#15376b; text-decoration:none; border-radius:4px; font-size:14px; }
            .card { background:#fff; border-radius:10px; padding:30px 34px; box-shadow:0 2px 10px rgba(0,0,0,.05); margin-bottom:24px; scroll-margin-top:96px; }
            .card h2 { font-size:20px; color:#15376b; margin-bottom:16px; padding-bottom:12px; border-bottom:2px solid #eef3fb; display:flex; align-items:center; gap:8px; }
            .card h3 { font-size:15px; color:#1f5fa8; margin:22px 0 10px; }
            .card p { font-size:14px; line-height:1.9; color:#444; margin-bottom:10px; }
            .card ul, .card ol { padding-left:22px; margin-bottom:10px; }
            .card li { font-size:14px; line-height:1.9; color:#444; }
            table { width:100%; border-collapse:collapse; margin:12px 0 16px; font-size:13px; }
            th { background:#f0f6ff; color:#15376b; font-weight:600; }
            th, td { padding:9px 12px; border:1px solid #e6eef9; text-align:left; vertical-align:top; }
            tr:nth-child(even) td { background:#fafcff; }
            code { background:#eef3fb; color:#1a4a8c; padding:2px 7px; border-radius:4px; font-family:Consolas,'Courier New',monospace; font-size:12.5px; word-break:break-all; }
            pre { background:#0f2444; color:#d8e6ff; padding:16px 18px; border-radius:8px; overflow-x:auto; margin:12px 0 16px; line-height:1.7; }
            pre code { background:none; color:#d8e6ff; padding:0; font-size:12.5px; }
            .tip { background:#f0f9eb; border-left:4px solid #67C23A; padding:12px 16px; border-radius:0 6px 6px 0; margin:12px 0; font-size:13px; line-height:1.8; color:#4a6b3a; }
            .warn { background:#fdf6ec; border-left:4px solid #E6A23C; padding:12px 16px; border-radius:0 6px 6px 0; margin:12px 0; font-size:13px; line-height:1.8; color:#8a6d3b; }
            .danger { background:#fef0f0; border-left:4px solid #F56C6C; padding:12px 16px; border-radius:0 6px 6px 0; margin:12px 0; font-size:13px; line-height:1.8; color:#a05252; }
            .flow { display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin:14px 0; }
            .flow-step { background:linear-gradient(135deg,#15376b,#1f5fa8); color:#fff; padding:12px 18px; border-radius:8px; font-size:13px; text-align:center; flex:1; min-width:130px; line-height:1.6; }
            .flow-step small { display:block; opacity:.85; font-size:11.5px; }
            .flow-arrow { color:#1f5fa8; font-size:18px; font-weight:bold; }
            details { background:#f8faff; border:1px solid #e6eef9; border-radius:8px; margin-bottom:10px; overflow:hidden; }
            details summary { padding:13px 18px; font-size:14px; font-weight:600; color:#15376b; cursor:pointer; list-style:none; display:flex; align-items:center; gap:8px; }
            details summary::before { content:'❓'; }
            details[open] summary::before { content:'✅'; }
            details summary:hover { background:#f0f6ff; }
            details .answer { padding:4px 20px 14px; font-size:13.5px; line-height:1.9; color:#444; border-top:1px dashed #e6eef9; }
            .kbd { display:inline-block; background:#fff; border:1px solid #ccc; border-bottom-width:2px; border-radius:4px; padding:1px 6px; font-size:12px; font-family:monospace; }
            .footer-note { text-align:center; color:#999; font-size:12px; padding:10px 0 30px; line-height:1.8; }
            @media (max-width: 900px) {
                .layout { flex-direction:column; }
                .toc { width:100%; position:static; max-height:none; }
                .header { padding:16px 20px; }
                .card { padding:22px 18px; }
            }
            @media print {
                .toc, .back-btn, .logout-btn { display:none; }
                .layout { padding:0; }
                .card { box-shadow:none; border:1px solid #ddd; page-break-inside:avoid; }
                body { background:#fff; }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div style="display:flex;align-items:center;gap:12px;">
                <img src="{{ url_for('static', filename='logo.png') }}" alt="华深智药" style="height:30px;filter:drop-shadow(0 1px 4px rgba(0,0,0,.25));">
                <h1>📖 运维操作手册 · 域账号密码自助重置系统</h1>
            </div>
            <div>
                <span style="margin-right:15px;">{{ username }}</span>
                <a href="/logout" class="logout-btn">退出登录</a>
            </div>
        </div>

        <div class="layout">
            <nav class="toc">
                <a href="#c1">1. 系统概览与访问入口</a>
                <a href="#c2">2. 首次上线流程</a>
                <a href="#c3">3. 服务管理（启停/日志）</a>
                <a href="#c4">4. 管理后台功能说明</a>
                <div class="toc-sub">
                    <a href="#c4-1">4.1 域配置管理</a>
                    <a href="#c4-2">4.2 短信配置</a>
                    <a href="#c4-3">4.3 操作日志</a>
                    <a href="#c4-4">4.4 保护名单</a>
                    <a href="#c4-5">4.5 修改管理员密码</a>
                </div>
                <a href="#c5">5. 用户自助重置流程</a>
                <a href="#c6">6. 配置项说明（.env）</a>
                <a href="#c7">7. 安全与限流机制</a>
                <a href="#c8">8. 日常巡检与备份</a>
                <a href="#c9">9. 常见问题排查（FAQ）</a>
                <a href="#c10">10. 应急联系与升级注意</a>
            </nav>

            <div class="content">
                <a href="/admin/dashboard" class="back-btn">← 返回管理后台</a>

                <!-- ================= 1 系统概览 ================= -->
                <div class="card" id="c1">
                    <h2>1️⃣ 系统概览与访问入口</h2>
                    <p>本系统面向远程/办公用户提供 <b>AD 域账号忘记密码的自助重置</b> 服务：用户在公开页面输入邮箱与手机号，系统与域控（AD）登记信息比对，比对通过后发送短信验证码，验证通过即可设置新密码。AD 密码修改完成后由 <b>Microsoft Entra Connect 自动同步到 Azure AD</b>（本系统不直连 AAD）。</p>
                    <h3>技术栈</h3>
                    <p>Python 3.10+ · Flask 3 · SQLAlchemy · ldap3（AD/LDAP）· 阿里云短信 SDK · cryptography（Fernet 凭据加密）· SQLite（默认）/ PostgreSQL · gunicorn（Linux）/ waitress（Windows）</p>
                    <h3>网络架构</h3>
                    <pre><code>内网用户 ──HTTP──&gt;  服务器:5000 (gunicorn)
外网用户 ──HTTPS──&gt; [WAF（证书/TLS）] ──HTTP──&gt; 服务器:5000
                                            ├─ /reset    公开重置向导（全网开放）
                                            ├─ /login    管理员登录（可限内网白名单）
                                            └─ /admin/*  管理后台
        服务器 ──LDAP(389/STARTTLS 或 636/LDAPS)──&gt; 域控 AD
        服务器 ──API──&gt; 阿里云短信（验证码 + 重置通知）
[Microsoft Entra Connect]  自动同步 AD 密码到 Azure AD / M365</code></pre>
                    <h3>访问入口</h3>
                    <table>
                        <tr><th>入口</th><th>地址</th><th>说明</th></tr>
                        <tr><td>用户重置页</td><td><code>/reset</code></td><td>公开页面，全员可用，无需登录</td></tr>
                        <tr><td>管理员登录</td><td><code>/login</code></td><td>默认账号 <code>admin</code>；登录失败 5 次锁 IP 15 分钟；可配置 <code>ADMIN_ALLOWED_IPS</code> 内网白名单</td></tr>
                        <tr><td>管理后台首页</td><td><code>/admin/dashboard</code></td><td>登录后进入，含统计卡片与功能菜单</td></tr>
                        <tr><td>健康检查</td><td><code>/health</code></td><td>返回 JSON 状态，可用于负载均衡/监控探活</td></tr>
                        <tr><td>退出登录</td><td><code>/logout</code></td><td>清除会话</td></tr>
                    </table>
                    <div class="tip">💡 默认端口 <b>5000</b>。完整地址形如 <code>http://服务器IP:5000/reset</code>；外网经 WAF 以 HTTPS 访问。</div>
                </div>

                <!-- ================= 2 首次上线 ================= -->
                <div class="card" id="c2">
                    <h2>2️⃣ 首次上线流程</h2>
                    <h3>2.1 服务器部署（Linux，一条命令）</h3>
                    <pre><code>cd 项目目录
bash deploy_linux.sh prod</code></pre>
                    <p>脚本自动完成：创建虚拟环境 → 升级 pip → 安装依赖 → 生成 <code>.env</code>（随机 SECRET_KEY 与加密密钥）→ 强制 <code>DEMO_MODE=false</code> → 端口冲突检查 → 后台启动 gunicorn（2 workers × 4 threads）。首次启动自动建表并创建管理员 <code>admin</code>。</p>
                    <table>
                        <tr><th>场景</th><th>命令</th></tr>
                        <tr><td>自定义初始管理员口令</td><td><code>ADMIN_PASSWORD=你的强口令 bash deploy_linux.sh prod</code></td></tr>
                        <tr><td>使用 PostgreSQL</td><td><code>DATABASE_URL=postgresql://user:pwd@host:5432/db bash deploy_linux.sh prod</code></td></tr>
                        <tr><td>更换端口</td><td><code>SYSTEM_PORT=5001 bash deploy_linux.sh prod</code></td></tr>
                        <tr><td>DEMO 体验模式</td><td><code>bash deploy_linux.sh</code>（不连真实 AD，邮箱任意、手机 13800000000）</td></tr>
                        <tr><td>Windows 服务器</td><td>运行 <code>deploy_windows.bat</code> 或 <code>start_windows.bat</code>；直接 <code>python app.py</code> 时自动使用 waitress</td></tr>
                    </table>
                    <h3>2.2 登录后台后必做 3 件事</h3>
                    <ol>
                        <li><b>🌐 域配置</b> → 填域名（Base DN / 管理员 DN 自动生成）→ 点【🔗 测试连接】通过后再保存 → 用【🔍 员工域账号验证】拿一个真实员工账号复核；</li>
                        <li><b>💬 短信配置</b> → 填阿里云 AccessKey / Secret / 签名 / 模板 CODE → 保存后【发送测试】到自己手机确认能收到；</li>
                        <li><b>🔑 修改密码</b> → 把默认的 <code>admin/admin</code> 改成强口令（默认口令存在被登录的风险，务必第一时间修改）。</li>
                    </ol>
                    <div class="warn">⚠️ 生产环境必须保证 <code>DEMO_MODE=false</code>（prod 部署脚本会自动强制）。DEMO 模式不连真实域控与短信，仅用于体验。</div>
                    <h3>2.3 可选：开机常驻（systemd）</h3>
                    <pre><code># 先按实际部署路径修改服务文件中的路径，再执行：
sudo cp systemd/ad-password-manager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ad-password-manager</code></pre>
                    <p>使用 systemd 后服务崩溃自动重启（Restart=always）、开机自启；此时不需要再跑 deploy 脚本启动。</p>
                    <h3>2.4 HTTPS（WAF 场景）</h3>
                    <p>服务器本机跑 HTTP:5000，由 WAF 回源并挂证书；防火墙将 5000 端口限制为只允许 WAF 与内网网段访问。<code>.env</code> 保持 <code>HTTPS_ENABLED=false</code>（同时兼容内网 HTTP 直连与外网 WAF HTTPS）。若纯 HTTPS 部署则改为 <code>true</code>（Session Cookie 仅走 HTTPS）。</p>
                </div>

                <!-- ================= 3 服务管理 ================= -->
                <div class="card" id="c3">
                    <h2>3️⃣ 服务管理（启停 / 状态 / 日志）</h2>
                    <h3>3.1 deploy 脚本方式（默认部署）</h3>
                    <table>
                        <tr><th>操作</th><th>命令</th></tr>
                        <tr><td>查看状态</td><td><code>bash deploy_linux.sh status</code></td></tr>
                        <tr><td>停止服务</td><td><code>bash deploy_linux.sh stop</code></td></tr>
                        <tr><td>重启服务</td><td>重新执行 <code>bash deploy_linux.sh prod</code>（自动停旧起新）</td></tr>
                        <tr><td>查看进程 PID</td><td><code>cat backend/.app.pid</code></td></tr>
                        <tr><td>查看实时日志</td><td><code>tail -f backend/logs/app.log</code></td></tr>
                    </table>
                    <h3>3.2 systemd 方式（安装后）</h3>
                    <pre><code>sudo systemctl start|stop|restart ad-password-manager   # 启动/停止/重启
sudo systemctl status ad-password-manager              # 状态
sudo journalctl -u ad-password-manager -f              # 实时日志
sudo journalctl -u ad-password-manager -n 100          # 最近 100 行</code></pre>
                    <h3>3.3 日志说明</h3>
                    <ul>
                        <li>应用日志：<code>backend/logs/app.log</code>，自动轮转（单文件 10MB，保留 5 份），包含请求日志、LDAP 改密诊断、审计事件等；</li>
                        <li>gunicorn 启动输出也追加写入 <code>backend/logs/app.log</code>；</li>
                        <li>业务审计（登录/重置/配置变更等）同时可在后台【📊 操作日志】页面按类型、用户、日期筛选查询。</li>
                    </ul>
                    <h3>3.4 常用检查命令</h3>
                    <pre><code>curl http://127.0.0.1:5000/health          # 健康检查（正常返回 status: healthy）
ss -tlnp | grep :5000                     # 查看端口占用
ps aux | grep gunicorn                    # 查看进程</code></pre>
                </div>

                <!-- ================= 4 后台功能 ================= -->
                <div class="card" id="c4">
                    <h2>4️⃣ 管理后台功能说明</h2>

                    <h3 id="c4-1">4.1 🌐 域配置管理（/admin/domains）</h3>
                    <p>配置要对接的 AD 域控。点击【添加域配置】：</p>
                    <ul>
                        <li><b>域名</b>：填域名（如 <code>helixon.com</code>），Base DN（<code>DC=helixon,DC=com</code>）与管理员 DN 会<b>自动生成</b>，可手动微调；</li>
                        <li><b>LDAP 主机 / 端口</b>：默认 389（明文端口，改密时自动升级 STARTTLS 加密，域控需安装证书）；勾选"启用 LDAPS"则切到 636 端口 SSL 直连；</li>
                        <li><b>管理员账号名 / 密码</b>：用于查询用户、执行改密的 AD 服务账号凭据，<b>Fernet 加密存储</b>，接口永不回传明文；</li>
                        <li>先点【🔗 测试连接】通过后【保存配置】按钮才会启用。</li>
                    </ul>
                    <p>列表页可对已存域执行【测试连接】【编辑】【删除】。<b>🔍 员工域账号验证</b>：输入任一员工的邮箱+密码即可验证"域控连通 + 账号密码正确"，用于上线自检和协助员工排查登录问题。</p>
                    <div class="tip">💡 改密默认走 389 端口 STARTTLS 加密，<b>无需在域控上开放 636/LDAPS</b>；但域控必须安装计算机证书，否则 STARTTLS 升级会失败（见 FAQ）。</div>

                    <h3 id="c4-2">4.2 💬 短信配置（/admin/sms）</h3>
                    <p>配置阿里云短信服务（验证码与重置通知都走它）：</p>
                    <ul>
                        <li><b>Access Key ID / Secret</b>：阿里云 RAM 账号密钥，Secret 加密存储、不回传（已配置时留空表示保持不变）；</li>
                        <li><b>短信签名</b>：需提前在阿里云控制台申请通过；</li>
                        <li><b>模板 CODE</b>：验证码模板（形如 <code>SMS_123456789</code>）；</li>
                        <li>【发送测试】填自己手机号验证整条链路（会产生少量短信费用）。</li>
                    </ul>

                    <h3 id="c4-3">4.3 📊 操作日志（/admin/logs）</h3>
                    <p>系统审计日志，支持按<b>操作类型</b>（登录成功/失败、重置成功/失败、身份校验、验证码错误、短信故障、管理员改密、保护名单更新、域配置变更、短信配置等）、<b>用户名</b>、<b>日期</b>筛选，分页浏览。可用于安全审计与故障定位。</p>

                    <h3 id="c4-4">4.4 🛡️ 保护名单（/admin/protected）</h3>
                    <p>名单中的账号<b>禁止</b>通过公开 /reset 自助重置（防止域管/服务账号密码被恶意重置）：</p>
                    <ul>
                        <li>默认含 <code>admin</code>、<code>Administrator</code>；</li>
                        <li>支持三种标识（不区分大小写）：用户 DN、sAMAccountName、组 DN（memberOf 匹配）；</li>
                        <li>建议加入：域管理员组 DN、所有服务账号；</li>
                        <li>添加/删除后需点【💾 保存名单】生效。</li>
                    </ul>

                    <h3 id="c4-5">4.5 🔑 修改密码（/admin/change-password）</h3>
                    <p>管理员修改自己的后台登录口令：需先输入当前密码验证；新密码至少 8 位且含大小写字母、数字、特殊字符。修改成功后下次登录使用新密码。</p>
                </div>

                <!-- ================= 5 用户流程 ================= -->
                <div class="card" id="c5">
                    <h2>5️⃣ 用户自助重置流程（可转发给员工）</h2>
                    <div class="flow">
                        <div class="flow-step">① 身份校验<small>输入 AD 登记的<br>邮箱 + 手机号</small></div>
                        <div class="flow-arrow">→</div>
                        <div class="flow-step">② 短信验证码<small>60 秒可重发<br>5 分钟内有效</small></div>
                        <div class="flow-arrow">→</div>
                        <div class="flow-step">③ 设置新密码<small>两次输入一致<br>需符合密码策略</small></div>
                        <div class="flow-arrow">→</div>
                        <div class="flow-step">④ 完成<small>动画成功页<br>新密码立即可用</small></div>
                    </div>
                    <ul>
                        <li>邮箱与手机号必须与 <b>AD 中登记的 mail / mobile 完全一致</b>，否则第一步即被拒绝；</li>
                        <li>新密码要求：至少 8 位，包含大写、小写、数字、特殊字符，且<b>不能包含用户名</b>（AD 域策略会拒绝）；</li>
                        <li>重置成功后：<b>域内登录（电脑解锁、VPN 等）立即生效</b>；云服务（M365/邮箱等）因依赖 Entra Connect 同步，约 <b>2-3 分钟</b>后生效；</li>
                        <li>整个向导会话 10 分钟超时，超时需重新开始；验证码输错 5 次作废需重发。</li>
                    </ul>
                    <div class="tip">💡 员工反馈"邮箱手机都对却过不了第一步"时，多为 AD 属性未登记或与员工填写不一致，请用后台【员工域账号验证】工具核对，或让域管理员补全 AD 的 mail/mobile 属性。</div>
                </div>

                <!-- ================= 6 配置 ================= -->
                <div class="card" id="c6">
                    <h2>6️⃣ 配置项说明（backend/.env）</h2>
                    <p>修改 .env 后需重启服务生效。文件含密钥，已在 .gitignore 中，<b>切勿提交到代码库</b>。</p>
                    <table>
                        <tr><th>配置项</th><th>默认</th><th>说明</th></tr>
                        <tr><td><code>SECRET_KEY</code></td><td>必填</td><td>Flask 会话签名密钥（部署脚本自动生成随机值）</td></tr>
                        <tr><td><code>DATABASE_URL</code></td><td>必填</td><td>默认 SQLite（<code>sqlite:///ad_password.db</code>），可换 PostgreSQL</td></tr>
                        <tr><td><code>SECRET_ENCRYPTION_KEY</code></td><td>必填</td><td>Fernet 密钥，用于加密 AD/短信凭据；<b>丢失则已存凭据全部无法解密，需重新录入</b></td></tr>
                        <tr><td><code>DEMO_MODE</code></td><td>false</td><td>演示模式；<b>生产必须 false</b></td></tr>
                        <tr><td><code>ADMIN_PASSWORD</code></td><td>admin</td><td>仅首次建号时使用的初始口令</td></tr>
                        <tr><td><code>HTTPS_ENABLED</code></td><td>false</td><td>false=HTTP 与 WAF HTTPS 双模式；true=纯 HTTPS（Cookie 仅加密传输）</td></tr>
                        <tr><td><code>SESSION_TIMEOUT</code></td><td>8</td><td>管理员会话超时（小时）</td></tr>
                        <tr><td><code>ADMIN_ALLOWED_IPS</code></td><td>空</td><td>/login 与 /admin/* 的 IP 白名单，支持 CIDR，逗号分隔（如 <code>10.0.0.0/8,192.168.1.0/24</code>）；<b>留空=不限制</b></td></tr>
                        <tr><td><code>LDAP_TLS_VALIDATE</code></td><td>false</td><td>是否校验域控 TLS 证书；域控证书由内部 CA 签发时可设 true（需配合下一项）</td></tr>
                        <tr><td><code>LDAP_CA_CERT</code></td><td>空</td><td>CA 证书文件路径，配合 <code>LDAP_TLS_VALIDATE=true</code> 启用强校验；默认不校验以兼容自签名证书</td></tr>
                        <tr><td><code>PASSWORD_MIN_LENGTH</code> 等</td><td>8/全开</td><td>新密码策略：最小长度、是否要求大小写/数字/特殊字符</td></tr>
                        <tr><td><code>SMS_ASYNC_SEND</code></td><td>true</td><td>短信异步发送（抹平响应时序差；调试时可关）</td></tr>
                        <tr><td><code>LOG_LEVEL / LOG_FILE</code></td><td>INFO / logs/app.log</td><td>日志级别与路径；单文件 10MB 轮转保留 5 份</td></tr>
                    </table>
                </div>

                <!-- ================= 7 安全机制 ================= -->
                <div class="card" id="c7">
                    <h2>7️⃣ 安全与限流机制</h2>
                    <h3>7.1 限流与锁定（达到阈值自动触发，到期自动解除）</h3>
                    <table>
                        <tr><th>维度</th><th>规则</th></tr>
                        <tr><td>同一手机号</td><td>60 秒冷却 + 每小时最多 5 条验证码</td></tr>
                        <tr><td>同一邮箱</td><td>每小时最多 5 次发码</td></tr>
                        <tr><td>同一 IP</td><td>每小时最多 20 次发码</td></tr>
                        <tr><td>身份校验失败</td><td>同一 IP 连续失败 10 次 → 锁定 30 分钟（防账号枚举）</td></tr>
                        <tr><td>管理员登录失败</td><td>同一 IP 失败 5 次 → 锁定 15 分钟（防暴力破解），成功后计数清零</td></tr>
                        <tr><td>验证码</td><td>5 分钟有效；输错 5 次作废需重发</td></tr>
                        <tr><td>重置会话</td><td>10 分钟超时；一次性授权；重置目标仅取自服务端会话，请求无法越权指定</td></tr>
                    </table>
                    <p class="footer-note" style="text-align:left;">身份校验通过后失败计数自动清零。所有计数使用数据库原子行锁实现，多 worker 并发下依然准确。</p>
                    <h3>7.2 数据与传输保护</h3>
                    <ul>
                        <li>AD 管理员密码、阿里云 Secret 使用 Fernet 加密入库，接口永不回传明文；</li>
                        <li>AD 改密默认 389 端口 STARTTLS 加密（或 636 LDAPS）；改密后用新密码做 LDAP 绑定二次验证确保生效；</li>
                        <li>LDAP 过滤器转义防注入、ORM 防 SQL 注入、Jinja 自动转义防 XSS；</li>
                        <li>全部 POST 接口受 CSRF 保护；Session Cookie HttpOnly + SameSite=Lax；</li>
                        <li>安全响应头（隐藏 Server 版本、CSP、HSTS、防点击劫持等）；反向代理下取真实客户端 IP 用于限流。</li>
                    </ul>
                </div>

                <!-- ================= 8 巡检备份 ================= -->
                <div class="card" id="c8">
                    <h2>8️⃣ 日常巡检与备份</h2>
                    <h3>8.1 建议巡检频率</h3>
                    <table>
                        <tr><th>频率</th><th>项目</th><th>方法</th></tr>
                        <tr><td>每天</td><td>服务存活</td><td><code>curl http://127.0.0.1:5000/health</code> 或监控探针</td></tr>
                        <tr><td>每天</td><td>错误日志</td><td>后台【操作日志】筛"重置失败/短信发送失败"；或 <code>grep ERROR backend/logs/app.log</code></td></tr>
                        <tr><td>每周</td><td>域连通性</td><td>后台域配置页点【测试连接】+【员工域账号验证】</td></tr>
                        <tr><td>每周</td><td>磁盘与日志体积</td><td>日志已自动轮转；必要时清理 <code>logs/</code> 旧文件</td></tr>
                        <tr><td>变更时</td><td>配置备份</td><td>修改 .env / 域配置 / 短信配置前先备份数据库（见下）</td></tr>
                    </table>
                    <h3>8.2 数据库备份</h3>
                    <pre><code># SQLite（默认）：项目根目录执行，备份到 backups/ 目录
python scripts/backup_database.py

# PostgreSQL：使用 pg_dump
pg_dump -U user -h host dbname &gt; backup_$(date +%Y%m%d).sql</code></pre>
                    <p>库内主要是：管理员账号、域配置（凭据密文）、短信配置（密文）、审计日志、限流计数。<b>用户密码不在本系统存储。</b></p>
                    <h3>8.3 系统自检</h3>
                    <pre><code>python scripts/health_check.py   # 检查数据库连接、管理员账号、域配置等</code></pre>
                </div>

                <!-- ================= 9 FAQ ================= -->
                <div class="card" id="c9">
                    <h2>9️⃣ 常见问题排查（FAQ）</h2>

                    <details>
                        <summary>域配置"测试连接"失败？</summary>
                        <div class="answer">依次检查：① LDAP 主机 IP/域名与端口（389 或 636）是否可达（<code>telnet dc_IP 389</code>）；② Base DN / 管理员 DN 是否拼对（页面填域名可自动生成）；③ 管理员密码是否正确/未过期；④ 账号是否被锁定。页面提示会带具体错误信息，也可查 <code>backend/logs/app.log</code>。</div>
                    </details>
                    <details>
                        <summary>改密时报"STARTTLS 失败 / 域控未装证书"？</summary>
                        <div class="answer">系统默认在 389 端口自动升级 STARTTLS 加密后改密，要求域控安装了计算机证书（AD CS 自动注册或手工导入）。解决办法：给域控安装证书；或域配置页勾选"启用 LDAPS"改走 636 端口。</div>
                    </details>
                    <details>
                        <summary>用户设置新密码总提示不符合策略？</summary>
                        <div class="answer">默认策略：至少 8 位 + 大写 + 小写 + 数字 + 特殊字符，且<b>不能包含用户名</b>（AD 域策略还会要求密码不含用户名/姓名片段、受"最短密码期限"限制）。请引导用户换一个全新的密码。注意：<b>重置成功后短期内不要反复重试改密</b>，AD 有最短密码期限制。</div>
                    </details>
                    <details>
                        <summary>用户说收不到验证码短信？</summary>
                        <div class="answer">① 后台【短信配置】→ 发送测试到自己手机，确认阿里云配置与签名/模板有效；② 查【操作日志】筛"短信发送失败"看具体错误；③ 确认未触发限流（同手机 60 秒冷却、每小时 5 条）；④ 确认 AD 里的手机号与用户输入一致（11 位、无多余字符）。</div>
                    </details>
                    <details>
                        <summary>第一步就提示"邮箱或手机号与域控登记信息不匹配"？</summary>
                        <div class="answer">系统要求两者与 AD 的 mail / mobile 属性<b>完全一致</b>才放行。用后台【员工域账号验证】验证该员工账号，或让域管理员核对/补全 AD 属性。为防账号枚举，系统不会提示具体是哪一项不对。</div>
                    </details>
                    <details>
                        <summary>管理员忘记后台登录密码怎么办？</summary>
                        <div class="answer">admin 在保护名单内，<b>不能</b>走公开重置流程。在服务器上执行：<pre style="margin:8px 0 0;"><code>cd backend &amp;&amp; python init_admin_password.py</code></pre>密码将被重置为 <code>admin</code>，登录后<b>立即</b>到【修改密码】页改成强口令。</div>
                    </details>
                    <details>
                        <summary>管理员登录页打不开 / 403 禁止访问？</summary>
                        <div class="answer">若 .env 配置了 <code>ADMIN_ALLOWED_IPS</code> 白名单，/login 与 /admin/* 只允许名单内 IP/CIDR 访问。请确认访问出口 IP 在名单内，或让运维把对应网段加入白名单后重启服务。<code>/reset</code> 不受此限制。</div>
                    </details>
                    <details>
                        <summary>IP 被锁定了怎么办？</summary>
                        <div class="answer">身份校验连续失败 10 次锁 30 分钟；管理员登录失败 5 次锁 15 分钟。属自动防护、到期自动解除，无需处理。若确认是正常用户触发，告知等待锁定期结束即可。</div>
                    </details>
                    <details>
                        <summary>重置成功了，但邮箱/M365 登录还是旧密码？</summary>
                        <div class="answer">云服务密码由 Microsoft Entra Connect 自动同步，一般 <b>2-3 分钟</b>生效；个别情况取决于同步周期。域内登录（域电脑、VPN）立即生效。若长时间未同步请检查 Entra Connect 同步任务状态。</div>
                    </details>
                    <details>
                        <summary>启动失败 / 端口被占用？</summary>
                        <div class="answer">查看日志定位：<code>tail -100 backend/logs/app.log</code>。端口占用：<code>ss -tlnp | grep :5000</code>，可换端口启动：<code>SYSTEM_PORT=5001 bash deploy_linux.sh prod</code>。若 .env 手工编辑过，检查 SECRET_KEY / DATABASE_URL 是否为空（为空会拒绝启动）。</div>
                    </details>
                    <details>
                        <summary>如何确认一次重置是否真的成功？</summary>
                        <div class="answer">系统改密后会自动用<b>新密码做一次 LDAP 绑定验证</b>，确保密码确实生效；后台【操作日志】中"重置成功"事件可查（含脱敏手机号）。失败事件同样有记录与原因。</div>
                    </details>
                </div>

                <!-- ================= 10 应急 ================= -->
                <div class="card" id="c10">
                    <h2>🔟 应急处理与升级注意</h2>
                    <h3>10.1 应急速查</h3>
                    <table>
                        <tr><th>状况</th><th>处置</th></tr>
                        <tr><td>服务无响应</td><td><code>bash deploy_linux.sh status</code> → 看日志 → 重启（重新跑 prod 脚本或 systemctl restart）</td></tr>
                        <tr><td>域控换 IP/密码</td><td>后台【域配置】编辑并【测试连接】</td></tr>
                        <tr><td>阿里云密钥泄露</td><td>阿里云控制台禁用旧 Key → 后台【短信配置】换新 Key → 发送测试</td></tr>
                        <tr><td>怀疑账号被枚举攻击</td><td>【操作日志】筛"身份校验未通过"看来源 IP；IP 锁定机制会自动拦截，必要时防火墙封禁</td></tr>
                        <tr><td>加密密钥（SECRET_ENCRYPTION_KEY）疑似泄露</td><td>换新密钥后需在后台重新录入域控与短信凭据（旧密文无法解密）</td></tr>
                    </table>
                    <h3>10.2 升级 / 代码更新</h3>
                    <ol>
                        <li>先备份数据库（见第 8 章）；</li>
                        <li>拉取/部署新代码；</li>
                        <li>若有数据库迁移 SQL（database/ 目录），先在库上执行；</li>
                        <li>重启服务并 <code>curl /health</code> 验证；后台点【测试连接】复核域控连通。</li>
                    </ol>
                    <div class="danger">⛔ 红线事项：① 生产环境 DEMO_MODE 必须为 false；② 默认 admin/admin 口令必须首次登录即改；③ .env 与数据库备份文件含密钥/密文，不得外传或提交 git；④ 保护名单中的账号（域管/服务账号）密码变更一律线下流程，不得从名单移除后走自助重置。</div>
                </div>

                <div class="footer-note">
                    华深智药 · 域账号密码自助重置系统 — 运维操作手册<br>
                  以服务器上的实际部署配置为准；本页面仅登录后台后可见（Ctrl/Command + P 可打印为 PDF）。
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, username=username)


@admin_bp.route('/api/reset-protected-accounts', methods=['GET'])
@admin_required
def get_protected_accounts():
    import json
    from models.models import SystemSetting
    st = SystemSetting.query.filter_by(setting_key='reset_protected_accounts').first()
    items = []
    if st and st.setting_value:
        try:
            items = json.loads(st.setting_value)
        except Exception:
            items = []
    if not items:
        items = ['admin', 'Administrator']
    return jsonify({'success': True, 'data': items})


@admin_bp.route('/api/reset-protected-accounts', methods=['PUT'])
@admin_required
def update_protected_accounts():
    import json
    from models.models import SystemSetting, db
    from utils.logger import log_operation
    data = request.get_json(silent=True) or {}
    items = data.get('accounts', [])
    if not isinstance(items, list):
        return jsonify({'success': False, 'message': '参数错误'}), 400
    cleaned = [str(x).strip() for x in items if str(x).strip()]
    st = SystemSetting.query.filter_by(setting_key='reset_protected_accounts').first()
    if not st:
        st = SystemSetting(setting_key='reset_protected_accounts',
                           setting_type='json', description='禁止自助重置的账号')
        db.session.add(st)
    st.setting_value = json.dumps(cleaned)
    db.session.commit()
    log_operation('protected_list_update', details='更新保护名单：%d 项' % len(cleaned))
    return jsonify({'success': True, 'data': cleaned})

