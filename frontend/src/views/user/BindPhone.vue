<template>
  <div class="bind-phone">
    <el-card>
      <template #header>
        <span>绑定手机号</span>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="手机号码" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入手机号码" />
        </el-form-item>
        
        <el-form-item label="验证码" prop="code">
          <div style="display: flex; gap: 10px;">
            <el-input v-model="form.code" placeholder="请输入验证码" style="flex: 1;" />
            <el-button 
              @click="handleSendCode" 
              :loading="sending"
              :disabled="countdown > 0"
            >
              {{ countdown > 0 ? `${countdown}秒后重试` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading">
            提交
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { userApi } from '@/api'

const formRef = ref(null)
const loading = ref(false)
const sending = ref(false)
const countdown = ref(0)

const form = reactive({
  phone: '',
  code: '',
})

const rules = {
  phone: [
    { required: true, message: '请输入手机号码', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
}

const handleSendCode = async () => {
  if (!form.phone) {
    ElMessage.warning('请输入手机号')
    return
  }
  
  sending.value = true
  try {
    await userApi.sendSmsCode({ phone: form.phone })
    ElMessage.success('验证码已发送')
    
    // 开始倒计时
    countdown.value = 60
    const timer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) {
        clearInterval(timer)
      }
    }, 1000)
  } catch (error) {
    console.error(error)
  } finally {
    sending.value = false
  }
}

const handleSubmit = async () => {
  if (!await formRef.value.validate()) return
  
  loading.value = true
  try {
    await userApi.bindPhone(form)
    ElMessage.success('手机号绑定成功')
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.bind-phone {
  max-width: 600px;
  margin: 0 auto;
}
</style>
