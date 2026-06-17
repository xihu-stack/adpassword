<template>
  <div class="change-password">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>修改密码</span>
        </div>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="新密码" prop="new_password">
          <el-input 
            v-model="form.new_password" 
            type="password" 
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>
        
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input 
            v-model="form.confirm_password" 
            type="password" 
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading">
            提交
          </el-button>
          <el-button @click="handleReset">重置</el-button>
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

const form = reactive({
  new_password: '',
  confirm_password: '',
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== form.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少 8 位', trigger: 'blur' },
    { 
      pattern: /[a-z]/,
      message: '密码必须包含小写字母',
      trigger: 'blur'
    },
    {
      pattern: /[A-Z]/,
      message: '密码必须包含大写字母',
      trigger: 'blur'
    },
    {
      pattern: /\d/,
      message: '密码必须包含数字',
      trigger: 'blur'
    },
    {
      pattern: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/,
      message: '密码必须包含特殊字符（如：!@#$%^&* 等）',
      trigger: 'blur'
    }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ],
}

const handleSubmit = async () => {
  if (!await formRef.value.validate()) return
  
  loading.value = true
  try {
    await userApi.changePassword(form)
    ElMessage.success('密码修改成功')
    handleReset()
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  formRef.value?.resetFields()
}
</script>

<style scoped>
.change-password {
  max-width: 600px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  font-size: 16px;
}
</style>
