<template>
  <div class="login-container">
    <div class="login-box">
      <h1 class="login-title">AD 密码管理系统</h1>
      <p class="login-subtitle">Active Directory 身份认证</p>
      
      <el-card class="login-card">
        <div class="login-content">
          <el-icon :size="64" color="#667eea"><Lock /></el-icon>
          
          <div class="login-actions">
            <p class="login-tip">使用 AD 域账号直接登录</p>
            
            <el-button 
              type="primary" 
              size="large" 
              @click="handleLogin"
              :loading="loading"
            >
              <el-icon><User /></el-icon>
              LDAP 登录
            </el-button>
          </div>
        </div>
      </el-card>
      
      <div class="login-footer">
        <p>© 2026 AD Password System. All rights reserved.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)

const handleLogin = () => {
  console.log('点击登录按钮')
  loading.value = true
  // 跳转到后端的 LDAP 登录页面
  setTimeout(() => {
    console.log('准备跳转到 /login')
    window.location.href = '/login'
  }, 100)
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px;
}

.login-box {
  width: 100%;
  max-width: 480px;
  text-align: center;
}

.login-title {
  font-size: 32px;
  font-weight: bold;
  color: white;
  margin-bottom: 10px;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
}

.login-subtitle {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 30px;
}

.login-card {
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.login-content {
  padding: 40px 30px;
}

.login-actions {
  margin-top: 30px;
}

.login-tip {
  color: #666;
  margin-bottom: 20px;
  font-size: 14px;
}

.login-footer {
  margin-top: 30px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
}
</style>
