<template>
  <div class="domain-config">
    <div class="page-header">
      <div class="header-content">
        <div class="header-icon">
          <el-icon :size="32"><Server /></el-icon>
        </div>
        <div class="header-text">
          <h2 class="page-title">域配置管理</h2>
          <p class="page-subtitle">Active Directory 域控制器配置</p>
        </div>
      </div>
      <el-button type="primary" class="add-btn" @click="handleAdd">
        <el-icon><Plus /></el-icon>
        添加域配置
      </el-button>
    </div>
    
    <div class="table-card">
      <el-table :data="domains" border stripe class="modern-table" :header-cell-style="{background: '#f5f7fa', color: '#606266', fontWeight: '600'}">
        <el-table-column prop="name" label="域名">
          <template #default="{ row }">
            <div class="domain-name">
              <el-icon><Connection /></el-icon>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="ldap_hosts" label="LDAP 主机">
          <template #default="{ row }">
            <span class="host-info">
              <el-icon><Monitor /></el-icon>
              {{ row.ldap_hosts || row.ldap_host }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="ldap_port" label="端口" width="100">
          <template #default="{ row }">
            <el-tag :type="row.use_ssl ? 'warning' : 'info'" size="small" effect="plain">
              {{ row.ldap_port }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="base_dn" label="Base DN" min-width="200">
          <template #default="{ row }">
            <span class="dn-text">{{ row.base_dn }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="admin_dn" label="管理员 DN" min-width="200">
          <template #default="{ row }">
            <span class="dn-text">{{ row.admin_dn }}</span>
          </template>
        </el-table-column>
        <el-table-column label="SSL" width="100">
          <template #default="{ row }">
            <el-tag :type="row.use_ssl ? 'success' : 'info'" size="small" effect="light">
              <el-icon><Lock v-if="row.use_ssl" /><Unlock v-else /></el-icon>
              {{ row.use_ssl ? '已启用' : '未启用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small" effect="light">
              <el-icon><CircleCheck v-if="row.is_active" /><CircleClose v-else /></el-icon>
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" type="primary" plain @click="handleTest(row)">
                <el-icon><Link /></el-icon>
                测试
              </el-button>
              <el-button size="small" type="success" plain @click="handleEdit(row)">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button size="small" type="danger" plain @click="handleDelete(row)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>
    
    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑域配置' : '添加域配置'" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="域名" prop="name">
          <el-input v-model="form.name" placeholder="例如：公司 AD 域" />
        </el-form-item>
        
        <el-form-item label="LDAP 主机" prop="ldap_hosts">
          <el-input 
            v-model="form.ldap_hosts" 
            placeholder="例如：192.168.1.226,192.168.1.227（多台服务器用逗号分隔）" 
          />
          <div class="form-tip">
            <el-icon><InfoFilled /></el-icon>
            <span>支持配置多台服务器实现故障转移，用逗号或分号分隔（例如：192.168.1.226,192.168.1.227）</span>
          </div>
        </el-form-item>
        
        <el-form-item label="LDAP 端口" prop="ldap_port">
          <div class="port-config">
            <div class="port-input">
              <el-input-number v-model="form.ldap_port" :min="1" :max="65535" :disabled="form.use_ssl" />
            </div>
            <div class="port-tips">
              <el-tag :type="form.use_ssl ? 'info' : 'success'" size="small" effect="plain">
                <el-icon><Connection /></el-icon>
                {{ form.use_ssl ? 'LDAPS 端口：636' : 'LDAP 端口：389' }}
              </el-tag>
            </div>
          </div>
          <div class="form-tip">
            <el-icon><InfoFilled /></el-icon>
            <span>普通 LDAP 端口：389，LDAPS 端口：636</span>
          </div>
        </el-form-item>
        
        <el-form-item label="LDAPS 端口" prop="ldaps_port">
          <div class="port-config">
            <div class="port-input">
              <el-input-number v-model="form.ldaps_port" :min="1" :max="65535" :disabled="!form.use_ssl" />
            </div>
            <div class="port-tips">
              <el-tag :type="form.use_ssl ? 'success' : 'info'" size="small" effect="plain">
                <el-icon><Lock /></el-icon>
                {{ form.use_ssl ? 'SSL 加密已启用' : 'SSL 加密未启用' }}
              </el-tag>
            </div>
          </div>
          <div class="form-tip">
            <el-icon><InfoFilled /></el-icon>
            <span>启用 SSL 加密后自动使用 LDAPS 端口</span>
          </div>
        </el-form-item>
        
        <el-form-item label="SSL 加密" class="ssl-switch-item">
          <div class="ssl-switch-container">
            <div class="switch-left">
              <el-switch v-model="form.use_ssl" class="ssl-switch" inline-prompt active-text="开" inactive-text="关" />
            </div>
            <div class="switch-right">
              <div class="ssl-badge" :class="{ 'ssl-active': form.use_ssl }">
                <el-icon :size="20"><Lock /></el-icon>
                <span>{{ form.use_ssl ? 'LDAPS (SSL 加密)' : 'LDAP (未加密)' }}</span>
              </div>
              <div class="ssl-description">
                <el-icon><Warning /></el-icon>
                <span>启用后会自动切换到 LDAPS 端口 (636)，需要服务器支持 SSL</span>
              </div>
            </div>
          </div>
        </el-form-item>
        
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Connection, Monitor, Lock, Unlock, CircleCheck, CircleClose, Edit, Delete, Link, InfoFilled, Warning } from '@element-plus/icons-vue'
import { adminApi } from '@/api'

const domains = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)

const formRef = ref(null)
const form = reactive({
  id: null,
  name: '',
  ldap_hosts: '',  // 新字段：多主机支持
  ldap_host: '',   // 保留字段以兼容
  ldap_port: 389,
  ldaps_port: 636,
  base_dn: '',
  admin_dn: '',
  admin_password: '',
  use_ssl: false,
  is_active: true,
})

const rules = {
  name: [{ required: true, message: '请输入域名', trigger: 'blur' }],
  ldap_hosts: [{ required: true, message: '请输入 LDAP 主机', trigger: 'blur' }],
  base_dn: [{ required: true, message: '请输入 Base DN', trigger: 'blur' }],
  admin_dn: [{ required: true, message: '请输入管理员 DN', trigger: 'blur' }],
  admin_password: [{ required: true, message: '请输入管理员密码', trigger: 'blur' }],
}

onMounted(async () => {
  await loadDomains()
})

const loadDomains = async () => {
  try {
    const res = await adminApi.getDomains()
    domains.value = res.data
  } catch (error) {
    console.error(error)
  }
}

const handleAdd = () => {
  isEdit.value = false
  Object.assign(form, {
    id: null,
    name: '',
    ldap_host: '',
    ldap_port: 389,
    ldaps_port: 636,
    base_dn: '',
    admin_dn: '',
    admin_password: '',
    use_ssl: false,
    is_active: true,
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  Object.assign(form, { ...row })
  dialogVisible.value = true
}

const handleTest = async (row) => {
  try {
    // 如果是编辑状态，使用输入框中的新密码
    const testConfig = { 
      id: row.id,
      name: row.name,
      ldap_hosts: row.ldap_hosts || row.ldap_host,
      ldap_host: row.ldap_host,
      ldap_port: row.ldap_port,
      ldaps_port: row.ldaps_port || 636,
      base_dn: row.base_dn,
      admin_dn: row.admin_dn,
      use_ssl: row.use_ssl || false,
      is_active: row.is_active,
    }
    
    // 如果当前在编辑对话框中，使用对话框中的密码
    if (dialogVisible.value && isEdit.value && form.id === row.id) {
      if (form.admin_password && form.admin_password.trim() !== '') {
        testConfig.admin_password = form.admin_password
      }
    }
    
    console.log('[测试连接] 发送配置:', testConfig)
    
    const res = await adminApi.testDomain(testConfig)
    if (res.success) {
      ElMessage.success(res.message)
    } else {
      ElMessage.error(res.message)
    }
  } catch (error) {
    console.error('[测试连接] 错误:', error)
    ElMessage.error('测试失败：' + (error.message || '未知错误'))
  }
}

const handleSubmit = async () => {
  if (!await formRef.value.validate()) return
  
  submitting.value = true
  try {
    if (isEdit.value) {
      await adminApi.updateDomain(form.id, form)
      ElMessage.success('更新成功')
    } else {
      await adminApi.createDomain(form)
      ElMessage.success('添加成功')
    }
    
    dialogVisible.value = false
    await loadDomains()
  } catch (error) {
    console.error(error)
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除此域配置吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    
    // TODO: 实现删除 API
    ElMessage.info('删除功能待实现')
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
    }
  }
}
</script>

<style scoped>
.domain-config {
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

.add-btn {
  padding: 12px 24px;
  font-size: 15px;
  font-weight: 500;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  transition: all 0.3s ease;
}

.add-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
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

.domain-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #303133;
}

.host-info {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #606266;
  font-family: 'Consolas', 'Monaco', monospace;
}

.dn-text {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
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

/* 端口配置优化 */
.port-config {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.port-input {
  flex: 1;
}

.port-tips {
  flex-shrink: 0;
}

.port-tips .el-tag {
  padding: 4px 10px;
  font-size: 13px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.port-tips .el-tag .el-icon {
  font-size: 14px;
}

.form-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #909399;
  margin-top: 6px;
}

.form-tip .el-icon {
  color: #667eea;
}

/* SSL 开关优化 */
.ssl-switch-item :deep(.el-form-item__label) {
  display: none;
}

.ssl-switch-item :deep(.el-form-item__content) {
  margin-left: 0 !important;
}

.ssl-switch-container {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%);
  border-radius: 12px;
  border: 2px solid #d0d0d0;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.ssl-switch-container.ssl-active {
  background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
  border-color: #67c23a;
  box-shadow: 0 2px 12px rgba(103, 194, 58, 0.2);
}

.switch-left {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.ssl-switch :deep(.el-switch__core) {
  --el-switch-on-color: #67c23a;
  --el-switch-off-color: #909399;
  height: 28px;
  border-radius: 14px;
  min-width: 56px;
}

.ssl-switch :deep(.el-switch__core .el-switch__action) {
  height: 22px;
  width: 22px;
}

.ssl-switch :deep(.el-switch__label--active) {
  color: #67c23a;
  font-weight: 600;
  font-size: 14px;
}

.ssl-switch :deep(.el-switch__label--inactive) {
  color: #909399;
  font-weight: 600;
  font-size: 14px;
}

.switch-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.ssl-badge {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  font-weight: 600;
  color: #606266;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.ssl-badge.ssl-active {
  color: #2e7d32;
}

.ssl-badge .el-icon {
  color: #667eea;
  flex-shrink: 0;
}

.ssl-badge.ssl-active .el-icon {
  color: #67c23a;
}

.ssl-description {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
}

.ssl-description .el-icon {
  color: #e6a23c;
  flex-shrink: 0;
}

.ssl-description span {
  word-break: break-word;
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

/* 响应式设计 */
@media (max-width: 1200px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .header-content {
    width: 100%;
  }
  
  .add-btn {
    width: 100%;
  }
}
</style>
