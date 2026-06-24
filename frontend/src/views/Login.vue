<template>
  <div style="display: flex; justify-content: center; align-items: center; height: 100vh; background: var(--rs-bg-primary);">
    <div class="card" style="width: 400px;">
      <h2 style="text-align: center; color: var(--rs-danger); margin-bottom: 24px;">⚡ RedScope</h2>
      <el-form :model="form" @submit.prevent="login">
        <el-form-item><el-input v-model="form.username" placeholder="用户名" size="large" /></el-form-item>
        <el-form-item><el-input v-model="form.password" placeholder="密码" type="password" size="large" show-password /></el-form-item>
        <el-button type="primary" style="width: 100%;" size="large" @click="login" :loading="loading">登录</el-button>
        <el-button style="width: 100%; margin-top: 8px;" size="large" @click="register">注册</el-button>
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

const login = async () => {
  loading.value = true
  try {
    const res = await api.post('/auth/login', form.value)
    localStorage.setItem('token', res.access_token)
    router.push('/')
  } catch (e) { ElMessage.error(e.response?.data?.detail || '登录失败') }
  finally { loading.value = false }
}

const register = async () => {
  try {
    const res = await api.post('/auth/register', form.value)
    localStorage.setItem('token', res.access_token)
    ElMessage.success('注册成功')
    router.push('/')
  } catch (e) { ElMessage.error(e.response?.data?.detail || '注册失败') }
}
</script>
