<template>
  <div class="dashboard">
    <h2>管理后台</h2>
    
    <el-row :gutter="20" style="margin-top: 30px;">
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="stat-card">
            <el-icon :size="48" color="#409EFF"><User /></el-icon>
            <div class="stat-info">
              <p class="stat-label">用户总数</p>
              <p class="stat-value">{{ stats.userCount }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="stat-card">
            <el-icon :size="48" color="#67C23A"><Connection /></el-icon>
            <div class="stat-info">
              <p class="stat-label">域配置数</p>
              <p class="stat-value">{{ stats.domainCount }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="stat-card">
            <el-icon :size="48" color="#E6A23C"><SuccessFilled /></el-icon>
            <div class="stat-info">
              <p class="stat-label">活跃域</p>
              <p class="stat-value">{{ stats.activeDomains }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-card style="margin-top: 30px;">
      <template #header>
        <span>快捷操作</span>
      </template>
      
      <el-row :gutter="20">
        <el-col :span="6">
          <el-button type="primary" @click="goToDomains" style="width: 100%;">
            <el-icon><Setting /></el-icon>
            域配置管理
          </el-button>
        </el-col>
              
        <el-col :span="6">
          <el-button type="success" @click="goToUsers" style="width: 100%;">
            <el-icon><Users /></el-icon>
            用户管理
          </el-button>
        </el-col>
              
        <el-col :span="6">
          <el-button type="warning" @click="goToSms" style="width: 100%;">
            <el-icon><ChatDotRound /></el-icon>
            短信配置
          </el-button>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { adminApi } from '@/api'
import { encryptPath } from '@/utils/pathEncrypt'

const router = useRouter()

const stats = reactive({
  userCount: 0,
  domainCount: 0,
  activeDomains: 0,
})

// 导航函数 - 使用加密路径
const goToDomains = () => {
  router.push(encryptPath('/admin/domains'))
}

const goToUsers = () => {
  router.push(encryptPath('/admin/users'))
}

const goToSms = () => {
  router.push(encryptPath('/admin/sms'))
}

const goToLogs = () => {
  router.push(encryptPath('/admin/logs'))
}

const goToSettings = () => {
  router.push(encryptPath('/admin/settings'))
}

onMounted(async () => {
  try {
    // 获取统计数据
    const response = await fetch('/admin/api/admin/dashboard/stats')
    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        stats.userCount = data.data.userCount || 0
        stats.domainCount = data.data.domainCount || 0
        stats.activeDomains = data.data.activeDomains || 0
      }
    }
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
})
</script>

<style scoped>
.dashboard h2 {
  font-size: 24px;
  color: #303133;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 10px;
}

.stat-info {
  flex: 1;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  margin: 5px 0 0 0;
}
</style>
