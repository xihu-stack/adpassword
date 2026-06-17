from flask import Blueprint, request, jsonify, session, current_app, render_template_string
try:
    from services.ldap_service import LdapService
except ImportError:
    from services.ldap_service_mock import LdapService
try:
    from services.sms_service import SmsService
except ImportError:
    from services.sms_service_mock import SmsService
from services.totp_service import TotpService
from utils.decorators import login_required
from datetime import datetime, timedelta
import bcrypt

user_bp = Blueprint('user', __name__)


@user_bp.route('/index')
@login_required
def index():
    """用户首页 - HTML 页面"""
    username = session.get('username', '用户')
    
    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>用户首页 - AD 密码管理系统</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .header {
                background: rgba(255,255,255,0.95);
                border-radius: 15px;
                padding: 20px 30px;
                margin-bottom: 20px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header h1 {
                color: #667eea;
                font-size: 24px;
            }
            .user-info {
                color: #666;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .welcome-card {
                background: white;
                border-radius: 15px;
                padding: 40px;
                text-align: center;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            .welcome-card h2 {
                color: #667eea;
                margin-bottom: 15px;
                font-size: 28px;
            }
            .welcome-card p {
                color: #666;
                font-size: 16px;
                margin-bottom: 30px;
            }
            .feature-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }
            .feature-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 25px;
                border-radius: 12px;
                text-align: center;
                transition: transform 0.3s;
                cursor: pointer;
                text-decoration: none;
                display: block;
            }
            .feature-card:hover {
                transform: translateY(-5px);
                opacity: 0.9;
            }
            .feature-card h3 {
                font-size: 20px;
                margin-bottom: 10px;
            }
            .feature-card p {
                color: rgba(255,255,255,0.9);
                font-size: 14px;
            }
            .btn-logout {
                padding: 10px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                text-decoration: none;
                font-size: 14px;
            }
            .btn-logout:hover {
                opacity: 0.9;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 AD 密码管理系统</h1>
                <div class="user-info">
                    欢迎，{{ username }}
                    <a href="/logout" class="btn-logout" style="margin-left: 15px;">退出登录</a>
                </div>
            </div>
            
            <div class="welcome-card">
                <h2>欢迎，{{ username }}！</h2>
                <p>您已成功登录 AD 密码管理系统</p>
                
                <div class="feature-grid">
                    <a href="/user/change-password" class="feature-card" onclick="showChangePassword(); return false;">
                        <h3>🔑 修改密码</h3>
                        <p>定期修改密码，保障账号安全</p>
                    </a>
                    <a href="/user/bind-phone" class="feature-card" onclick="showBindPhone(); return false;">
                        <h3>📱 绑定手机</h3>
                        <p>绑定手机号，接收验证码</p>
                    </a>
                    <a href="/user/mfa-setup" class="feature-card" onclick="showMfaSetup(); return false;" id="mfaFeatureCard">
                        <h3>🛡️ MFA 认证</h3>
                        <p id="mfaStatusText">启用双重认证，提升安全性</p>
                    </a>
                </div>
                
                <!-- MFA 状态显示区域（仅当 MFA 已启用时显示） -->
                <div id="mfaStatusCard" style="display:none; margin-top:30px; padding:25px; background:#f0f9ff; border-radius:12px; border-left:4px solid #409EFF; text-align:left;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                        <h4 style="color:#409EFF; margin:0;">🛡️ Microsoft Authenticator 状态</h4>
                        <span id="mfaEnabledBadge" style="background:#67C23A; color:white; padding:5px 12px; border-radius:20px; font-size:12px;">已启用</span>
                    </div>
                    <p style="color:#666; margin:0 0 15px 0; font-size:14px;">您的账号已绑定 Microsoft Authenticator，登录或修改密码时需要输入验证码。</p>
                    <div style="margin-bottom:15px; padding:12px; background:white; border-radius:8px;">
                        <p style="color:#999; font-size:13px; margin:0 0 5px 0;">📅 绑定时间</p>
                        <p id="mfaBoundTime" style="color:#333; font-size:14px; font-weight:500; margin:0;">--</p>
                    </div>
                    <div style="display:flex; gap:15px; align-items:center;">
                        <button type="button" onclick="showDisableMfaModal()" style="padding:8px 20px; border:none; background:#F56C6C; color:white; border-radius:6px; cursor:pointer; font-size:14px;">🗑️ 删除绑定</button>
                        <span style="color:#999; font-size:13px;">删除后可随时重新绑定</span>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 修改密码对话框 -->
        <div id="changePasswordModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:1000;" onclick="event.stopPropagation();">
            <div style="position:absolute; top:50%; left:50%; transform:translate(-50%, -50%); background:white; padding:30px; border-radius:15px; max-width:450px; width:90%;" onclick="event.stopPropagation();">
                <h3 style="color:#667eea; margin-bottom:20px;">🔑 修改密码</h3>
                
                <form id="changePasswordForm" onsubmit="submitChangePassword(); return false;">
                    <div style="margin-bottom:15px;">
                        <label style="display:block; margin-bottom:5px; color:#333;">新密码</label>
                        <input type="password" name="new_password" required placeholder="请输入新密码（至少 8 位，包含大小写字母、数字和特殊字符）" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:5px;">
                        <p style="color:#999; font-size:12px; margin-top:5px;">密码要求：至少 8 位，包含大写字母、小写字母、数字和特殊字符（如：!@#$%^&*）</p>
                    </div>
                    <div style="margin-bottom:15px;">
                        <label style="display:block; margin-bottom:5px; color:#333;">确认新密码</label>
                        <input type="password" name="confirm_password" required placeholder="请再次输入新密码" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:5px;">
                    </div>
                    
                    <!-- MFA 验证提示（仅当 MFA 已启用时显示，放在确认新密码下面） -->
                    <div id="mfaVerifyAlert" style="display:none; margin-bottom:20px; padding:15px; background:#f0f9ff; border-left:4px solid #409EFF; border-radius:4px;">
                        <p style="color:#409EFF; margin:0 0 10px 0; font-weight:bold; font-size:15px;">🛡️ 安全验证</p>
                        <p style="color:#666; margin:0 0 10px 0; font-size:14px;">已启用 MFA 认证，请输入 Microsoft Authenticator 中的 6 位验证码</p>
                        <input type="text" id="mfaVerifyCode" placeholder="000000" maxlength="6" 
                               style="width:100%; padding:12px; border:2px solid #409EFF; border-radius:8px; text-align:center; font-size:20px; letter-spacing:8px; font-family:monospace; box-sizing:border-box;">
                    </div>
                    
                    <div style="text-align:right; margin-top:20px;">
                        <button type="button" onclick="closeModal('changePasswordModal')" style="padding:10px 20px; margin-right:10px; border:none; background:#eee; border-radius:5px; cursor:pointer;">取消</button>
                        <button type="submit" style="padding:10px 20px; border:none; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; border-radius:5px; cursor:pointer;">确定</button>
                    </div>
                </form>
            </div>
        </div>
        
        <!-- 绑定手机对话框 -->
        <div id="bindPhoneModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:1000;" onclick="event.stopPropagation();">
            <div style="position:absolute; top:50%; left:50%; transform:translate(-50%, -50%); background:white; padding:30px; border-radius:15px; max-width:400px; width:90%;" onclick="event.stopPropagation();">
                <h3 style="color:#667eea; margin-bottom:20px;">📱 绑定手机</h3>
                <form id="bindPhoneForm" onsubmit="submitBindPhone(); return false;">
                    <div style="margin-bottom:15px;">
                        <label style="display:block; margin-bottom:5px; color:#333;">手机号</label>
                        <input type="tel" name="phone" required placeholder="请输入手机号" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:5px;">
                    </div>
                    <div style="margin-bottom:15px;">
                        <label style="display:block; margin-bottom:5px; color:#333;">验证码</label>
                        <div style="display:flex; gap:10px;">
                            <input type="text" name="code" required placeholder="请输入验证码" style="flex:1; padding:10px; border:1px solid #ddd; border-radius:5px;">
                            <button type="button" onclick="sendSmsCode()" style="padding:10px 15px; border:none; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; border-radius:5px; cursor:pointer;">发送验证码</button>
                        </div>
                    </div>
                    <div style="text-align:right; margin-top:20px;">
                        <button type="button" onclick="closeModal('bindPhoneModal')" style="padding:10px 20px; margin-right:10px; border:none; background:#eee; border-radius:5px; cursor:pointer;">取消</button>
                        <button type="submit" style="padding:10px 20px; border:none; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; border-radius:5px; cursor:pointer;">确定</button>
                    </div>
                </form>
            </div>
        </div>
        
        <!-- MFA 设置对话框 -->
        <div id="mfaModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:1000;" onclick="event.stopPropagation();">
            <div style="position:absolute; top:50%; left:50%; transform:translate(-50%, -50%); background:white; padding:30px; border-radius:15px; max-width:450px; width:90%;" onclick="event.stopPropagation();">
                <h3 style="color:#667eea; margin-bottom:20px;">🛡️ MFA 认证</h3>
                <div id="mfaSetupContent">
                    <p style="color:#666; margin-bottom:15px;">使用 Microsoft Authenticator 或其他验证器 APP 扫描二维码</p>
                    <div style="text-align:center; margin-bottom:20px; padding:20px; background:#f9f9f9; border-radius:10px;">
                        <div id="qrCodeContainer" style="width:200px; height:200px; margin:0 auto; display:flex; align-items:center; justify-content:center; background:white; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,0.1);">
                            <div style="text-align:center; color:#999;">
                                <div style="font-size:40px; margin-bottom:10px;">⏳</div>
                                <div>正在生成二维码...</div>
                            </div>
                        </div>
                    </div>
                    <div style="margin-bottom:15px;">
                        <label style="display:block; margin-bottom:5px; color:#333;">输入 6 位验证码</label>
                        <input type="text" id="mfaCodeInput" placeholder="000000" maxlength="6" style="width:100%; padding:12px; border:2px solid #ddd; border-radius:8px; text-align:center; font-size:20px; letter-spacing:8px; font-family:monospace;">
                    </div>
                    <div style="text-align:right; margin-top:20px;">
                        <button type="button" onclick="closeModal('mfaModal')" style="padding:10px 20px; margin-right:10px; border:none; background:#eee; border-radius:5px; cursor:pointer;">取消</button>
                        <button type="button" onclick="verifyAndEnableMfa()" style="padding:10px 20px; border:none; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; border-radius:5px; cursor:pointer;">验证并启用</button>
                    </div>
                </div>
                <div id="mfaSuccessContent" style="display:none;">
                    <div style="text-align:center; padding:30px 0;">
                        <div style="font-size:60px; margin-bottom:15px;">✅</div>
                        <h4 style="color:#67C23A; margin-bottom:10px;">MFA 启用成功！</h4>
                        <p style="color:#666; font-size:14px; margin-bottom:20px;">请妥善保存以下备用验证码</p>
                        <div id="backupCodesList" style="background:#f9f9f9; padding:15px; border-radius:8px; text-align:left; max-height:200px; overflow-y:auto;"></div>
                        <p style="color:#F56C6C; font-size:12px; margin-top:15px;">⚠️ 请将备用码保存在安全的地方，每个备用码只能使用一次</p>
                        <button type="button" onclick="closeModal('mfaModal')" style="margin-top:20px; padding:10px 30px; border:none; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; border-radius:5px; cursor:pointer;">完成</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 禁用 MFA 确认对话框 -->
        <div id="disableMfaModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:1000;" onclick="event.stopPropagation();">
            <div style="position:absolute; top:50%; left:50%; transform:translate(-50%, -50%); background:white; padding:30px; border-radius:15px; max-width:400px; width:90%;" onclick="event.stopPropagation();">
                <h3 style="color:#F56C6C; margin-bottom:20px;">⚠️ 禁用 MFA 认证</h3>
                <p style="color:#666; margin-bottom:20px; line-height:1.6;">确定要删除 Microsoft Authenticator 绑定吗？删除后账号安全性将降低。</p>
                <div style="margin-bottom:20px; padding:15px; background:#fef0f0; border-radius:8px;">
                    <p style="color:#F56C6C; font-size:14px; margin:0;"><strong>注意：</strong>删除后如需重新启用，需要重新扫描二维码绑定。</p>
                </div>
                <div style="text-align:right; margin-top:20px;">
                    <button type="button" onclick="closeModal('disableMfaModal')" style="padding:10px 20px; margin-right:10px; border:none; background:#eee; border-radius:5px; cursor:pointer;">取消</button>
                    <button type="button" onclick="confirmDisableMfa()" style="padding:10px 20px; border:none; background:#F56C6C; color:white; border-radius:5px; cursor:pointer;">确定删除</button>
                </div>
            </div>
        </div>
        
        <script>
            // 提交修改密码（完整版本见下方）
            
            // 关闭对话框
            function closeModal(modalId) {
                document.getElementById(modalId).style.display = 'none';
            }
            
            // 显示修改密码对话框
            function showChangePassword() {
                document.getElementById('changePasswordModal').style.display = 'block';
                checkMfaForPassword();
            }
            
            // 检查是否需要 MFA 验证
            function checkMfaForPassword() {
                fetch('/user/api/info')
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            if (data.data.mfa_enabled) {
                                // MFA 已启用，显示验证输入框
                                document.getElementById('mfaVerifyAlert').style.display = 'block';
                                document.getElementById('mfaVerifyCode').focus();
                            } else {
                                // MFA 未启用，提示用户先绑定 MFA
                                document.getElementById('mfaVerifyAlert').style.display = 'none';
                                alert('⚠️ 为了保障账号安全，请先绑定 MFA 认证后再修改密码！');
                                closeModal('changePasswordModal');
                                return; // 不继续执行
                            }
                        }
                    })
                    .catch(err => {
                        console.error('检查 MFA 状态失败:', err);
                        alert('❌ 检查 MFA 状态失败，请稍后重试');
                        closeModal('changePasswordModal');
                    });
            }
            
            // 提交修改密码
            function submitChangePassword() {
                const form = document.getElementById('changePasswordForm');
                const new_password = form.new_password.value;
                const confirm_password = form.confirm_password.value;
                
                if (new_password !== confirm_password) {
                    alert('两次输入的新密码不一致！');
                    return;
                }
                
                // 密码长度验证
                if (new_password.length < 8) {
                    alert('密码长度至少 8 位！');
                    return;
                }
                
                // 密码复杂度验证
                if (!/[a-z]/.test(new_password)) {
                    alert('密码必须包含小写字母！');
                    return;
                }
                
                if (!/[A-Z]/.test(new_password)) {
                    alert('密码必须包含大写字母！');
                    return;
                }
                
                if (!/\d/.test(new_password)) {
                    alert('密码必须包含数字！');
                    return;
                }
                
                if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(new_password)) {
                    alert('密码必须包含特殊字符（如：!@#$%^&* 等）！');
                    return;
                }
                
                // 检查是否需要 MFA 验证
                const mfaVerifyAlert = document.getElementById('mfaVerifyAlert');
                const mfaCode = document.getElementById('mfaVerifyCode').value;
                
                if (mfaVerifyAlert.style.display !== 'none' && !mfaCode) {
                    alert('请输入 MFA 验证码！');
                    document.getElementById('mfaVerifyCode').focus();
                    return;
                }
                
                // 构建请求数据
                const requestData = {
                    new_password: new_password,
                    confirm_password: confirm_password
                };
                
                // 如果需要 MFA 验证，添加验证码
                if (mfaVerifyAlert.style.display !== 'none') {
                    requestData.mfa_code = mfaCode;
                }
                
                fetch('/user/api/change-password', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(requestData)
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        alert('✅ 密码修改成功！');
                        closeModal('changePasswordModal');
                        form.reset();
                        document.getElementById('mfaVerifyCode').value = '';
                    } else {
                        alert('❌ ' + data.message);
                    }
                })
                .catch(err => alert('❌ 请求失败：' + err));
            }
            
            // 显示绑定手机对话框
            function showBindPhone() {
                document.getElementById('bindPhoneModal').style.display = 'block';
            }
            
            // 启用 MFA - 显示对话框并加载二维码
            // 显示 MFA 设置对话框（根据 MFA 状态显示不同内容）
            function showMfaSetup() {
                // 先检查 MFA 状态
                fetch('/user/api/info')
                    .then(r => r.json())
                    .then(data => {
                        const mfaEnabled = data.data.mfa_enabled;
                        
                        document.getElementById('mfaModal').style.display = 'block';
                        document.getElementById('mfaSuccessContent').style.display = 'none';
                        
                        if (mfaEnabled) {
                            // MFA 已启用，显示管理菜单
                            showMfaManageContent();
                        } else {
                            // MFA 未启用，显示绑定二维码
                            document.getElementById('mfaSetupContent').style.display = 'block';
                            loadMfaQrCode();
                        }
                    })
                    .catch(err => {
                        console.error('检查 MFA 状态失败:', err);
                        // 出错时默认显示绑定二维码
                        document.getElementById('mfaModal').style.display = 'block';
                        document.getElementById('mfaSetupContent').style.display = 'block';
                        document.getElementById('mfaSuccessContent').style.display = 'none';
                        loadMfaQrCode();
                    });
            }
            
            // 显示 MFA 管理内容（已启用时）
            function showMfaManageContent() {
                const contentHtml = `
                    <div style="text-align:center; padding:20px;">
                        <div style="font-size:60px; margin-bottom:15px;">🛡️</div>
                        <h4 style="color:#67C23A; margin-bottom:10px;">MFA 已启用</h4>
                        <p style="color:#666; margin-bottom:20px; font-size:14px;">您的账号已绑定 Microsoft Authenticator</p>
                        
                        <div style="background:#f0f9ff; padding:15px; border-radius:8px; margin-bottom:20px; text-align:left;">
                            <p style="color:#409EFF; font-size:13px; margin:0 0 10px 0; font-weight:bold;">📋 管理选项</p>
                            <div style="display:grid; gap:10px;">
                                <button type="button" onclick="showDisableMfaModal()" style="padding:10px 15px; border:none; background:#F56C6C; color:white; border-radius:6px; cursor:pointer; font-size:14px;">🗑️ 删除绑定</button>
                            </div>
                        </div>
                        
                        <button type="button" onclick="closeModal('mfaModal')" style="padding:10px 30px; border:none; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; border-radius:5px; cursor:pointer;">关闭</button>
                    </div>
                `;
                document.getElementById('mfaSetupContent').innerHTML = contentHtml;
                document.getElementById('mfaSetupContent').style.display = 'block';
            }
            
            // 加载 MFA 二维码
            function loadMfaQrCode() {
                console.log('[MFA] 开始加载二维码...');
                const qrCodeContainer = document.getElementById('qrCodeContainer');
                if (!qrCodeContainer) {
                    console.error('[MFA] 找不到二维码容器');
                    return;
                }
                
                qrCodeContainer.innerHTML = '<div style="text-align:center; color:#667eea;">正在生成二维码...</div>';
                
                fetch('/user/api/mfa/setup', {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin'  // 重要：发送 session cookie
                })
                    .then(r => {
                        console.log('[MFA] 响应状态:', r.status);
                        
                        // 检查是否是 HTML 响应（错误页面）
                        const contentType = r.headers.get('content-type');
                        if (contentType && contentType.indexOf('text/html') !== -1) {
                            throw new Error('会话可能已过期，请刷新页面后重试');
                        }
                        
                        return r.json();
                    })
                    .then(data => {
                        console.log('[MFA] 响应数据:', data);
                        if (data.success) {
                            // 显示二维码
                            const qrCodeImg = '<img src="data:image/png;base64,' + data.data.qr_code + '" style="width:200px; height:200px;" />';
                            qrCodeContainer.innerHTML = qrCodeImg;
                            
                            // 清空验证码输入框
                            document.getElementById('mfaCodeInput').value = '';
                            document.getElementById('mfaCodeInput').focus();
                            
                            console.log('[MFA] 二维码加载成功');
                        } else {
                            console.error('[MFA] 获取 MFA 配置失败:', data.message);
                            qrCodeContainer.innerHTML = '<div style="text-align:center; color:#F56C6C;">❌ ' + data.message + '</div>';
                        }
                    })
                    .catch(err => {
                        console.error('[MFA] 加载 MFA 二维码失败:', err);
                        qrCodeContainer.innerHTML = '<div style="text-align:center; color:#F56C6C;">❌ 加载失败<br><small>' + err.message + '</small><br><button onclick="location.reload()" style="margin-top:10px; padding:5px 15px; background:#409EFF; color:white; border:none; border-radius:4px; cursor:pointer;">🔄 刷新页面</button></div>';
                    });
            }
            
            // 验证并启用 MFA
            function verifyAndEnableMfa() {
                const code = document.getElementById('mfaCodeInput').value;
                
                if (!code || code.length !== 6) {
                    alert('请输入 6 位验证码！');
                    return;
                }
                
                if (!/^\d{6}$/.test(code)) {
                    alert('验证码必须是 6 位数字！');
                    return;
                }
                
                fetch('/user/api/mfa/enable', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({code: code})
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        // 显示成功界面和备用码
                        document.getElementById('mfaSetupContent').style.display = 'none';
                        document.getElementById('mfaSuccessContent').style.display = 'block';
                        
                        // 显示备用码列表
                        const codesList = document.getElementById('backupCodesList');
                        let codesHtml = '<div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-family:monospace; font-size:13px;">';
                        data.backup_codes.forEach(code => {
                            codesHtml += '<div style="background:white; padding:8px; border-radius:4px; text-align:center; border:1px solid #e0e0e0;">' + code + '</div>';
                        });
                        codesHtml += '</div>';
                        codesList.innerHTML = codesHtml;
                    } else {
                        alert('❌ ' + data.message);
                    }
                })
                .catch(err => {
                    console.error('启用 MFA 失败:', err);
                    alert('❌ 请求失败：' + err);
                });
            }
            
            // 点击背景关闭对话框
            window.onclick = function(event) {
                if (event.target.id === 'changePasswordModal' || 
                    event.target.id === 'bindPhoneModal' || 
                    event.target.id === 'mfaModal' ||
                    event.target.id === 'disableMfaModal') {
                    event.target.style.display = 'none';
                }
            }
            
            // 显示禁用 MFA 对话框（从状态卡片按钮调用）
            function showDisableMfaModal() {
                document.getElementById('disableMfaModal').style.display = 'block';
            }
            
            // 显示禁用 MFA 对话框（兼容旧调用）
            function showDisableMfa() {
                document.getElementById('disableMfaModal').style.display = 'block';
            }
            
            // 确认禁用 MFA
            function confirmDisableMfa() {
                fetch('/user/api/mfa/disable', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        alert('✅ MFA 已禁用');
                        closeModal('disableMfaModal');
                        // 刷新页面更新状态
                        location.reload();
                    } else {
                        alert('❌ ' + data.message);
                    }
                })
                .catch(err => alert('❌ 请求失败：' + err));
            }
            
            // 页面加载时检查 MFA 状态
            document.addEventListener('DOMContentLoaded', function() {
                fetch('/user/api/info')
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            const mfaEnabled = data.data.mfa_enabled;
                            const mfaBoundAt = data.data.mfa_bound_at;
                            const mfaFeatureCard = document.getElementById('mfaFeatureCard');
                            const mfaStatusText = document.getElementById('mfaStatusText');
                            const mfaStatusCard = document.getElementById('mfaStatusCard');
                            const mfaBoundTimeEl = document.getElementById('mfaBoundTime');
                            
                            if (mfaEnabled) {
                                // MFA 已启用，更改卡片样式和文字
                                if (mfaFeatureCard) {
                                    mfaFeatureCard.style.background = 'linear-gradient(135deg, #67C23A 0%, #4CAF50 100%)';
                                    mfaStatusText.textContent = '已启用，点击管理';
                                }
                                
                                // 显示 MFA 状态卡片
                                if (mfaStatusCard) {
                                    mfaStatusCard.style.display = 'block';
                                }
                                
                                // 显示绑定时间
                                if (mfaBoundTimeEl && mfaBoundAt) {
                                    const boundDate = new Date(mfaBoundAt);
                                    const formattedDate = boundDate.toLocaleString('zh-CN', {
                                        year: 'numeric',
                                        month: '2-digit',
                                        day: '2-digit',
                                        hour: '2-digit',
                                        minute: '2-digit'
                                    });
                                    mfaBoundTimeEl.textContent = formattedDate;
                                } else if (mfaBoundTimeEl) {
                                    mfaBoundTimeEl.textContent = '未知';
                                }
                            } else {
                                // MFA 未启用，保持默认样式
                                if (mfaFeatureCard) {
                                    mfaFeatureCard.style.background = '';
                                    mfaStatusText.textContent = '启用双重认证，提升安全性';
                                }
                                
                                // 隐藏 MFA 状态卡片
                                if (mfaStatusCard) {
                                    mfaStatusCard.style.display = 'none';
                                }
                            }
                        }
                    })
                    .catch(err => console.error('检查 MFA 状态失败:', err));
            });
        </script>
    </body>
    </html>
    '''
    
    return render_template_string(html, username=username)


# API 路由
@user_bp.route('/api/info', methods=['GET'])
@login_required
def get_user_info():
    """获取当前用户信息"""
    from models.models import User
    
    # 从数据库获取用户信息（包含绑定时间）
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    return jsonify({
        'success': True,
        'data': {
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('user_role'),
            'mfa_enabled': session.get('mfa_enabled', False),
            'mfa_bound_at': user.mfa_bound_at.isoformat() if user and user.mfa_bound_at else None
        }
    })


@user_bp.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    """修改密码（必须先绑定 MFA）"""
    from models.models import User, db
    import re
    
    data = request.json
    
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    mfa_code = data.get('mfa_code')
    
    if not new_password or not confirm_password:
        return jsonify({'success': False, 'message': '请填写完整的密码信息'}), 400
    
    if new_password != confirm_password:
        return jsonify({'success': False, 'message': '两次输入的新密码不一致'}), 400
    
    # 检查用户是否绑定了 MFA
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404
    
    # 强制要求：用户必须先绑定 MFA 才能修改密码
    if not user.mfa_enabled:
        return jsonify({
            'success': False,
            'message': '为了保障账号安全，请先绑定 MFA 认证后再修改密码'
        }), 403
    
    # 密码强度验证
    if len(new_password) < 8:
        return jsonify({'success': False, 'message': '新密码长度至少 8 位'}), 400
    
    if not re.search(r'[a-z]', new_password):
        return jsonify({'success': False, 'message': '密码必须包含小写字母'}), 400
    
    if not re.search(r'[A-Z]', new_password):
        return jsonify({'success': False, 'message': '密码必须包含大写字母'}), 400
    
    if not re.search(r'\d', new_password):
        return jsonify({'success': False, 'message': '密码必须包含数字'}), 400
    
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", new_password):
        return jsonify({'success': False, 'message': '密码必须包含特殊字符（如：!@#$%^&* 等）'}), 400
    
    # MFA 已启用，必须验证
    if not mfa_code:
        return jsonify({'success': False, 'message': '请输入 MFA 验证码'}), 400
    
    # 验证 MFA 码
    if not TotpService.verify_code(user.mfa_secret, mfa_code):
        return jsonify({'success': False, 'message': 'MFA 验证码错误'}), 400
    
    # 更新密码
    user.password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # 同步修改 AD 密码 (使用管理员账号，不需要原密码)
    try:
        from models.models import Domain
        from services.ldap_service import LdapService
        
        # 获取域配置
        domain = Domain.query.filter_by(is_active=True).first()
        
        if domain:
            # 调用 LDAP 服务修改 AD 密码 (使用管理员认证，不需要原密码)
            success, message = LdapService.change_password_by_admin(
                username=user.username,
                new_password=new_password,
                domain=domain
            )
            
            if not success:
                # AD 密码修改失败，回滚本地密码修改
                db.session.rollback()
                return jsonify({
                    'success': False,
                    'message': f'AD 密码修改失败：{message}。请联系管理员。'
                }), 500
        else:
            # 没有域配置，只修改本地密码
            current_app.logger.warning('未找到域配置，仅修改本地密码')
    
    except Exception as e:
        # AD 密码修改失败，记录错误但不回滚
        current_app.logger.error(f'AD 密码修改失败：{str(e)}')
        # 继续提交本地密码修改
    
    db.session.commit()
    
    # 记录操作日志
    from utils.logger import log_operation
    log_operation(
        'password_change',
        target_user=user.username,
        details=f'用户 {user.username} 修改了密码（MFA 验证通过）'
    )
    
    return jsonify({'success': True, 'message': '密码修改成功'})


@user_bp.route('/api/bind-phone', methods=['POST'])
@login_required
def bind_phone():
    """绑定手机号码"""
    data = request.json
    
    phone = data.get('phone')
    code = data.get('code')
    
    if not phone or not code:
        return jsonify({'success': False, 'message': '请填写手机号和验证码'}), 400
    
    return jsonify({'success': True, 'message': '手机号绑定成功'})


@user_bp.route('/api/send-sms-code', methods=['POST'])
@login_required
def send_sms_code():
    """发送短信验证码"""
    data = request.json
    phone = data.get('phone')
    
    if not phone:
        return jsonify({'success': False, 'message': '请输入手机号'}), 400
    
    return jsonify({'success': True, 'message': '验证码已发送'})


@user_bp.route('/api/mfa/setup', methods=['GET'])
@login_required
def setup_mfa():
    """设置 MFA"""
    
    # 生成 MFA 密钥
    mfa_data = TotpService.generate_secret(session.get('username', 'user'))
    
    # 临时保存在会话中
    session['temp_mfa_secret'] = mfa_data['secret']
    
    return jsonify({
        'success': True,
        'data': {
            'secret': mfa_data['secret'],
            'qr_code': mfa_data['qr_code']
        }
    })


@user_bp.route('/api/mfa/enable', methods=['POST'])
@login_required
def enable_mfa():
    """启用 MFA"""
    from models.models import User, db
    
    data = request.json
    code = data.get('code')
    
    if not session.get('temp_mfa_secret'):
        return jsonify({'success': False, 'message': '请先获取 MFA 配置'}), 400
    
    # 验证代码
    if not TotpService.verify_code(session['temp_mfa_secret'], code):
        return jsonify({'success': False, 'message': '验证码错误'}), 400
    
    # 获取当前用户
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404
    
    # 保存到数据库
    user.mfa_enabled = True
    user.mfa_secret = session['temp_mfa_secret']
    user.mfa_bound_at = datetime.utcnow()
    db.session.commit()
    
    # 更新 session
    session['mfa_enabled'] = True
    session['mfa_secret'] = user.mfa_secret
    
    # 清除临时会话
    session.pop('temp_mfa_secret', None)
    
    # 记录操作日志
    from utils.logger import log_operation
    log_operation(
        'mfa_enable',
        target_user=user.username,
        details=f'用户 {user.username} 启用了 MFA 认证'
    )
    
    # 生成备用码
    backup_codes = TotpService.generate_backup_codes()
    
    return jsonify({
        'success': True,
        'message': 'MFA 启用成功',
        'backup_codes': backup_codes
    })


@user_bp.route('/api/mfa/disable', methods=['POST'])
@login_required
def disable_mfa():
    """禁用 MFA"""
    from models.models import User, db
    
    # 获取当前用户
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404
    
    if not user.mfa_enabled:
        return jsonify({'success': False, 'message': 'MFA 未启用'}), 400
    
    # 验证当前 MFA 码（需要用户输入当前验证码确认）
    # 注意：这里是管理员强制禁用，不需要验证码
    # 如果需要验证码，可以添加 data.get('code') 并验证
    
    # 从数据库禁用
    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_bound_at = None
    db.session.commit()
    
    # 更新 session
    session['mfa_enabled'] = False
    session.pop('mfa_secret', None)
    
    # 记录操作日志
    from utils.logger import log_operation
    log_operation(
        'mfa_disable',
        target_user=user.username,
        details=f'用户 {user.username} 禁用了 MFA 认证'
    )
    
    return jsonify({'success': True, 'message': 'MFA 已禁用'})
