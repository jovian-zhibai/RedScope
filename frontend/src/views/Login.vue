<template>
  <div style="display: flex; justify-content: center; align-items: center; height: 100vh; background: var(--rs-bg-primary);">
    <div class="card" style="width: 400px;">
      <h2 style="text-align: center; color: var(--rs-danger); margin-bottom: 24px;">⚡ RedScope</h2>
      <el-form :model="form" @submit.prevent="login">
        <el-form-item><el-input v-model="form.username" placeholder="用户名（至少3位）" size="large" /></el-form-item>
        <el-form-item><el-input v-model="form.password" placeholder="密码（至少8位，含字母+数字）" type="password" size="large" show-password /></el-form-item>
        <el-button type="primary" style="width: 100%;" size="large" @click="login" :loading="loading">登录</el-button>
        <el-button style="width: 100%; margin-top: 8px;" size="large" @click="register" :loading="registering">注册</el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const router = useRouter()
const form = ref({ username: '', password: '' })
const loading = ref(false)
const registering = ref(false)

function getErrorMsg(e, fallback) {
  const data = e.response?.data
  return data?.detail || data?.error || data?.message || fallback
}

const login = async () => {
  loading.value = true
  try {
    const res = await api.post('/auth/login', form.value)
    localStorage.setItem('token', res.access_token)
    router.push('/')
  } catch (e) { ElMessage.error(getErrorMsg(e, '登录失败')) }
  finally { loading.value = false }
}

const register = async () => {
  if (form.value.username.length < 3) { ElMessage.warning('用户名至少3位'); return }
  if (form.value.password.length < 8) { ElMessage.warning('密码至少8位'); return }

  registering.value = true
  try {
    const res = await api.post('/auth/register', form.value)
    localStorage.setItem('token', res.access_token)
    ElMessage.success('注册成功')
    router.push('/')
  } catch (e) { ElMessage.error(getErrorMsg(e, '注册失败')) }
  finally { registering.value = false }
}
</script>
