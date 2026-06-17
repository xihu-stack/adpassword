<template>
  <div class="user-manage">
    <div class="page-header">
      <div class="header-content">
        <div class="header-icon">
          <el-icon :size="32"><User /></el-icon>
        </div>
        <div class="header-text">
          <h2 class="page-title">用户管理</h2>
          <p class="page-subtitle">系统用户账号管理</p>
        </div>
      </div>
    </div>
    
    <div class="table-card">
      <el-table :data="users" border stripe v-loading="loading" class="modern-table" :header-cell-style="{background: '#f5f7fa', color: '#606266', fontWeight: '600'}">
        <el-table-column prop="username" label="用户名">
          <template #default="{ row }">
            <div class="user-info">
              <el-icon><User /></el-icon>
              <span>{{ row.username }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="display_name" label="显示名">
          <template #default="{ row }">
            <span class="display-name">{{ row.display_name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱">
          <template #default="{ row }">
            <span class="email-info">
              <el-icon><Message /></el-icon>
              {{ row.email }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="手机号">
          <template #default="{ row }">
            <span class="phone-info">
              <el-icon><Phone /></el-icon>
              {{ row.phone }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'" size="small" effect="light">
              <el-icon><Star v-if="row.role === 'admin'" /><UserFilled v-else /></el-icon>
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="MFA" width="120">
          <template #default="{ row }">
            <el-tag :type="row.mfa_enabled ? 'success' : 'info'" size="small" effect="light">
              <el-icon><Shield v-if="row.mfa_enabled" /><Lock v-else /></el-icon>
              {{ row.mfa_enabled ? '已启用' : '未启用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" type="primary" plain @click="handleEditPhone(row)">
                <el-icon><Phone /></el-icon>
                绑定
              </el-button>
              <el-button size="small" :type="row.role === 'admin' ? 'warning' : 'success'" plain @click="handleChangeRole(row)">
                <el-icon><Star /></el-icon>
                {{ row.role === 'admin' ? '取消管理员' : '设为管理员' }}
              </el-button>
              <el-button size="small" type="danger" plain @click="handleResetPassword(row)">
                <el-icon><RefreshLeft /></el-icon>
                重置密码
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>
    
    <!-- 分页 -->
    <el-pagination
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.perPage"
      :total="pagination.total"
      layout="total, prev, pager, next"
      @current-change="loadUsers"
      style="margin-top: 20px; justify-content: flex-end;"
    />
    
    <!-- 重置密码对话框 -->
    <el-dialog v-model="passwordDialogVisible" title="重置密码" width="400px">
      <el-form :model="passwordForm" ref="passwordFormRef" label-width="100px">
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.password" type="password" show-password />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitResetPassword" :loading="resetting">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api'

const users = ref([])
const loading = ref(false)
const passwordDialogVisible = ref(false)
const resetting = ref(false)
const currentUser = ref(null)

const pagination = reactive({
  page: 1,
  perPage: 20,
  total: 0,
})

const passwordForm = reactive({
  password: '',
})

onMounted(() => {
  loadUsers()
})

const loadUsers = async () => {
  loading.value = true
  try {
    const res = await adminApi.getUsers({
      page: pagination.page,
      per_page: pagination.perPage,
    })
    users.value = res.data
    pagination.total = res.total
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleEditPhone = (row) => {
  ElMessage.info('绑定手机功能待实现')
}

const handleChangeRole = async (row) => {
  try {
    const newRole = row.role === 'admin' ? 'user' : 'admin'
    const action = newRole === 'admin' ? '设为管理员' : '取消管理员'
    
    await ElMessageBox.confirm(`确定要${action}吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    
    await adminApi.updateUser(row.id, { role: newRole })
    ElMessage.success('操作成功')
    loadUsers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
    }
  }
}

const handleResetPassword = (row) => {
  currentUser.value = row
  passwordForm.password = ''
  passwordDialogVisible.value = true
}

const submitResetPassword = async () => {
  if (!passwordForm.password) {
    ElMessage.warning('请输入新密码')
    return
  }
  
  resetting.value = true
  try {
    await adminApi.resetUserPassword(currentUser.value.id, {
      password: passwordForm.password,
    })
    ElMessage.success('密码重置成功')
    passwordDialogVisible.value = false
  } catch (error) {
    console.error(error)
  } finally {
    resetting.value = false
  }
}
</script>

<style scoped>
.user-manage {
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: calc(100vh - 60px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 24px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  color: white;
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 4px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.table-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
}

.modern-table {
  border-radius: 8px;
  overflow: hidden;
}

.modern-table :deep(.el-table__header th) {
  font-weight: 600;
  font-size: 14px;
}

.modern-table :deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #303133;
}

.display-name {
  color: #606266;
}

.email-info {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #606266;
  font-family: 'Consolas', 'Monaco', monospace;
}

.phone-info {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #606266;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.action-buttons .el-button {
  padding: 6px 12px;
  font-size: 13px;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.action-buttons .el-button:hover {
  transform: translateY(-1px);
}

/* 分页优化 */
:deep(.el-pagination) {
  padding: 20px 0;
}

:deep(.el-pagination .el-pager li) {
  border-radius: 6px;
  transition: all 0.3s ease;
}

:deep(.el-pagination .el-pager li.active) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

:deep(.el-pagination .el-pager li:hover) {
  transform: translateY(-1px);
}

/* 对话框优化 */
:deep(.el-dialog) {
  border-radius: 16px;
  overflow: hidden;
}

:deep(.el-dialog__header) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px 24px;
  margin: 0;
}

:deep(.el-dialog__title) {
  color: white;
  font-size: 18px;
  font-weight: 600;
}

:deep(.el-dialog__body) {
  padding: 24px;
}

:deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid #ebeef5;
}

/* 表单优化 */
:deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}

:deep(.el-input__inner) {
  border-radius: 6px;
  border: 1px solid #dcdfe6;
  transition: all 0.3s ease;
}

:deep(.el-input__inner:focus) {
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

/* 按钮优化 */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

:deep(.el-button--primary:hover) {
  opacity: 0.9;
  transform: translateY(-1px);
}

/* Loading 优化 */
:deep(.el-loading-spinner .path) {
  stroke: #667eea;
}

:deep(.el-loading-spinner .el-loading-text) {
  color: #667eea;
  font-weight: 600;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .header-content {
    width: 100%;
  }
}
</style>
