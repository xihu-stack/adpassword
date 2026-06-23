from flask import Blueprint, request, jsonify, session, current_app, render_template_string
try:
    from services.ldap_service import LdapService
except ImportError:
    from services.ldap_service_mock import LdapService
from utils.decorators import admin_required, login_required
from datetime import datetime

admin_bp = Blueprint('admin', __name__)


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
                <a href="/" class="menu-item">
                    <div class="menu-icon">🏠</div>
                    <div class="menu-title">返回首页</div>
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
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">域名称</label>
                            <input type="text" name="name" placeholder="例如：example.com" required style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">LDAP 主机</label>
                            <input type="text" name="ldap_host" placeholder="例如：192.168.1.100" required style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">LDAP 端口</label>
                            <input type="number" name="ldap_port" id="ldap_port" value="389" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                            <div style="margin-top: 12px;">
                                <label class="checkbox-label" style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                    <input type="checkbox" id="use_ssl" onchange="onSSLChanged()" style="width: 16px; height: 16px; cursor: pointer;">
                                    <span>🔒 启用 LDAPS (SSL 加密连接)</span>
                                </label>
                                <small style="color: #999; display: block; margin-top: 5px;">启用后会自动切换到 LDAPS 端口（636），需要服务器支持 SSL。普通 LDAP 端口：389，LDAPS 端口：636</small>
                            </div>
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">基础 DN</label>
                            <input type="text" name="base_dn" placeholder="例如：DC=example,DC=com" required style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">管理员 DN</label>
                            <input type="text" name="admin_dn" placeholder="例如：CN=Administrator,CN=Users,DC=example,DC=com" required style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
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
            </div>
        </div>
        
        <script>
            // 页面加载时获取域配置列表
            document.addEventListener('DOMContentLoaded', function() {
                loadDomainList();
            });
            
            function showAddForm() {
                document.querySelector('.empty-state').style.display = 'none';
                document.getElementById('addForm').style.display = 'block';
            }
            
            function hideAddForm() {
                document.getElementById('addForm').style.display = 'none';
                document.querySelector('.empty-state').style.display = 'block';
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
            
            // 渲染域配置列表
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
                                    <h4 style="margin: 0 0 5px 0; color: #333; font-size: 16px;">${domain.name}</h4>
                                    <p style="margin: 0; color: #666; font-size: 14px;">${domain.ldap_host}:${domain.ldap_port}</p>
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
                                <span style="color: #333; margin-left: 10px;">${domain.base_dn}</span>
                            </div>
                            <div>
                                <span style="color: #999;">管理员 DN:</span>
                                <span style="color: #333; margin-left: 10px;">${domain.admin_dn || '-'}</span>
                            </div>
                            <div>
                                <span style="color: #999;">创建时间:</span>
                                <span style="color: #333; margin-left: 10px;">${domain.created_at || '-'}</span>
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
                            document.getElementById('accessSecret').value = data.data.access_secret || '';
                            document.getElementById('signName').value = data.data.sign_name || '';
                            document.getElementById('templateCode').value = data.data.template_code || '';
                            
                            // 更新状态徽章
                            updateStatus('accessKeyStatus', data.data.access_key);
                            updateStatus('accessSecretStatus', data.data.access_secret);
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
                
                // 验证必填项
                if (!formData.access_key || !formData.access_secret || !formData.sign_name || !formData.template_code) {
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
                        <option value="login">登录</option>
                        <option value="password_reset">密码重置</option>
                        <option value="user_sync">用户同步</option>
                        <option value="user_create">用户创建</option>
                        <option value="user_update">用户更新</option>
                        <option value="user_delete">用户删除</option>
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
                                <td>${time}</td>
                                <td>${log.admin_username || '-'}</td>
                                <td><span class="badge ${badgeClass}">${formatAction(log.action)}</span></td>
                                <td>${log.target_user || '-'}</td>
                                <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${log.details || '-'}</td>
                                <td>${log.ip_address || '-'}</td>
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
                    'password_reset': 'badge-password',
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
                    'login': '登录',
                    'password_reset': '密码重置',
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
        use_ssl = request.form.get('use_ssl', 'false').lower() == 'true'
        
        # 优先使用 ldap_hosts，如果没有则使用 ldap_host
        if not ldap_hosts:
            ldap_hosts = ldap_host
        
        # 验证必填字段
        if not all([name, ldap_hosts, base_dn, admin_dn]):
            return '''
            <script>
                alert('请填写所有必填字段！');
                window.history.back();
            </script>
            '''
        
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
            return '''
            <script>
                alert('首次配置必须输入 LDAP 管理员密码！');
                window.history.back();
            </script>
            '''
        
        # 保存到数据库
        db.session.commit()
        
        # 重定向到域列表页面
        from flask import redirect, url_for
        return redirect(url_for('admin.domains_page'))
        
    except Exception as e:
        db.session.rollback()
        return f'''
        <script>
            alert('保存失败：{str(e)}');
            window.history.back();
        </script>
        '''


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


@admin_bp.route('/api/admin/domains/test', methods=['POST'])
@admin_required
def test_domain_connection_live(domain_id):
    """测试域配置连接 - 支持实时测试（使用前端传来的密码）"""
    from models.models import Domain, db
    import logging
    
    try:
        data = request.get_json()
        
        # 记录接收到的数据
        logging.info(f'[测试连接 API] 接收到数据：{data}')
        
        # 优先使用前端传来的配置，否则从数据库读取
        if data:
            # 使用前端传来的配置
            config = {
                'ldap_hosts': data.get('ldap_hosts'),
                'ldap_host': data.get('ldap_host'),
                'ldap_port': data.get('ldap_port'),
                'ldaps_port': data.get('ldaps_port'),
                'base_dn': data.get('base_dn'),
                'admin_dn': data.get('admin_dn'),
                'admin_password': data.get('admin_password', ''),
                'use_ssl': data.get('use_ssl', False)
            }
            logging.info(f'[测试连接 API] 使用前端配置：use_ssl={config["use_ssl"]}, ldap_port={config["ldap_port"]}')
        else:
            # 从数据库读取
            domain = Domain.query.get(domain_id)
            if not domain:
                return jsonify({
                    'success': False,
                    'message': '域配置不存在'
                }), 404
            
            config = {
                'ldap_host': domain.ldap_host,
                'ldap_port': domain.ldap_port,
                'ldaps_port': domain.ldaps_port,
                'base_dn': domain.base_dn,
                'admin_dn': domain.admin_dn,
                'admin_password': domain.ldap_password_plain or domain.admin_password_plain,
                'use_ssl': domain.use_ssl
            }
            logging.info(f'[测试连接 API] 使用数据库配置：use_ssl={config["use_ssl"]}, ldap_port={config["ldap_port"]}')
        
        # 使用 LDAP 服务测试连接
        try:
            from services.ldap_service import LdapService
        except ImportError:
            from services.ldap_service_mock import LdapService
        
        # 测试连接
        result, message = LdapService.test_connection(config)
        
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
        try:
            from services.ldap_service import LdapService
        except ImportError:
            from services.ldap_service_mock import LdapService
        
        # 测试连接（传入字典参数）
        result, message = LdapService.test_connection({
            'ldap_host': domain.ldap_host,
            'ldap_port': domain.ldap_port,
            'ldaps_port': domain.ldaps_port,
            'base_dn': domain.base_dn,
            'admin_dn': domain.admin_dn,
            'admin_password': domain.ldap_password_plain or domain.admin_password_plain,  # 优先使用 ldap_password
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
        from services.ldap_service import LdapService
        from ldap3 import Server, Connection, SIMPLE, ALL, Tls
        import ssl
        
        diagnosis_result = {
            'success': False,
            'ldap_port_status': False,
            'ldaps_port_status': False,
            'ldap_connection': False,
            'ldaps_connection': False,
            'issues': [],
            'suggestions': []
        }
        
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
        
        # 2. 测试 LDAP 连接
        try:
            server = Server(f"ldap://{domain.ldap_host}:{domain.ldap_port or 389}", get_info=ALL, connect_timeout=10)
            conn = Connection(server, user=domain.admin_dn, password=domain.ldap_password_plain, authentication=SIMPLE, auto_bind=False)
            
            if conn.bind():
                diagnosis_result['ldap_connection'] = True
                conn.unbind()
        except Exception as e:
            pass
        
        # 3. 测试 LDAPS 连接
        try:
            tls_context = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLS_CLIENT, ciphers='ALL:@SECLEVEL=0')
            server = Server(f"ldaps://{domain.ldap_host}:{domain.ldaps_port or 636}", get_info=ALL, tls=tls_context, connect_timeout=10)
            conn = Connection(server, user=domain.admin_dn, password=domain.ldap_password_plain, authentication=SIMPLE, auto_bind=False)
            
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


@admin_bp.route('/api/admin/domains', methods=['GET'])
@login_required
def get_domains():
    """获取所有域配置"""
    if session.get('user_role') != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    return jsonify({
        'success': True,
        'data': []
    })


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
            return '''
            <script>
                alert('请填写所有必填字段！');
                window.history.back();
            </script>
            '''
        
        # 创建域配置对象
        domain = Domain(
            name=name,
            ldap_host=ldap_host,
            ldap_port=ldap_port,
            base_dn=base_dn,
            admin_dn=admin_dn,
            is_active=True
        )
        
        # 保存密码 (加密存储，LDAP 连接时按需解密)
        domain.set_admin_password(admin_password)
        domain.set_ldap_password(admin_password)
        
        # 保存到数据库
        db.session.add(domain)
        db.session.commit()
        
        # 重定向到域列表页面
        from flask import redirect, url_for
        return redirect(url_for('admin.domains_page'))
        
    except Exception as e:
        db.session.rollback()
        return f'''
        <script>
            alert('保存失败：{str(e)}');
            window.history.back();
        </script>
        '''


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
        try:
            from services.ldap_service import LdapService
        except ImportError:
            from services.ldap_service_mock import LdapService
        
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
    
    print(f'[域配置更新] 域 {domain.name} 配置已更新')
    print(f'  ldap_hosts: {domain.ldap_hosts}')
    print(f'  use_ssl: {domain.use_ssl}')
    print(f'  ldap_port: {domain.ldap_port}')
    
    return jsonify({'success': True, 'message': '域配置更新成功'})




@admin_bp.route('/api/admin/sms-config', methods=['GET'])
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
                'access_secret': config.access_secret,
                'sign_name': config.sign_name,
                'template_code': config.template_code,
                'is_active': config.is_active
            }
        })
    else:
        return jsonify({'success': True, 'data': None})


