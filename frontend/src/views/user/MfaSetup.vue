<template>
  <div class="mfa-setup">
    <el-card>
      <template #header>
        <span>MFA 设置</span>
      </template>
      
      <div v-if="!mfaEnabled">
        <div v-if="!setupStarted" style="text-align: center; padding: 40px;">
          <el-icon :size="64" color="#E6A23C"><WarningFilled /></el-icon>
          <p style="margin: 20px 0;">为了您的账号安全，请绑定 Microsoft Authenticator</p>
          <el-button type="primary" @click="handleStartSetup">开始设置</el-button>
        </div>
        
        <div v-else>
          <div style="text-align: center; margin-bottom: 20px;">
            <p>1. 使用 Microsoft Authenticator 扫描下方二维码</p>
            <img v-if="qrCode" :src="`data:image/png;base64,${qrCode}`" alt="QR Code" style="margin: 20px auto;" />
          </div>
          
          <div style="text-align: center; margin-bottom: 20px;">
            <p>2. 输入 Authenticator 中显示的 6 位验证码</p>
            <el-input 
              v-model="code" 
              placeholder="请输入 6 位验证码" 
              maxlength="6"
              style="max-width: 300px; margin: 10px auto;"
            />
          </div>
          
          <div style="text-align: center;">
            <el-button type="primary" @click="handleVerify" :loading="verifying">验证并启用</el-button>
            <el-button @click="setupStarted = false">返回</el-button>
          </div>
          
          <div v-if="backupCodes" style="margin-top: 30px; padding: 20px; background: #f0f9eb; border-radius: 8px;">
            <h4>备用验证码（请妥善保存）</h4>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 10px;">
              <div v-for="(code, index) in backupCodes" :key="index" style="padding: 8px; background: white; border-radius: 4px; text-align: center;">
                {{ code }}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div v-else style="text-align: center; padding: 40px;">
        <el-icon :size="64" color="#67C23A"><CircleCheck /></el-icon>
        <p style="margin: 20px 0;">MFA 已启用</p>
        <el-button type="danger" @click="handleDisable">禁用 MFA</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { userApi } from '@/api'

const mfaEnabled = ref(false)
const setupStarted = ref(false)
const verifying = ref(false)
const qrCode = ref('')
const secret = ref('')
const code = ref('')
const backupCodes = ref([])

const handleStartSetup = async () => {
  try {
    const res = await userApi.setupMfa()
    qrCode.value = res.data.qr_code
    secret.value = res.data.secret
    setupStarted.value = true
  } catch (error) {
    console.error(error)
  }
}

const handleVerify = async () => {
  if (!code.value || code.value.length !== 6) {
    ElMessage.warning('请输入 6 位验证码')
    return
  }
  
  verifying.value = true
  try {
    const res = await userApi.enableMfa({ code: code.value })
    mfaEnabled.value = true
    backupCodes.value = res.data.backup_codes
    ElMessage.success('MFA 启用成功')
  } catch (error) {
    console.error(error)
  } finally {
    verifying.value = false
  }
}

const handleDisable = async () => {
  try {
    const confirm = await ElMessageBox.confirm('确定要禁用 MFA 吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    
    if (confirm) {
      // 需要输入当前 MFA 码来确认
      const { value } = await ElMessageBox.prompt('请输入当前 MFA 验证码以确认禁用', '验证身份', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputPattern: /^\d{6}$/,
        inputErrorMessage: '请输入 6 位数字验证码',
      })
      
      await userApi.disableMfa({ code: value })
      mfaEnabled.value = false
      ElMessage.success('MFA 已禁用')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
    }
  }
}
</script>

<style scoped>
.mfa-setup {
  max-width: 600px;
  margin: 0 auto;
}
</style>
