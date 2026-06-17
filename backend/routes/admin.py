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
        <title>管理后台 - AD 密码管理系统</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                background: #f5f7fa;
                min-height: 100vh;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
        <div class="header">
            <h1>🔐 AD 密码管理系统 - 管理后台</h1>
            <div class="user-info">
                <span>欢迎，{{ username }}</span>
                <a href="/logout" class="logout-btn">退出登录</a>
            </div>
        </div>
        
        <div class="container">
            <div class="welcome-card">
                <h2>欢迎回来，{{ username }}！</h2>
                <p>这是 AD 密码管理系统的管理后台。您可以在这里管理域配置、用户信息、短信设置等。</p>
                
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
                <a href="/admin/users" class="menu-item">
                    <div class="menu-icon">👥</div>
                    <div class="menu-title">用户管理</div>
                </a>
                <a href="/admin/sms" class="menu-item">
                    <div class="menu-icon">💬</div>
                    <div class="menu-title">短信配置</div>
                </a>
                <a href="/admin/logs" class="menu-item">
                    <div class="menu-icon">📊</div>
                    <div class="menu-title">操作日志</div>
                </a>
                <a href="/admin/settings" class="menu-item">
                    <div class="menu-icon">⚙️</div>
                    <div class="menu-title">系统设置</div>
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
        <title>域配置管理 - AD 密码管理系统</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f5f7fa; }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
                color: #667eea;
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
                        <button onclick="showSyncUsersModal()" style="padding: 8px 16px; background: #67C23A; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block;">🔄 同步 AD 用户</button>
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
            
            // 显示同步用户信息模态框
            function showSyncUsersModal() {
                const modalHtml = `
                <div id="syncUsersModal" style="
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.5);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    z-index: 9999;
                ">
                    <div style="
                        background: white;
                        border-radius: 8px;
                        width: 80%;
                        max-width: 1000px;
                        max-height: 80vh;
                        overflow: auto;
                        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                    ">
                        <div style="
                            padding: 20px;
                            border-bottom: 1px solid #e0e0e0;
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                        ">
                            <h3 style="margin: 0; font-size: 18px;">🔄 同步 AD 用户信息</h3>
                            <button onclick="closeSyncUsersModal()" style="
                                background: none;
                                border: none;
                                font-size: 24px;
                                cursor: pointer;
                                color: #999;
                                padding: 0;
                                width: 30px;
                                height: 30px;
                                line-height: 30px;
                            ">&times;</button>
                        </div>
                        
                        <div style="padding: 20px;">
                            <div style="
                                padding: 15px;
                                background: #f0f7ff;
                                border-left: 4px solid #409EFF;
                                margin-bottom: 20px;
                                border-radius: 4px;
                            ">
                                <strong>💡 同步说明：</strong>
                                <ul style="margin: 10px 0 0 20px; padding: 0; color: #666;">
                                    <li>同步内容：邮箱、手机号码</li>
                                    <li>同步前会清空现有用户数据（保留 admin 账号）</li>
                                    <li>所有用户将从 AD 域重新导入</li>
                                    <li style="color: #E6A23C; font-weight: bold;">⚠️ 不设置密码，用户需使用 LDAP 认证登录</li>
                                </ul>
                            </div>
                            
                            <div id="syncLoading" style="display: none; text-align: center; padding: 40px;">
                                <div style="font-size: 48px; margin-bottom: 20px;">⏳</div>
                                <p style="font-size: 16px; color: #666;">正在从 AD 域获取用户信息，请稍候...</p>
                            </div>
                            
                            <div id="syncResult" style="display: none;"></div>
                            
                            <div id="userTableContainer" style="display: none;">
                                <h4 style="margin-bottom: 15px;">AD 用户信息（预览）</h4>
                                <table style="
                                    width: 100%;
                                    border-collapse: collapse;
                                    font-size: 14px;
                                ">
                                    <thead>
                                        <tr style="background: #f5f5f5;">
                                            <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: left;">用户名</th>
                                            <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: left;">邮箱</th>
                                            <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: left;">手机号码</th>
                                            <th style="padding: 12px; border: 1px solid #e0e0e0; text-align: center;">操作</th>
                                        </tr>
                                    </thead>
                                    <tbody id="userTableBody">
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        
                        <div style="
                            padding: 15px 20px;
                            border-top: 1px solid #e0e0e0;
                            display: flex;
                            justify-content: flex-end;
                            gap: 10px;
                        ">
                            <button onclick="closeSyncUsersModal()" style="
                                padding: 10px 20px;
                                background: #909399;
                                color: white;
                                border: none;
                                border-radius: 4px;
                                cursor: pointer;
                                font-size: 14px;
                            ">关闭</button>
                            <button onclick="executeSync()" id="syncBtn" style="
                                padding: 10px 20px;
                                background: #67C23A;
                                color: white;
                                border: none;
                                border-radius: 4px;
                                cursor: pointer;
                                font-size: 14px;
                            ">🔄 立即同步</button>
                        </div>
                    </div>
                </div>
                `;
                
                document.body.insertAdjacentHTML('beforeend', modalHtml);
                
                // 加载 AD 用户信息（从 LDAP）
                loadADUsersFromLDAP();
            }
            
            // 加载 AD 用户信息（从 LDAP）
            function loadADUsersFromLDAP() {
                const loading = document.getElementById('syncLoading');
                const userTableContainer = document.getElementById('userTableContainer');
                const syncResult = document.getElementById('syncResult');
                
                // 显示加载
                loading.style.display = 'block';
                userTableContainer.style.display = 'none';
                syncResult.style.display = 'none';
                
                // 调用预览 API（从 LDAP 获取）
                fetch('/admin/api/admin/users/preview')
                    .then(response => response.json())
                    .then(data => {
                        loading.style.display = 'none';
                        
                        if (data.success && data.data && data.data.length > 0) {
                            // 显示用户表格
                            renderUserTable(data.data);
                            userTableContainer.style.display = 'block';
                            
                            // 显示统计信息
                            syncResult.style.display = 'block';
                            syncResult.className = 'sync-result sync-success';
                            syncResult.innerHTML = `
                                <strong>✅ 从 AD 域获取到 ${data.total} 个用户</strong><br>
                                同步域：${data.domain_name || '当前域'}
                            `;
                            syncResult.style.cssText = `
                                padding: 15px;
                                background: #f0f9ff;
                                border-left: 4px solid #67C23A;
                                border-radius: 4px;
                                margin-bottom: 20px;
                            `;
                        } else {
                            // 无用户数据
                            userTableContainer.style.display = 'block';
                            document.getElementById('userTableBody').innerHTML = `
                                <tr>
                                    <td colspan="5" style="padding: 20px; text-align: center; color: #999;">
                                        暂无 AD 用户数据
                                    </td>
                                </tr>
                            `;
                            
                            syncResult.style.display = 'block';
                            syncResult.className = 'sync-result sync-error';
                            syncResult.innerHTML = `<strong>⚠️ 警告：</strong> 从 AD 域未获取到任何用户数据`;
                            syncResult.style.cssText = `
                                padding: 15px;
                                background: #fef0f0;
                                border-left: 4px solid #F56C6C;
                                border-radius: 4px;
                                margin-bottom: 20px;
                            `;
                        }
                    })
                    .catch(error => {
                        loading.style.display = 'none';
                        console.error('加载 AD 用户失败:', error);
                        
                        userTableContainer.style.display = 'block';
                        document.getElementById('userTableBody').innerHTML = `
                            <tr>
                                <td colspan="5" style="padding: 20px; text-align: center; color: #F56C6C;">
                                    加载失败：${error}
                                </td>
                            </tr>
                        `;
                        
                        syncResult.style.display = 'block';
                        syncResult.className = 'sync-result sync-error';
                        syncResult.innerHTML = `<strong>❌ 加载失败：</strong> ${error}`;
                        syncResult.style.cssText = `
                            padding: 15px;
                            background: #fef0f0;
                            border-left: 4px solid #F56C6C;
                            border-radius: 4px;
                            margin-bottom: 20px;
                        `;
                    });
            }
            
            // 关闭同步用户信息模态框
            function closeSyncUsersModal() {
                const modal = document.getElementById('syncUsersModal');
                if (modal) {
                    modal.remove();
                }
            }
            
            // 执行同步
            function executeSync() {
                const syncBtn = document.getElementById('syncBtn');
                const loading = document.getElementById('syncLoading');
                const syncResult = document.getElementById('syncResult');
                const userTableContainer = document.getElementById('userTableContainer');
                
                // 禁用按钮，显示加载
                syncBtn.disabled = true;
                syncBtn.innerHTML = '⏳ 同步中...';
                loading.style.display = 'block';
                syncResult.style.display = 'none';
                userTableContainer.style.display = 'none';
                
                fetch('/admin/api/admin/users/sync', {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    loading.style.display = 'none';
                    syncBtn.disabled = false;
                    syncBtn.innerHTML = '🔄 立即同步';
                    
                    syncResult.style.display = 'block';
                    
                    if (data.success) {
                        syncResult.className = 'sync-result sync-success';
                        syncResult.innerHTML = `
                            <strong>✅ 同步成功！</strong><br>
                            同步域：${data.data.domain_name || '当前域'}<br>
                            新增用户：${data.data.added || 0} 人<br>
                            删除用户：${data.data.deleted || 0} 人<br>
                            总用户数：${data.data.total || 0} 人
                        `;
                        syncResult.style.cssText = `
                            padding: 15px;
                            background: #f0f9ff;
                            border-left: 4px solid #67C23A;
                            border-radius: 4px;
                            margin-bottom: 20px;
                        `;
                        
                        // 加载用户列表并显示
                        loadUserListToTable();
                    } else {
                        syncResult.className = 'sync-result sync-error';
                        syncResult.innerHTML = `<strong>❌ 同步失败：</strong> ${data.message}`;
                        syncResult.style.cssText = `
                            padding: 15px;
                            background: #fef0f0;
                            border-left: 4px solid #F56C6C;
                            border-radius: 4px;
                            margin-bottom: 20px;
                        `;
                    }
                })
                .catch(error => {
                    loading.style.display = 'none';
                    syncBtn.disabled = false;
                    syncBtn.innerHTML = '🔄 立即同步';
                    
                    syncResult.style.display = 'block';
                    syncResult.className = 'sync-result sync-error';
                    syncResult.innerHTML = `<strong>❌ 同步出错：</strong> ${error}`;
                    syncResult.style.cssText = `
                        padding: 15px;
                        background: #fef0f0;
                        border-left: 4px solid #F56C6C;
                        border-radius: 4px;
                        margin-bottom: 20px;
                    `;
                });
            }
            
            // 加载用户列表到表格
            function loadUserListToTable() {
                fetch('/admin/api/admin/users/list')
                    .then(response => response.json())
                    .then(data => {
                        if (data.success && data.data && data.data.length > 0) {
                            renderUserTable(data.data);
                            document.getElementById('userTableContainer').style.display = 'block';
                        } else {
                            document.getElementById('userTableBody').innerHTML = `
                                <tr>
                                    <td colspan="5" style="padding: 20px; text-align: center; color: #999;">
                                        暂无用户数据
                                    </td>
                                </tr>
                            `;
                            document.getElementById('userTableContainer').style.display = 'block';
                        }
                    })
                    .catch(error => {
                        console.error('加载用户列表失败:', error);
                        document.getElementById('userTableBody').innerHTML = `
                            <tr>
                                <td colspan="5" style="padding: 20px; text-align: center; color: #F56C6C;">
                                    加载失败：${error}
                                </td>
                            </tr>
                        `;
                        document.getElementById('userTableContainer').style.display = 'block';
                    });
            }
            
            // 渲染用户表格
            function renderUserTable(users) {
                const tbody = document.getElementById('userTableBody');
                let html = '';
                
                users.forEach(user => {
                    html += `
                    <tr>
                        <td style="padding: 12px; border: 1px solid #e0e0e0;">
                            <strong>${user.username || '-'}</strong>
                        </td>
                        <td style="padding: 12px; border: 1px solid #e0e0e0;">
                            ${user.email || '-'}
                        </td>
                        <td style="padding: 12px; border: 1px solid #e0e0e0;">
                            ${user.phone || '-'}
                        </td>
                        <td style="padding: 12px; border: 1px solid #e0e0e0; text-align: center;">
                            <span style="color: #E6A23C; font-size: 12px; font-weight: bold;">⚠️ LDAP 认证</span>
                        </td>
                    </tr>
                    `;
                });
                
                tbody.innerHTML = html;
            }
            
            // 重置用户密码
            function resetUserPassword(username) {
                if (confirm(`确定要重置用户 "${username}" 的密码吗？`)) {
                    // 调用现有的重置密码 API
                    fetch(`/admin/api/admin/users/reset-password`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            username: username,
                            new_password: 'Ad@123456'
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert(`✅ 用户 "${username}" 的密码已重置为：Ad@123456`);
                        } else {
                            alert(`❌ 重置失败：${data.message}`);
                        }
                    })
                    .catch(error => {
                        alert(`❌ 重置出错：${error}`);
                    });
                }
            }
        </script>
    </body>
    </html>
    '''
    
    return render_template_string(html, username=username)


@admin_bp.route('/users')
@admin_required
def users_page():
    """用户管理页面"""
    username = session.get('username', '管理员')
    
    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>用户管理 - AD 密码管理系统</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f5f7fa; }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px 40px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .container { max-width: 1400px; margin: 0 auto; padding: 30px; }
            .back-btn { display: inline-block; margin-bottom: 20px; padding: 10px 20px; background: white; color: #667eea; text-decoration: none; border-radius: 4px; }
            .card { background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
            .toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .sync-btn { padding: 12px 24px; background: #409EFF; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
            .sync-btn:hover { background: #3a8ee6; }
            .sync-btn:disabled { background: #a0cfff; cursor: not-allowed; }
            .user-list { list-style: none; }
            .user-item { display: flex; justify-content: space-between; align-items: center; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 10px; }
            .user-info { display: flex; align-items: center; gap: 15px; }
            .user-avatar { width: 40px; height: 40px; border-radius: 50%; background: #667eea; color: white; display: flex; align-items: center; justify-content: center; font-size: 18px; }
            .user-details h4 { margin: 0 0 5px 0; color: #333; }
            .user-details p { margin: 0; color: #666; font-size: 14px; }
            .user-actions { display: flex; gap: 10px; }
            .btn { padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; }
            .btn-reset { background: #E6A23C; color: white; }
            .btn-delete { background: #F56C6C; color: white; }
            .empty-state { text-align: center; padding: 60px 20px; color: #999; }
            .empty-state-icon { font-size: 64px; margin-bottom: 20px; }
            .sync-result { margin-top: 20px; padding: 15px; border-radius: 4px; display: none; }
            .sync-success { background: #f0f9ff; border: 1px solid #67C23A; color: #67C23A; }
            .sync-error { background: #fef0f0; border: 1px solid #F56C6C; color: #F56C6C; }
            .loading { text-align: center; padding: 40px; color: #999; display: none; }
            .loading-spinner { border: 4px solid #f3f3f3; border-top: 4px solid #667eea; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 20px; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>👥 用户管理</h1>
            <div>
                <span style="margin-right: 15px;">{{ username }}</span>
                <a href="/logout" class="logout-btn">退出登录</a>
            </div>
        </div>
        
        <div class="container">
            <a href="/admin/dashboard" class="back-btn">← 返回管理后台</a>
            
            <div class="card">
                <div class="toolbar">
                    <h3 style="margin: 0;">用户列表</h3>
                    <button onclick="syncUsers()" class="sync-btn" id="syncBtn">🔄 同步 AD 用户</button>
                </div>
                
                <div id="loading" class="loading">
                    <div class="loading-spinner"></div>
                    <p>正在从 AD 服务器同步用户...</p>
                </div>
                
                <div id="syncResult" class="sync-result"></div>
                
                <ul class="user-list" id="userList">
                    <li class="empty-state">
                        <div class="empty-state-icon">👥</div>
                        <h2>暂无用户数据</h2>
                        <p>请点击上方"同步 AD 用户"按钮导入用户</p>
                    </li>
                </ul>
            </div>
        </div>
        
        <script>
            // 页面加载时获取用户列表
            document.addEventListener('DOMContentLoaded', function() {
                loadUserList();
            });
            
            // 加载用户列表
            function loadUserList() {
                fetch('/admin/api/admin/users/list')
                    .then(response => response.json())
                    .then(data => {
                        if (data.success && data.data && data.data.length > 0) {
                            renderUserList(data.data);
                        } else {
                            showEmptyState();
                        }
                    })
                    .catch(error => {
                        console.error('加载用户列表失败:', error);
                        showEmptyState();
                    });
            }
            
            // 渲染用户列表
            function renderUserList(users) {
                const container = document.getElementById('userList');
                let html = '';
                
                users.forEach(user => {
                    const firstLetter = user.username.charAt(0).toUpperCase();
                    const displayName = user.display_name || user.username;
                    const phone = user.phone || '暂无手机号';
                    const mfaStatus = user.mfa_enabled ? '<span style="color:#67C23A;">✅ 已启用</span>' : '<span style="color:#909399;">❌ 未启用</span>';
                    
                    html += `
                    <li class="user-item">
                        <div class="user-info">
                            <div class="user-avatar">${firstLetter}</div>
                            <div class="user-details">
                                <h4>${displayName} (${user.username})</h4>
                                <p>${user.email || '暂无邮箱'}</p>
                                <p style="font-size: 12px; color: #666; margin-top: 3px;">
                                    📱 ${phone} 
                                    <a href="javascript:void(0)" onclick="editPhone(${user.id}, '${user.username}', '${user.phone || ''}')" 
                                       style="margin-left:10px; color:#409EFF; text-decoration:none;">[修改]</a>
                                </p>
                                <p style="font-size: 12px; margin-top: 5px;">
                                    🛡️ MFA 认证：${mfaStatus}
                                </p>
                                <p style="font-size: 12px; color: #999; margin-top: 5px;">
                                    同步时间：${user.last_sync || '从未同步'}
                                </p>
                            </div>
                        </div>
                        <div class="user-actions">
                            <button onclick="resetPassword('${user.username}')" class="btn btn-reset">🔑 重置密码</button>
                            <button onclick="deleteUser(${user.id})" class="btn btn-delete">🗑️ 删除</button>
                        </div>
                    </li>
                    `;
                });
                
                container.innerHTML = html;
            }
            
            // 显示空状态
            function showEmptyState() {
                document.getElementById('userList').innerHTML = `
                    <li class="empty-state">
                        <div class="empty-state-icon">👥</div>
                        <h2>暂无用户数据</h2>
                        <p>请点击上方"同步 AD 用户"按钮导入用户</p>
                    </li>
                `;
            }
            
            // 同步 AD 用户
            function syncUsers() {
                const syncBtn = document.getElementById('syncBtn');
                const loading = document.getElementById('loading');
                const syncResult = document.getElementById('syncResult');
                
                // 禁用按钮，显示加载
                syncBtn.disabled = true;
                syncBtn.innerHTML = '⏳ 同步中...';
                loading.style.display = 'block';
                syncResult.style.display = 'none';
                
                fetch('/admin/api/admin/users/sync', {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    loading.style.display = 'none';
                    syncBtn.disabled = false;
                    syncBtn.innerHTML = '🔄 同步 AD 用户';
                    
                    syncResult.style.display = 'block';
                    
                    if (data.success) {
                        syncResult.className = 'sync-result sync-success';
                        syncResult.innerHTML = `
                            <strong>✅ 同步成功！</strong><br>
                            同步域：${data.data.domain_name || '当前域'}<br>
                            新增用户：${data.data.added || 0} 人<br>
                            更新用户：${data.data.updated || 0} 人<br>
                            删除用户：${data.data.deleted || 0} 人<br>
                            总用户数：${data.data.total || 0} 人
                        `;
                        // 刷新用户列表
                        loadUserList();
                    } else {
                        syncResult.className = 'sync-result sync-error';
                        syncResult.innerHTML = `<strong>❌ 同步失败：</strong> ${data.message}`;
                    }
                })
                .catch(error => {
                    loading.style.display = 'none';
                    syncBtn.disabled = false;
                    syncBtn.innerHTML = '🔄 同步 AD 用户';
                    
                    syncResult.style.display = 'block';
                    syncResult.className = 'sync-result sync-error';
                    syncResult.innerHTML = `<strong>❌ 同步出错：</strong> ${error}`;
                });
            }
            
            // 重置密码 - 显示模态框
            function resetPassword(username) {
                // 创建模态框 HTML
                const modalHtml = `
                <div id="resetPasswordModal" style="
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0,0,0,0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 9999;
                ">
                    <div style="
                        background: white;
                        padding: 30px;
                        border-radius: 8px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                        width: 400px;
                        max-width: 90%;
                    ">
                        <h3 style="margin: 0 0 20px 0; color: #333; font-size: 18px;">
                            🔑 重置用户密码
                        </h3>
                        <p style="margin: 0 0 20px 0; color: #666;">
                            用户：<strong style="color: #409EFF;">${username}</strong>
                        </p>
                        
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; color: #333; font-weight: 500;">
                                新密码 <span style="color: #F56C6C;">*</span>
                            </label>
                            <input type="password" id="newPassword" placeholder="请输入新密码（至少 6 位）" style="
                                width: 100%;
                                padding: 10px;
                                border: 1px solid #dcdfe6;
                                border-radius: 4px;
                                font-size: 14px;
                                outline: none;
                                box-sizing: border-box;
                            " onfocus="this.style.borderColor='#409EFF'" onblur="this.style.borderColor='#dcdfe6'">
                        </div>
                        
                        <div style="margin-bottom: 20px;">
                            <label style="display: block; margin-bottom: 5px; color: #333; font-weight: 500;">
                                确认密码 <span style="color: #F56C6C;">*</span>
                            </label>
                            <input type="password" id="confirmPassword" placeholder="请再次输入新密码" style="
                                width: 100%;
                                padding: 10px;
                                border: 1px solid #dcdfe6;
                                border-radius: 4px;
                                font-size: 14px;
                                outline: none;
                                box-sizing: border-box;
                            " onfocus="this.style.borderColor='#409EFF'" onblur="this.style.borderColor='#dcdfe6'">
                        </div>
                        
                        <div style="display: flex; gap: 10px; justify-content: flex-end;">
                            <button onclick="closeResetPasswordModal()" style="
                                padding: 8px 20px;
                                border: 1px solid #dcdfe6;
                                background: white;
                                color: #606266;
                                border-radius: 4px;
                                cursor: pointer;
                                font-size: 14px;
                            ">取消</button>
                            <button onclick="submitResetPassword('${username}')" style="
                                padding: 8px 20px;
                                background: #409EFF;
                                color: white;
                                border: none;
                                border-radius: 4px;
                                cursor: pointer;
                                font-size: 14px;
                            ">确定</button>
                        </div>
                    </div>
                </div>
                `;
                
                // 添加到页面
                const existingModal = document.getElementById('resetPasswordModal');
                if (existingModal) {
                    existingModal.remove();
                }
                document.body.insertAdjacentHTML('beforeend', modalHtml);
                
                // 聚焦到第一个输入框
                setTimeout(() => {
                    document.getElementById('newPassword').focus();
                }, 100);
                
                // 支持回车键提交
                document.getElementById('confirmPassword').addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        submitResetPassword(username);
                    }
                });
            }
            
            // 关闭重置密码模态框
            function closeResetPasswordModal() {
                const modal = document.getElementById('resetPasswordModal');
                if (modal) {
                    modal.remove();
                }
            }
            
            // 提交重置密码
            function submitResetPassword(username) {
                const newPassword = document.getElementById('newPassword').value;
                const confirmPassword = document.getElementById('confirmPassword').value;
                
                // 验证
                if (!newPassword) {
                    alert('请输入新密码！');
                    document.getElementById('newPassword').focus();
                    return;
                }
                
                if (newPassword.length < 6) {
                    alert('密码长度至少 6 位！');
                    document.getElementById('newPassword').focus();
                    return;
                }
                
                if (newPassword !== confirmPassword) {
                    alert('两次输入的密码不一致！');
                    document.getElementById('confirmPassword').focus();
                    return;
                }
                
                // 调用 API
                fetch(`/admin/api/admin/users/username/${username}/reset-password`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ password: newPassword })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(`✅ 密码重置成功！`);
                        closeResetPasswordModal();
                    } else {
                        alert(`❌ 密码重置失败：${data.message}`);
                    }
                })
                .catch(error => {
                    alert(`❌ 密码重置出错：${error}`);
                });
            }
            
            // 删除用户
            function deleteUser(userId) {
                if (confirm('确定要删除此用户吗？')) {
                    fetch(`/admin/api/admin/users/${userId}`, {
                        method: 'DELETE'
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert('删除成功');
                            loadUserList();
                        } else {
                            alert('删除失败：' + data.message);
                        }
                    })
                    .catch(error => {
                        alert('删除出错：' + error);
                    });
                }
            }
            
            // 修改手机号
            function editPhone(userId, username, currentPhone) {
                const modalHtml = `
                <div id="editPhoneModal" style="
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0,0,0,0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 9999;
                ">
                    <div style="
                        background: white;
                        padding: 30px;
                        border-radius: 8px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                        width: 400px;
                        max-width: 90%;
                    ">
                        <h3 style="margin: 0 0 20px 0; color: #333; font-size: 18px;">
                            📱 修改手机号
                        </h3>
                        <p style="margin: 0 0 20px 0; color: #666;">
                            用户：<strong style="color: #409EFF;">${username}</strong>
                        </p>
                        <div style="margin-bottom: 20px;">
                            <label style="display: block; margin-bottom: 8px; color: #333; font-weight: bold;">新手机号</label>
                            <input type="tel" id="newPhoneInput" placeholder="请输入新手机号" 
                                   style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;"
                                   value="${currentPhone || ''}">
                        </div>
                        <div style="text-align: right;">
                            <button onclick="closeEditPhoneModal()" 
                                style="padding: 8px 16px; margin-right: 10px; border: none; background: #eee; border-radius: 4px; cursor: pointer;">
                                取消
                            </button>
                            <button onclick="submitEditPhone(${userId})" 
                                style="padding: 8px 16px; border: none; background: #409EFF; color: white; border-radius: 4px; cursor: pointer;">
                                确定
                            </button>
                        </div>
                    </div>
                </div>
                `;
                
                document.body.insertAdjacentHTML('beforeend', modalHtml);
            }
            
            // 关闭修改手机号弹窗
            function closeEditPhoneModal() {
                const modal = document.getElementById('editPhoneModal');
                if (modal) {
                    modal.remove();
                }
            }
            
            // 提交修改手机号
            function submitEditPhone(userId) {
                const newPhone = document.getElementById('newPhoneInput').value.trim();
                
                if (!newPhone) {
                    alert('请输入手机号');
                    return;
                }
                
                // 简单的手机号验证（11 位数字）
                if (!/^\d{11}$/.test(newPhone)) {
                    alert('请输入有效的 11 位手机号');
                    return;
                }
                
                fetch(`/admin/api/admin/users/${userId}/phone`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({phone: newPhone})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('✅ 手机号修改成功');
                        closeEditPhoneModal();
                        loadUserList();
                    } else {
                        alert('❌ 修改失败：' + data.message);
                    }
                })
                .catch(error => {
                    alert('❌ 请求出错：' + error);
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
        <title>短信配置 - AD 密码管理系统</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f5f7fa; }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px 40px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .container { max-width: 1000px; margin: 0 auto; padding: 30px; }
            .back-btn { display: inline-block; margin-bottom: 20px; padding: 10px 20px; background: white; color: #667eea; text-decoration: none; border-radius: 4px; }
            .card { background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
            .card-title { font-size: 20px; color: #333; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #eee; }
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 8px; color: #333; font-weight: 500; }
            .form-group input { width: 100%; padding: 12px 15px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
            .form-group input:focus { outline: none; border-color: #667eea; }
            .form-group small { display: block; margin-top: 5px; color: #999; font-size: 12px; }
            .btn { padding: 12px 30px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }
            .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
            .btn-primary:hover { opacity: 0.9; }
            .btn-test { background: #67C23A; color: white; margin-left: 10px; }
            .form-actions { margin-top: 30px; text-align: right; }
            .status-badge { display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 12px; margin-left: 10px; }
            .status-active { background: #67C23A; color: white; }
            .status-inactive { background: #909399; color: white; }
        </style>
    </head>
    <body>
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
                        <input type="text" id="signName" name="sign_name" required placeholder="请输入短信签名，如：AD 密码管理系统">
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
        <title>操作日志 - AD 密码管理系统</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f5f7fa; }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px 40px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .container { max-width: 1400px; margin: 0 auto; padding: 30px; }
            .back-btn { display: inline-block; margin-bottom: 20px; padding: 10px 20px; background: white; color: #667eea; text-decoration: none; border-radius: 4px; }
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
            .pagination button.active { background: #667eea; color: white; border-color: #667eea; }
            .pagination button:disabled { background: #f5f5f5; cursor: not-allowed; }
            .filter-form { display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }
            .filter-form select, .filter-form input { padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; }
            .btn { padding: 8px 15px; border: none; border-radius: 4px; cursor: pointer; }
            .btn-primary { background: #667eea; color: white; }
            .empty-state { text-align: center; padding: 60px 20px; color: #999; }
            .empty-state-icon { font-size: 64px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
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
                        <option value="mfa_enable">MFA 启用</option>
                        <option value="mfa_disable">MFA 禁用</option>
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
                    'mfa_enable': 'badge-system',
                    'mfa_disable': 'badge-system'
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
                    'mfa_enable': 'MFA 启用',
                    'mfa_disable': 'MFA 禁用'
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


@admin_bp.route('/settings')
@admin_required
def settings_page():
    """系统设置页面"""
    username = session.get('username', '管理员')
    
    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>系统设置 - AD 密码管理系统</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f5f7fa; }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px 40px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .container { max-width: 1400px; margin: 0 auto; padding: 30px; }
            .back-btn { display: inline-block; margin-bottom: 20px; padding: 10px 20px; background: white; color: #667eea; text-decoration: none; border-radius: 4px; }
            .card { background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
            .card-title { font-size: 20px; color: #333; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #eee; }
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 8px; color: #333; font-weight: 500; }
            .form-group input[type="text"], .form-group input[type="number"], .form-group input[type="email"], .form-group select { width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
            .form-group input[type="checkbox"] { width: auto; margin-right: 8px; }
            .form-group small { display: block; margin-top: 5px; color: #999; font-size: 12px; }
            .checkbox-group { display: flex; align-items: center; padding: 10px 0; }
            .btn { padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
            .btn-primary { background: #667eea; color: white; }
            .btn-primary:hover { background: #5568d3; }
            .btn-secondary { background: #6c757d; color: white; margin-left: 10px; }
            .section-title { font-size: 16px; color: #667eea; margin: 20px 0 15px 0; padding-left: 10px; border-left: 3px solid #667eea; }
            .save-bar { position: sticky; bottom: 0; background: white; padding: 15px 30px; border-top: 1px solid #eee; display: flex; justify-content: flex-end; box-shadow: 0 -2px 10px rgba(0,0,0,0.05); }
            .toast { position: fixed; top: 20px; right: 20px; padding: 15px 25px; border-radius: 4px; color: white; z-index: 10000; display: none; }
            .toast-success { background: #52c41a; }
            .toast-error { background: #f5222d; }
            
            /* 数据库配置样式优化 */
            .db-select {
                background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
                border: 2px solid #e8ecef;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                transition: all 0.3s ease;
                cursor: pointer;
            }
            .db-select:hover {
                border-color: #667eea;
                background: linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%);
            }
            .db-select:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            .db-input {
                border: 2px solid #e8ecef;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                transition: all 0.3s ease;
            }
            .db-input:hover {
                border-color: #a0aec0;
            }
            .db-input:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            .form-row {
                display: flex;
                gap: 20px;
                margin-bottom: 20px;
            }
            .label-icon {
                display: inline-block;
                margin-right: 6px;
                font-size: 16px;
            }
            .help-text {
                color: #909399;
                font-size: 12px;
                margin-top: 6px;
                display: block;
                font-style: italic;
            }
            .db-input-full {
                width: 100% !important;
            }
            .test-connection-section {
                display: flex;
                align-items: center;
                gap: 15px;
                margin-top: 25px;
                padding-top: 20px;
                border-top: 1px dashed #e8ecef;
            }
            .btn-test {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 12px 28px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .btn-test:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
            }
            .btn-test:active {
                transform: translateY(0);
            }
            .btn-icon {
                font-size: 16px;
            }
            .test-result {
                flex: 1;
                font-size: 14px;
                font-weight: 500;
                min-height: 20px;
            }
            .connection-status-section {
                margin-top: 25px;
            }
            .status-title {
                font-size: 15px;
                color: #333;
                margin-bottom: 12px;
                font-weight: 600;
            }
            .connection-status {
                padding: 20px;
                border-radius: 10px;
                border: 2px solid;
                transition: all 0.3s ease;
            }
            .connection-status.status-empty {
                background: linear-gradient(135deg, #f8f9fa 0%, #fafbfc 100%);
                border-color: #e8ecef;
            }
            .connection-status.status-success {
                background: linear-gradient(135deg, #f0f9ff 0%, #e6f7ff 100%);
                border-color: #1890ff;
            }
            .connection-status.status-error {
                background: linear-gradient(135deg, #fff1f0 0%, #fff2f0 100%);
                border-color: #ff4d4f;
            }
            .status-content {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .status-icon {
                font-size: 20px;
            }
            .status-text {
                font-size: 14px;
                color: #666;
            }
            .connection-status.status-success .status-text {
                color: #1890ff;
                font-weight: 500;
            }
            .connection-status.status-error .status-text {
                color: #ff4d4f;
                font-weight: 500;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>⚙️ 系统设置</h1>
            <div>
                <span style="margin-right: 15px;">{{ username }}</span>
                <a href="/logout" class="logout-btn">退出登录</a>
            </div>
        </div>
        
        <div class="container">
            <a href="/admin/dashboard" class="back-btn">← 返回管理后台</a>
            
            <form id="settingsForm" onsubmit="return false;">
                <div class="card">
                    <h2 class="card-title">基本设置</h2>
                    
                    <div class="form-group">
                        <label for="system_name">系统名称</label>
                        <input type="text" id="system_name" name="system_name" placeholder="AD 密码管理系统" />
                        <small>显示在页面标题和登录页的系统名称</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="session_timeout">会话超时时间（分钟）</label>
                        <input type="number" id="session_timeout" name="session_timeout" min="5" max="1440" value="30" />
                        <small>用户无操作后自动登出的时间，范围 5-1440 分钟</small>
                    </div>
                </div>
                
                <div class="card">
                    <h2 class="card-title">密码策略</h2>
                    
                    <div class="form-group">
                        <label for="password_min_length">最小密码长度</label>
                        <input type="number" id="password_min_length" name="password_min_length" min="6" max="128" value="8" />
                        <small>用户密码的最小长度要求</small>
                    </div>
                    
                    <div class="section-title">复杂度要求</div>
                    
                    <div class="checkbox-group">
                        <input type="checkbox" id="password_require_uppercase" name="password_require_uppercase" checked />
                        <label for="password_require_uppercase">必须包含大写字母 (A-Z)</label>
                    </div>
                    
                    <div class="checkbox-group">
                        <input type="checkbox" id="password_require_lowercase" name="password_require_lowercase" checked />
                        <label for="password_require_lowercase">必须包含小写字母 (a-z)</label>
                    </div>
                    
                    <div class="checkbox-group">
                        <input type="checkbox" id="password_require_number" name="password_require_number" checked />
                        <label for="password_require_number">必须包含数字 (0-9)</label>
                    </div>
                    
                    <div class="checkbox-group">
                        <input type="checkbox" id="password_require_special" name="password_require_special" checked />
                        <label for="password_require_special">必须包含特殊字符 (!@#$%^&* 等)</label>
                    </div>
                </div>
                
                <div class="card">
                    <h2 class="card-title">安全设置</h2>
                    
                    <div class="checkbox-group">
                        <input type="checkbox" id="mfa_required" name="mfa_required" />
                        <label for="mfa_required">强制要求 MFA（所有用户必须绑定 Microsoft Authenticator）</label>
                    </div>
                    
                    <div class="checkbox-group">
                        <input type="checkbox" id="enable_sms_verify" name="enable_sms_verify" checked />
                        <label for="enable_sms_verify">启用短信验证功能</label>
                    </div>
                </div>
                
                <div class="card">
                    <h2 class="card-title">🔌 系统端口配置</h2>
                    
                    <div class="form-group">
                        <label for="system_port"><span class="label-icon">🌐</span> 系统服务端口</label>
                        <input type="number" id="system_port" name="system_port" min="1" max="65535" value="5000" />
                        <small class="help-text">💡 修改端口后需要重启服务，Web 访问将使用新端口（如 http://127.0.0.1:新端口）</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="system_host"><span class="label-icon">🖥️</span> 监听地址</label>
                        <input type="text" id="system_host" name="system_host" placeholder="0.0.0.0" value="0.0.0.0" />
                        <small class="help-text">💡 0.0.0.0 表示监听所有网卡，127.0.0.1 表示仅本地访问</small>
                    </div>
                    
                    <div class="connection-status-section">
                        <h4 class="status-title"><span class="label-icon">📊</span> 当前服务状态</h4>
                        <div id="service_status" class="connection-status status-success">
                            <div class="status-content">
                                <span class="status-icon">✅</span>
                                <div style="flex: 1;">
                                    <div style="color: #1890ff; font-weight: 600; margin-bottom: 8px; font-size: 15px;">
                                        服务运行中
                                    </div>
                                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 13px; color: #666;">
                                        <div><span style="color: #999;">当前端口：</span><strong id="current_port">5000</strong></div>
                                        <div><span style="color: #999;">监听地址：</span><strong id="current_host">0.0.0.0</strong></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h2 class="card-title">🗄️ 数据库配置</h2>
                    
                    <div class="form-group">
                        <label for="db_type"><span class="label-icon">📊</span> 数据库类型</label>
                        <select id="db_type" onchange="updateDefaultPort()" class="db-select">
                            <option value="mysql">🐬 MySQL</option>
                            <option value="pgsql">🐘 PostgreSQL</option>
                            <option value="sqlserver">🖥️ SQL Server</option>
                        </select>
                        <small class="help-text">💡 选择数据库类型，端口会自动填充默认值</small>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group" style="flex: 2;">
                            <label for="db_host"><span class="label-icon">🌐</span> 数据库主机地址</label>
                            <input type="text" id="db_host" class="db-input" placeholder="例如：192.168.1.100 或 db.example.com" />
                        </div>
                        
                        <div class="form-group" style="flex: 1;">
                            <label for="db_port"><span class="label-icon">🔌</span> 端口</label>
                            <input type="number" id="db_port" class="db-input" placeholder="3306" />
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="db_database"><span class="label-icon">📁</span> 数据库名称</label>
                        <input type="text" id="db_database" class="db-input" placeholder="ad_system" />
                    </div>
                    
                    <div class="form-group">
                        <label for="db_username"><span class="label-icon">👤</span> 用户名</label>
                        <input type="text" id="db_username" class="db-input db-input-full" placeholder="root" />
                    </div>
                    
                    <div class="form-group">
                        <label for="db_password"><span class="label-icon">🔐</span> 密码</label>
                        <input type="password" id="db_password" class="db-input db-input-full" placeholder="请输入数据库密码" />
                        <small class="help-text">💡 留空表示保持原有密码不变</small>
                    </div>
                    
                    <div class="test-connection-section">
                        <button type="button" class="btn btn-test" onclick="testDatabaseConnection()">
                            <span class="btn-icon">🔍</span> 测试连接
                        </button>
                        <div id="db_test_result" class="test-result"></div>
                    </div>
                    
                    <div class="connection-status-section">
                        <h4 class="status-title"><span class="label-icon">📊</span> 连接状态</h4>
                        <div id="db_connection_status" class="connection-status status-empty">
                            <div class="status-content">
                                <span class="status-icon">💡</span>
                                <span class="status-text">尚未配置数据库连接</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="save-bar">
                    <button type="button" class="btn btn-secondary" onclick="loadSettings()">重置</button>
                    <button type="submit" class="btn btn-primary" onclick="saveSettings()">💾 保存设置</button>
                </div>
            </form>
        </div>
        
        <div id="toast" class="toast"></div>
        
        <script>
            // 加载系统设置
            function loadSettings() {
                fetch('/admin/api/settings')
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            fillSettings(data.data);
                        } else {
                            showToast('加载设置失败：' + data.message, 'error');
                        }
                    })
                    .catch(err => {
                        console.error('加载设置失败:', err);
                        showToast('加载设置失败：网络错误', 'error');
                    });
            }
            
            // 填充表单数据
            function fillSettings(settings) {
                const getValue = (key, defaultVal) => {
                    const setting = settings.find(s => s.setting_key === key);
                    if (!setting) return defaultVal;
                    
                    if (setting.setting_type === 'boolean') {
                        return setting.setting_value === 'true';
                    } else if (setting.setting_type === 'integer') {
                        return parseInt(setting.setting_value) || defaultVal;
                    }
                    return setting.setting_value || defaultVal;
                };
                
                // 基本设置
                document.getElementById('system_name').value = getValue('system_name', 'AD 密码管理系统');
                document.getElementById('session_timeout').value = getValue('session_timeout', 30);
                
                // 密码策略
                document.getElementById('password_min_length').value = getValue('password_min_length', 8);
                document.getElementById('password_require_uppercase').checked = getValue('password_require_uppercase', true);
                document.getElementById('password_require_lowercase').checked = getValue('password_require_lowercase', true);
                document.getElementById('password_require_number').checked = getValue('password_require_number', true);
                document.getElementById('password_require_special').checked = getValue('password_require_special', true);
                
                // 安全设置
                document.getElementById('mfa_required').checked = getValue('mfa_required', false);
                document.getElementById('enable_sms_verify').checked = getValue('enable_sms_verify', true);
                
                // 系统端口配置
                document.getElementById('system_port').value = getValue('system_port', 5000);
                document.getElementById('system_host').value = getValue('system_host', '0.0.0.0');
                
                // 更新当前服务状态显示
                updateServiceStatus();
                
                // 加载数据库配置
                loadDatabaseConfig();
            }
            
            // 更新服务状态显示
            function updateServiceStatus() {
                const port = document.getElementById('system_port').value || '5000';
                const host = document.getElementById('system_host').value || '0.0.0.0';
                document.getElementById('current_port').textContent = port;
                document.getElementById('current_host').textContent = host;
            }
            
            // 加载服务状态
            function loadServiceStatus() {
                fetch('/admin/api/service/status')
                    .then(r => r.json())
                    .then(data => {
                        if (data.success && data.data) {
                            const status = data.data;
                            document.getElementById('current_port').textContent = status.port || '5000';
                            document.getElementById('current_host').textContent = status.host || '0.0.0.0';
                        }
                    })
                    .catch(err => {
                        console.error('加载服务状态失败:', err);
                    });
            }
            
            // 加载数据库配置
            function loadDatabaseConfig() {
                fetch('/admin/api/database/config')
                    .then(r => r.json())
                    .then(data => {
                        if (data.success && data.data) {
                            const config = data.data;
                            document.getElementById('db_type').value = config.type || 'mysql';
                            document.getElementById('db_host').value = config.host || '';
                            document.getElementById('db_port').value = config.port || '';
                            document.getElementById('db_database').value = config.database || '';
                            document.getElementById('db_username').value = config.username || '';
                            document.getElementById('db_password').value = ''; // 密码不回填
                            
                            // 更新连接状态显示
                            updateConnectionStatus(true, config);
                        } else {
                            updateConnectionStatus(false, null);
                        }
                    })
                    .catch(err => {
                        console.error('加载数据库配置失败:', err);
                        updateConnectionStatus(false, null);
                    });
            }
            
            // 更新默认端口
            function updateDefaultPort() {
                const dbType = document.getElementById('db_type').value;
                const portInput = document.getElementById('db_port');
                
                const defaultPorts = {
                    'mysql': 3306,
                    'pgsql': 5432,
                    'sqlserver': 1433
                };
                
                if (!portInput.value || portInput.value === '') {
                    portInput.value = defaultPorts[dbType] || '';
                }
            }
            
            // 测试数据库连接
            function testDatabaseConnection() {
                const config = {
                    type: document.getElementById('db_type').value,
                    host: document.getElementById('db_host').value,
                    port: document.getElementById('db_port').value,
                    database: document.getElementById('db_database').value,
                    username: document.getElementById('db_username').value,
                    password: document.getElementById('db_password').value
                };
                
                // 验证必填字段
                if (!config.host || !config.database || !config.username) {
                    showToast('请填写完整的数据库配置信息', 'error');
                    return;
                }
                
                const resultDiv = document.getElementById('db_test_result');
                resultDiv.innerHTML = '<span style="color: #666;">⏳ 正在测试连接...</span>';
                
                fetch('/admin/api/database/test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        resultDiv.innerHTML = '<span style="color: #52c41a;">✓ ' + data.message + '</span>';
                        updateConnectionStatus(true, config);
                        showToast(data.message, 'success');
                    } else {
                        resultDiv.innerHTML = '<span style="color: #f5222d;">✗ ' + data.message + '</span>';
                        updateConnectionStatus(false, null);
                        showToast('连接测试失败：' + data.message, 'error');
                    }
                })
                .catch(err => {
                    resultDiv.innerHTML = '<span style="color: #f5222d;">✗ 网络错误</span>';
                    console.error('测试连接失败:', err);
                    showToast('测试连接失败：网络错误', 'error');
                });
            }
            
            // 更新连接状态显示
            function updateConnectionStatus(connected, config) {
                const statusDiv = document.getElementById('db_connection_status');
                
                if (connected && config) {
                    const dbNames = {
                        'mysql': '🐬 MySQL',
                        'pgsql': '🐘 PostgreSQL',
                        'sqlserver': '🖥️ SQL Server'
                    };
                    const dbName = dbNames[config.type] || config.type;
                    
                    statusDiv.className = 'connection-status status-success';
                    statusDiv.innerHTML = `
                        <div class="status-content">
                            <span class="status-icon">✅</span>
                            <div style="flex: 1;">
                                <div style="color: #1890ff; font-weight: 600; margin-bottom: 8px; font-size: 15px;">
                                    已配置数据库连接
                                </div>
                                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 13px; color: #666;">
                                    <div><span style="color: #999;">类型：</span><strong>${dbName}</strong></div>
                                    <div><span style="color: #999;">主机：</span><strong>${config.host}:${config.port}</strong></div>
                                    <div><span style="color: #999;">数据库：</span><strong>${config.database}</strong></div>
                                    <div><span style="color: #999;">用户：</span><strong>${config.username}</strong></div>
                                </div>
                            </div>
                        </div>
                    `;
                } else {
                    statusDiv.className = 'connection-status status-empty';
                    statusDiv.innerHTML = `
                        <div class="status-content">
                            <span class="status-icon">💡</span>
                            <span class="status-text">尚未配置数据库连接</span>
                        </div>
                    `;
                }
            }
            
            // 保存系统设置
            function saveSettings() {
                const settings = [
                    { key: 'system_name', value: document.getElementById('system_name').value, type: 'string' },
                    { key: 'session_timeout', value: document.getElementById('session_timeout').value, type: 'integer' },
                    { key: 'password_min_length', value: document.getElementById('password_min_length').value, type: 'integer' },
                    { key: 'password_require_uppercase', value: document.getElementById('password_require_uppercase').checked ? 'true' : 'false', type: 'boolean' },
                    { key: 'password_require_lowercase', value: document.getElementById('password_require_lowercase').checked ? 'true' : 'false', type: 'boolean' },
                    { key: 'password_require_number', value: document.getElementById('password_require_number').checked ? 'true' : 'false', type: 'boolean' },
                    { key: 'password_require_special', value: document.getElementById('password_require_special').checked ? 'true' : 'false', type: 'boolean' },
                    { key: 'mfa_required', value: document.getElementById('mfa_required').checked ? 'true' : 'false', type: 'boolean' },
                    { key: 'enable_sms_verify', value: document.getElementById('enable_sms_verify').checked ? 'true' : 'false', type: 'boolean' },
                    { key: 'system_port', value: document.getElementById('system_port').value, type: 'integer' },
                    { key: 'system_host', value: document.getElementById('system_host').value, type: 'string' }
                ];
                
                // 先保存系统设置
                fetch('/admin/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ settings: settings })
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        // 然后保存数据库配置
                        return saveDatabaseConfig();
                    } else {
                        showToast('设置保存失败：' + data.message, 'error');
                        throw new Error(data.message);
                    }
                })
                .then(dbResult => {
                    if (dbResult && dbResult.success) {
                        showToast('所有设置保存成功！', 'success');
                        logOperation('system_settings_update', '更新系统设置和数据库配置');
                    } else if (dbResult) {
                        showToast('系统设置保存成功，但数据库配置失败：' + dbResult.message, 'error');
                    } else {
                        showToast('设置保存成功！', 'success');
                        logOperation('system_settings_update', '更新系统设置');
                    }
                })
                .catch(err => {
                    console.error('保存设置失败:', err);
                    showToast('保存设置失败：' + err.message, 'error');
                });
            }
            
            // 保存数据库配置
            function saveDatabaseConfig() {
                const config = {
                    type: document.getElementById('db_type').value,
                    host: document.getElementById('db_host').value,
                    port: document.getElementById('db_port').value,
                    database: document.getElementById('db_database').value,
                    username: document.getElementById('db_username').value,
                    password: document.getElementById('db_password').value
                };
                
                // 如果没有填写密码且已有配置，则使用原有密码（不测试）
                // 如果有新密码或新配置，则自动测试连接
                return fetch('/admin/api/database/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        return data;
                    } else {
                        throw new Error(data.message);
                    }
                });
            }
            
            // 显示提示消息
            function showToast(message, type) {
                const toast = document.getElementById('toast');
                toast.textContent = message;
                toast.className = 'toast toast-' + type;
                toast.style.display = 'block';
                setTimeout(() => { toast.style.display = 'none'; }, 3000);
            }
            
            // 记录操作日志
            function logOperation(action, details) {
                fetch('/admin/api/log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: action, details: details })
                }).catch(err => console.error('记录日志失败:', err));
            }
            
            // 页面加载时获取设置
            document.addEventListener('DOMContentLoaded', function() {
                loadSettings();
                loadServiceStatus(); // 加载服务状态
            });
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
        <title>编辑域配置 - AD 密码管理系统</title>
        <style>
            body {
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                background: #f5f7fa;
                margin: 0;
                padding: 0;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
                background: #667eea;
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
                accent-color: #667eea;
            }
            .checkbox-description {
                color: #666;
                font-size: 13px;
                margin-left: 28px;
                line-height: 1.5;
            }
            .form-group input:focus {
                outline: none;
                border-color: #667eea;
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
        
        # 如果提供了 LDAP 密码，则更新（明文存储）
        if admin_password:
            domain.ldap_password = admin_password
        
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
                'admin_password': domain.ldap_password or domain.admin_password,
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
            'admin_password': domain.ldap_password or domain.admin_password,  # 优先使用 ldap_password
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
            conn = Connection(server, user=domain.admin_dn, password=domain.ldap_password, authentication=SIMPLE, auto_bind=False)
            
            if conn.bind():
                diagnosis_result['ldap_connection'] = True
                conn.unbind()
        except Exception as e:
            pass
        
        # 3. 测试 LDAPS 连接
        try:
            tls_context = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLS_CLIENT, ciphers='ALL:@SECLEVEL=0')
            server = Server(f"ldaps://{domain.ldap_host}:{domain.ldaps_port or 636}", get_info=ALL, tls=tls_context, connect_timeout=10)
            conn = Connection(server, user=domain.admin_dn, password=domain.ldap_password, authentication=SIMPLE, auto_bind=False)
            
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
        
        # 保存密码 (明文保存，用于 LDAP 连接)
        # 注意：LDAP 连接需要明文密码，不能加密
        domain.admin_password = admin_password
        
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
        
        # 存储密码 (明文保存，用于 LDAP 连接)
        # 注意：LDAP 连接需要明文密码，不能加密
        admin_password = data['admin_password']
        domain.admin_password = admin_password
        domain.ldap_password = admin_password
        
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
        domain.admin_password = data['admin_password']
        domain.ldap_password = data['admin_password']
    
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



@admin_bp.route('/api/admin/users', methods=['GET'])
@login_required
def get_users():
    """获取用户列表"""
    if session.get('user_role') != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    return jsonify({
        'success': True,
        'data': [],
        'total': 0,
        'pages': 0
    })


@admin_bp.route('/api/admin/users/list', methods=['GET'])
@admin_required
def get_users_list():
    """获取用户列表 - 完整版本"""
    from models.models import User
    
    try:
        users = User.query.all()
        user_list = [{
            'id': u.id,
            'username': u.username,
            'email': u.ad_email,
            'display_name': u.ad_display_name,
            'phone': u.phone,
            'is_active': u.is_active,
            'mfa_enabled': u.mfa_enabled or False,
            'last_sync': u.updated_at.strftime('%Y-%m-%d %H:%M:%S') if u.updated_at else '从未同步',
        } for u in users]
        
        return jsonify({
            'success': True,
            'data': user_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'data': []
        })


@admin_bp.route('/api/admin/users/sync', methods=['POST'])
@admin_required
def sync_users_from_ad():
    """从 AD 服务器同步用户（与 Domains 页面的 LDAP 配置关联）"""
    from models.models import User, Domain, db
    try:
        # 优先使用真实的 LDAP 服务
        from services.ldap_service import LdapService
        print('[INFO] 使用真实 LDAP 服务同步用户')
    except ImportError:
        # 如果真实服务不可用，使用模拟服务
        from services.ldap_service_mock import LdapService
        print('[INFO] 使用模拟 LDAP 服务同步用户')
    
    from datetime import datetime
    
    try:
        # 获取第一个启用的域配置（主域）
        domain = Domain.query.filter_by(is_active=True).first()
        
        print(f'[DEBUG] 使用域配置：{domain.name if domain else "无"}')
        
        if not domain:
            return jsonify({
                'success': False,
                'message': '请先在【域配置管理】中配置 LDAP 信息'
            }), 200
        
        added_count = 0
        updated_count = 0
        
        try:
            print(f'[DEBUG] 开始同步域：{domain.name}')
            
            # 统计删除前的用户数量（排除 admin）
            deleted_count = User.query.filter(User.username != 'admin').count()
            print(f'[DEBUG] 删除前用户数（排除 admin）: {deleted_count}')
            
            # 从 LDAP 同步用户
            ad_users = LdapService.sync_users(domain)
            
            print(f'[DEBUG] 从域 {domain.name} 获取到 {len(ad_users)} 个用户')
            
            # 检查是否获取到用户
            if not ad_users or len(ad_users) == 0:
                print(f'[WARNING] 域 {domain.name} 中没有找到任何用户')
                print(f'[WARNING] 请检查:')
                print(f'  1. LDAP 连接配置是否正确 (主机：{domain.ldap_host})')
                print(f'  2. Base DN 是否配置正确：{domain.base_dn}')
                print(f'  3. AD 域中是否有用户')
                print(f'  4. 管理员账号是否有权读取 AD 数据')
            
            # 清空 users 表（保留 admin 用户）
            # 注意：需要先删除关联的日志记录，避免外键约束错误
            admin_user = User.query.filter_by(username='admin').first()
            
            # 1. 先删除非 admin 用户相关的管理员日志
            users_to_delete = User.query.filter(User.username != 'admin').all()
            user_ids_to_delete = [user.id for user in users_to_delete]
            print(f'[DEBUG] 将要删除的用户 IDs: {user_ids_to_delete}')
            
            if user_ids_to_delete:
                # 删除这些用户的管理员日志
                from models.models import AdminLog, SmsVerificationCode
                AdminLog.query.filter(AdminLog.admin_id.in_(user_ids_to_delete)).delete(synchronize_session=False)
                db.session.flush()
                print(f'[DEBUG] 已删除 {len(user_ids_to_delete)} 个用户的管理员日志')
                
                # 删除这些用户的短信验证码记录
                SmsVerificationCode.query.filter(SmsVerificationCode.user_id.in_(user_ids_to_delete)).delete(synchronize_session=False)
                db.session.flush()
                print(f'[DEBUG] 已删除 {len(user_ids_to_delete)} 个用户的短信验证码记录')
            
            # 2. 然后删除非 admin 用户
            User.query.filter(User.username != 'admin').delete()
            db.session.flush()  # 立即执行删除
            
            print(f'[DEBUG] 已清空 users 表，保留 admin 用户')
            
            # 同步所有 AD 用户（全部作为新增）
            for ad_user in ad_users:
                print(f'[DEBUG] 处理用户：{ad_user["username"]}')
                
                # 创建新用户
                user = User(
                    username=ad_user['username'],
                    ad_email=ad_user.get('email', ''),
                    ad_display_name=ad_user.get('display_name', ''),
                    phone=ad_user.get('phone', ''),
                    ad_dn=ad_user.get('dn', ''),
                    domain_id=domain.id,  # 关联到当前域
                    is_active=True,
                    updated_at=datetime.utcnow()
                )
                # 不设置密码，由 LDAP 认证处理
                db.session.add(user)
                added_count += 1
                print(f'[DEBUG] 新增用户：{ad_user["username"]}')
        except Exception as e:
            print(f'同步域 {domain.name} 失败：{str(e)}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'同步失败：{str(e)}'
            }), 500
        
        print(f'[DEBUG] 同步完成：新增 {added_count}, 更新 {updated_count}, 删除 {deleted_count}')
        db.session.commit()
        
        # 记录操作日志
        from utils.logger import log_operation
        log_operation(
            'user_sync',
            details=f'从 AD 同步用户：新增 {added_count} 人，更新 {updated_count} 人，删除 {deleted_count} 人'
        )
        
        return jsonify({
            'success': True,
            'message': '同步完成',
            'data': {
                'added': added_count,
                'updated': updated_count,
                'deleted': deleted_count,
                'total': User.query.count(),
                'domain_name': domain.name
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f'同步失败：{str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'同步失败：{str(e)}'
        }), 500


@admin_bp.route('/api/admin/users/preview', methods=['GET'])
@admin_required
def preview_ad_users():
    """预览 AD 用户信息（从 LDAP 获取，不保存到数据库）"""
    try:
        # 优先使用真实的 LDAP 服务
        from services.ldap_service import LdapService
        print('[INFO] 使用真实 LDAP 服务预览用户')
    except ImportError:
        # 如果真实服务不可用，使用模拟服务
        from services.ldap_service_mock import LdapService
        print('[INFO] 使用模拟 LDAP 服务预览用户')
    
    try:
        # 获取第一个启用的域配置（主域）
        domain = Domain.query.filter_by(is_active=True).first()
        
        print(f'[DEBUG] 使用域配置：{domain.name if domain else "无"}')
        
        if not domain:
            return jsonify({
                'success': False,
                'message': '请先在【域配置管理】中配置 LDAP 信息'
            }), 200
        
        # 从 LDAP 同步用户
        ad_users = LdapService.sync_users(domain)
        
        print(f'[DEBUG] 从域 {domain.name} 获取到 {len(ad_users)} 个用户')
        
        # 格式化用户信息
        user_list = []
        for ad_user in ad_users:
            user_info = {
                'username': ad_user.get('username', ''),
                'email': ad_user.get('email', ''),
                'phone': ad_user.get('phone', ''),
                'display_name': ad_user.get('display_name', ''),
                'dn': ad_user.get('dn', '')
            }
            user_list.append(user_info)
        
        return jsonify({
            'success': True,
            'data': user_list,
            'total': len(user_list),
            'domain_name': domain.name
        })
        
    except Exception as e:
        print(f'预览失败：{str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'获取 AD 用户失败：{str(e)}',
            'data': [],
            'total': 0
        })


@admin_bp.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """更新用户信息（管理员）"""
    from models.models import User, db
    
    data = request.json
    user = User.query.get_or_404(user_id)
    
    try:
        # 更新手机号
        if 'phone' in data:
            user.phone = data['phone']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '用户信息更新成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'更新失败：{str(e)}'
        }), 500


@admin_bp.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """删除用户"""
    from models.models import User, db
    
    try:
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
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


@admin_bp.route('/api/admin/users/username/<username>/reset-password', methods=['POST'])
@admin_required
def reset_user_password_by_username(username):
    """通过用户名重置用户密码"""
    from models.models import User, Domain, db
    from services.ldap_service import LdapService
    from ldap3 import Connection, Server, SUBTREE, SIMPLE
    from ldap3.core import exceptions as ldap_exceptions
    import ldap3
    
    data = request.json
    new_password = data.get('password')
    
    if not new_password:
        return jsonify({'success': False, 'message': '密码不能为空'}), 400
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': '密码长度至少 6 位'}), 400
    
    try:
        # 查找用户
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'}), 404
        
        # 获取域配置
        domain = Domain.query.first()
        if not domain:
            return jsonify({'success': False, 'message': '域配置不存在'}), 404
        
        # 使用 LDAP 同步密码到 AD
        # 注意：AD 密码修改必须使用 LDAPS（SSL）连接
        try:
            # 连接 AD（使用 ldap_password 明文密码）
            ldap_password = domain.ldap_password or domain.admin_password
            
            # 智能判断：根据端口决定是否使用 LDAPS
            is_ldaps_port = (domain.ldap_port == 636 or domain.ldaps_port == 636 or domain.ldap_port == domain.ldaps_port)
            use_ldaps = domain.use_ssl or is_ldaps_port
            
            if use_ldaps:
                # 使用 LDAPS 加密连接（端口 636）
                ldaps_port = domain.ldaps_port or 636
                protocol = 'ldaps'
                print(f'[LDAP 密码修改] 检测到 LDAPS 配置，使用 LDAPS 加密连接：{domain.ldap_host}:{ldaps_port}')
                
                # 创建 TLS 配置，允许自签名证书
                import ssl
                from ldap3 import Tls
                tls_context = Tls(
                    validate=ssl.CERT_NONE,  # 不验证证书（允许自签名）
                    version=ssl.PROTOCOL_TLS_CLIENT,
                    ciphers='ALL:@SECLEVEL=0'  # 降低安全级别以兼容旧服务器
                )
                
                server = Server(
                    f"{protocol}://{domain.ldap_host}:{ldaps_port}",
                    get_info=None,
                    tls=tls_context,
                    connect_timeout=10
                )
            else:
                # 使用 LDAP 明文连接（端口 389）
                ldap_port = domain.ldap_port or 389
                protocol = 'ldap'
                print(f'[LDAP 密码修改] 使用 LDAP 明文连接：{domain.ldap_host}:{ldap_port}')
                server = Server(f"{protocol}://{domain.ldap_host}:{ldap_port}", get_info=None)
            
            conn = Connection(
                server,
                user=domain.admin_dn,
                password=ldap_password,
                authentication=SIMPLE,
                auto_bind=True,
                receive_timeout=30
            )
            
            # 搜索用户 DN
            search_filter = f'(&(sAMAccountName={username}))'
            conn.search(
                search_base=domain.base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=['distinguishedName']
            )
            
            if not conn.entries:
                return jsonify({'success': False, 'message': 'AD 中未找到用户'}), 404
            
            user_dn = conn.entries[0].entry_dn
            
            # 重置密码（使用 unicodePwd 属性）
            # AD 要求密码必须用双引号包裹并编码为 UTF-16LE
            encoded_password = ('"' + new_password + '"').encode('utf-16-le')
            
            changes = {
                'unicodePwd': [(ldap3.MODIFY_REPLACE, [encoded_password])]
            }
            
            result = conn.modify(user_dn, changes)
            
            if result:
                # 同步本地数据库密码（bcrypt 加密）
                from werkzeug.security import generate_password_hash
                user.password = generate_password_hash(new_password)
                db.session.commit()
                
                # 记录操作日志
                from utils.logger import log_operation
                log_operation(
                    'password_reset',
                    target_user=username,
                    details=f'管理员重置用户 {username} 的密码'
                )
                
                # 成功提示不包含敏感信息（用户名和密码）
                return jsonify({
                    'success': True,
                    'message': '密码重置成功'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'AD 密码重置失败：{conn.result}'
                }), 500
                
        except ldap_exceptions.LDAPException as e:
            return jsonify({
                'success': False,
                'message': f'LDAP 连接错误：{str(e)}'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'重置密码失败：{str(e)}'
        }), 500


@admin_bp.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(user_id):
    """通过 ID 重置用户密码（保留兼容）"""
    from models.models import User
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404
    
    # 重定向到用户名版本的 API
    return reset_user_password_by_username(user.username)


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


@admin_bp.route('/api/settings', methods=['GET'])
@admin_required
def get_settings():
    """获取系统设置"""
    from models.models import SystemSetting
    
    try:
        settings = SystemSetting.query.all()
        return jsonify({
            'success': True,
            'data': [s.to_dict() for s in settings]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取设置失败：{str(e)}'
        }), 500


@admin_bp.route('/api/settings', methods=['POST'])
@admin_required
def save_settings():
    """保存系统设置"""
    from models.models import SystemSetting, db
    
    try:
        data = request.get_json()
        settings_data = data.get('settings', [])
        
        if not settings_data:
            return jsonify({
                'success': False,
                'message': '未提供设置数据'
            }), 400
        
        for setting_item in settings_data:
            key = setting_item.get('key')
            value = setting_item.get('value')
            setting_type = setting_item.get('type', 'string')
            
            if not key:
                continue
            
            # 查找或创建设置
            setting = SystemSetting.query.filter_by(setting_key=key).first()
            
            if setting:
                setting.setting_value = str(value)
                setting.setting_type = setting_type
            else:
                setting = SystemSetting(
                    setting_key=key,
                    setting_value=str(value),
                    setting_type=setting_type
                )
                db.session.add(setting)
        
        db.session.commit()
        
        # 记录操作日志
        from utils.logger import log_operation
        log_operation('system_settings_update', details=f'管理员 {session.get("username")} 更新了系统设置')
        
        return jsonify({
            'success': True,
            'message': '设置保存成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'保存设置失败：{str(e)}'
        }), 500


@admin_bp.route('/api/service/status', methods=['GET'])
@admin_required
def get_service_status():
    """获取当前服务状态（端口和主机）"""
    try:
        # 从系统设置中获取端口和主机配置
        from models.models import SystemSetting
        
        port_setting = SystemSetting.query.filter_by(setting_key='system_port').first()
        host_setting = SystemSetting.query.filter_by(setting_key='system_host').first()
        
        port = port_setting.setting_value if port_setting else '5000'
        host = host_setting.setting_value if host_setting else '0.0.0.0'
        
        return jsonify({
            'success': True,
            'data': {
                'port': port,
                'host': host
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取服务状态失败：{str(e)}'
        }), 500


@admin_bp.route('/api/database/test', methods=['POST'])
@admin_required
def test_database_connection():
    """测试数据库连接"""
    from services.database_service import DatabaseService
    import logging
    
    try:
        data = request.get_json()
        
        # 记录接收到的数据用于调试
        logging.info(f'接收到的数据库配置：{data}')
        
        if not data:
            return jsonify({
                'success': False,
                'message': '未提供配置数据'
            }), 400
        
        db_type = data.get('type')
        host = data.get('host')
        port = data.get('port')
        database = data.get('database')
        username = data.get('username')
        password = data.get('password')
        
        # 记录详细信息
        logging.info(f'数据库类型：{db_type}, 主机：{host}, 端口：{port}, 数据库：{database}, 用户：{username}')
        
        # 验证必填字段
        required_fields = ['type', 'host', 'database', 'username']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'缺少必填字段：{", ".join(missing_fields)}'
            }), 400
        
        # 使用默认端口
        if not port:
            port = DatabaseService.DEFAULT_PORTS.get(db_type, 0)
        
        # 测试连接
        result = DatabaseService.test_connection(
            db_type=db_type,
            host=host,
            port=int(port),
            database=database,
            username=username,
            password=password
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'测试失败：{str(e)}'
        }), 500


@admin_bp.route('/api/database/config', methods=['GET'])
@admin_required
def get_database_config():
    """获取数据库配置"""
    from models.models import SystemSetting
    
    try:
        import json
        
        setting = SystemSetting.query.filter_by(setting_key='database_config').first()
        
        if setting and setting.setting_value:
            config = json.loads(setting.setting_value)
            # 不返回密码
            config.pop('password', None)
            config.pop('password_encrypted', None)
            return jsonify({
                'success': True,
                'data': config
            })
        else:
            return jsonify({
                'success': True,
                'data': None
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取配置失败：{str(e)}'
        }), 500


@admin_bp.route('/api/database/config', methods=['POST'])
@admin_required
def save_database_config():
    """保存数据库配置（包含自动测试连接）"""
    from models.models import SystemSetting, db
    from services.database_service import DatabaseService
    import json
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': '未提供配置数据'
            }), 400
        
        db_type = data.get('type')
        host = data.get('host')
        port = data.get('port')
        database = data.get('database')
        username = data.get('username')
        password = data.get('password')
        
        # 验证必填字段
        required_fields = ['type', 'host', 'database', 'username']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'缺少必填字段：{", ".join(missing_fields)}'
            }), 400
        
        # 如果是新配置或密码改变，需要测试连接
        existing_setting = SystemSetting.query.filter_by(setting_key='database_config').first()
        need_test = not existing_setting or password
        
        if need_test:
            # 使用现有密码或新密码测试连接
            test_password = password
            if not test_password and existing_setting:
                # 如果没有新密码，说明用户只想更新其他配置，不需要测试
                need_test = False
            
            if need_test:
                # 测试连接
                test_result = DatabaseService.test_connection(
                    db_type=db_type,
                    host=host,
                    port=int(port) if port else DatabaseService.DEFAULT_PORTS.get(db_type),
                    database=database,
                    username=username,
                    password=test_password
                )
                
                if not test_result['success']:
                    return jsonify({
                        'success': False,
                        'message': f'数据库连接测试失败：{test_result["message"]}'
                    }), 400
        
        # 构建配置对象
        config = {
            'type': db_type,
            'host': host,
            'port': int(port) if port else DatabaseService.DEFAULT_PORTS.get(db_type),
            'database': database,
            'username': username
        }
        
        # 如果有新密码，加密存储
        if password:
            config['password_encrypted'] = DatabaseService.encrypt_password(password)
        elif existing_setting:
            # 保留原有加密密码
            existing_config = json.loads(existing_setting.setting_value)
            config['password_encrypted'] = existing_config.get('password_encrypted')
        
        # 保存配置
        setting = SystemSetting.query.filter_by(setting_key='database_config').first()
        
        if setting:
            setting.setting_value = json.dumps(config)
            setting.setting_type = 'json'
        else:
            setting = SystemSetting(
                setting_key='database_config',
                setting_value=json.dumps(config),
                setting_type='json',
                description='数据库连接配置'
            )
            db.session.add(setting)
        
        db.session.commit()
        
        # 记录操作日志
        from utils.logger import log_operation
        log_operation('database_config_update', 
                     details=f'管理员 {session.get("username")} 更新了数据库配置：{db_type}@{host}:{config["port"]}/{database}')
        
        # 提示用户需要重启应用
        return jsonify({
            'success': True,
            'message': '数据库配置保存成功！请重启应用使配置生效。',
            'data': config
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'保存配置失败：{str(e)}'
        }), 500


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