@admin_bp.route('/api/admin/sms-config', methods=['POST'])
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
    
    if not all([access_key, access_secret, sign_name, template_code]):
        return jsonify({'success': False, 'message': '请填写完整的配置信息'}), 400
    
    # 保存或更新配置
    config = SmsConfig.query.first()
    
    if config:
        # 更新现有配置
        config.access_key = access_key
        config.access_secret = access_secret
        config.sign_name = sign_name
        config.template_code = template_code
        config.is_active = True
        action = 'sms_config_update'
        details = f'更新短信配置：签名={sign_name}, 模板={template_code}'
    else:
        # 创建新配置
        config = SmsConfig(
            access_key=access_key,
            access_secret=access_secret,
            sign_name=sign_name,
            template_code=template_code,
            is_active=True
        )
        db.session.add(config)
        action = 'sms_config_create'
        details = f'创建短信配置：签名={sign_name}, 模板={template_code}'
    
    db.session.commit()
    
    # 记录操作日志
    log_operation(action, details=details)
    
    return jsonify({'success': True, 'message': '短信配置保存成功'})


@admin_bp.route('/api/admin/sms-test', methods=['POST'])
@admin_required
def send_test_sms():
    """发送测试短信"""
    from models.models import SmsConfig, db
    try:
        from services.sms_service import SmsService
    except ImportError:
        from services.sms_service_mock import SmsService
    
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
        sms = SmsService()
        # 生成随机验证码
        import random
        code = str(random.randint(100000, 999999))
        
        # 这里调用实际的短信发送 API
        # 由于是测试，我们只返回成功消息
        result = sms.send_sms(phone, {'code': code})
        
        if result:
            return jsonify({
                'success': True,
                'message': f'测试短信已发送到 {phone}，验证码：{code}'
            })
        else:
            return jsonify({'success': False, 'message': '短信发送失败，请检查配置'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'发送失败：{str(e)}'}), 500


@admin_bp.route('/api/admin/logs', methods=['GET'])
@admin_required
def get_admin_logs():
    """获取管理日志"""
    from models.models import AdminLog, User, db
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    action_filter = request.args.get('action', '')
    username_filter = request.args.get('username', '')
    date_filter = request.args.get('date', '')
    
    # 构建查询
    query = AdminLog.query
    
    if action_filter:
        query = query.filter(AdminLog.action == action_filter)
    
    if username_filter:
        query = query.join(User).filter(User.username.like(f'%{username_filter}%'))
    
    if date_filter:
        from datetime import datetime
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d')
            query = query.filter(
                AdminLog.created_at >= date_obj,
                AdminLog.created_at < date_obj.replace(day=date_obj.day+1) if date_obj.day < 28 else date_obj
            )
        except:
            pass
    
    # 分页排序
    pagination = query.order_by(AdminLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    logs = []
    for log in pagination.items:
        admin_user = User.query.get(log.admin_id) if log.admin_id else None
        logs.append({
            'id': log.id,
            'admin_id': log.admin_id,
            'admin_username': admin_user.username if admin_user else 'Unknown',
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
        items = ['admin']
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

