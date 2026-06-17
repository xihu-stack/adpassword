<template>
  <div class="sms-config">
    <h2>短信配置</h2>
    
    <el-card>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="Access Key" prop="access_key">
          <el-input v-model="form.access_key" placeholder="阿里云 AccessKey ID" />
        </el-form-item>
        
        <el-form-item label="Access Secret" prop="access_secret">
          <el-input v-model="form.access_secret" type="password" show-password placeholder="阿里云 AccessKey Secret" />
        </el-form-item>
        
        <el-form-item label="签名名称" prop="sign_name">
          <el-input v-model="form.sign_name" placeholder="例如：XX 公司" />
        </el-form-item>
        
        <el-form-item label="模板代码" prop="template_code">
          <el-input v-model="form.template_code" placeholder="例如：SMS_123456789" />
        </el-form-item>
        
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading">保存配置</el-button>
        </el-form-item>
      </el-form>
      
      <el-alert
        title="配置说明"
        type="info"
        :closable="false"
        style="margin-top: 20px;"
      >
        <p>1. 需要在阿里云控制台申请短信服务</p>
        <p>2. 创建短信签名和模板</p>
        <p>3. 模板变量需要包含 code 字段用于验证码</p>
      </el-alert>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '@/api'

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  access_key: '',
  access_secret: '',
  sign_name: '',
  template_code: '',
  is_active: true,
})

const rules = {
  access_key: [{ required: true, message: '请输入 Access Key', trigger: 'blur' }],
  access_secret: [{ required: true, message: '请输入 Access Secret', trigger: 'blur' }],
  sign_name: [{ required: true, message: '请输入签名名称', trigger: 'blur' }],
  template_code: [{ required: true, message: '请输入模板代码', trigger: 'blur' }],
}

onMounted(async () => {
  await loadConfig()
})

const loadConfig = async () => {
  try {
    const res = await adminApi.getSmsConfig()
    if (res.data) {
      Object.assign(form, res.data)
    }
  } catch (error) {
    console.error(error)
  }
}

const handleSubmit = async () => {
  if (!await formRef.value.validate()) return
  
  loading.value = true
  try {
    await adminApi.saveSmsConfig(form)
    ElMessage.success('配置保存成功')
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.sms-config h2 {
  margin-bottom: 20px;
  color: #303133;
}
</style>
