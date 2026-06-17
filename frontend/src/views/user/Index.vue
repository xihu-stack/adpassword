<template>
  <div class="user-container">
    <el-container>
      <!-- 侧边栏 -->
      <el-aside width="250px">
        <div class="logo">
          <el-icon :size="24"><Lock /></el-icon>
          <span>AD 密码管理</span>
        </div>
        
        <el-menu
          :default-active="activeMenu"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
          router
        >
          <el-menu-item index="/user/index">
            <el-icon><User /></el-icon>
            <span>修改密码</span>
          </el-menu-item>
          
          <el-menu-item index="/user/phone">
            <el-icon><Phone /></el-icon>
            <span>绑定手机</span>
          </el-menu-item>
          
          <el-menu-item index="/user/mfa">
            <el-icon><Key /></el-icon>
            <span>MFA 设置</span>
          </el-menu-item>
        </el-menu>
        
        <div class="user-info">
          <el-avatar :size="50">{{ userStore.userInfo.username?.charAt(0).toUpperCase() }}</el-avatar>
          <div class="info">
            <p class="username">{{ userStore.userInfo.username }}</p>
            <p class="role">{{ userStore.userInfo.role === 'admin' ? '管理员' : '普通用户' }}</p>
          </div>
        </div>
        
        <el-button @click="handleLogout" class="logout-btn">
          <el-icon><SwitchButton /></el-icon>
          退出登录
        </el-button>
      </el-aside>
      
      <!-- 主内容区 -->
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)

const handleLogout = () => {
  userStore.clearUserInfo()
  window.location.href = '/logout'
}
</script>

<style scoped>
.user-container {
  height: 100vh;
}

.el-container {
  height: 100%;
}

.el-aside {
  background-color: #304156;
  color: white;
  display: flex;
  flex-direction: column;
  padding: 20px 0;
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 18px;
  font-weight: bold;
  color: white;
  padding: 0 20px;
  margin-bottom: 30px;
}

.el-menu {
  border-right: none;
  flex: 1;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.user-info .username {
  font-size: 14px;
  font-weight: bold;
  color: white;
  margin: 0;
}

.user-info .role {
  font-size: 12px;
  color: #909399;
  margin: 4px 0 0 0;
}

.logout-btn {
  margin: 20px;
  background-color: transparent;
  color: #bfcbd9;
  border: 1px solid #bfcbd9;
}

.logout-btn:hover {
  background-color: #f56c6c;
  border-color: #f56c6c;
  color: white;
}

.el-main {
  background-color: #f0f2f5;
  padding: 30px;
}
</style>
