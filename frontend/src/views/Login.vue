<template>
  <div class="login-page">
    <div class="login-bg"></div>
    <div class="login-container">
      <div class="login-card card">
        <div class="login-brand">
          <span class="brand-red">RED</span><span class="brand-scope">SCOPE</span>
        </div>
        <div class="login-subtitle">渗透测试一体化工作台</div>
        <el-form :model="form" @submit.prevent="login" style="margin-top: 28px;">
          <el-form-item>
            <el-input v-model="form.username" placeholder="用户名" size="large" :prefix-icon="User" />
          </el-form-item>
          <el-form-item>
            <el-input v-model="form.password" placeholder="密码" type="password" size="large" show-password :prefix-icon="Lock" />
          </el-form-item>
          <el-button type="primary" style="width: 100%; height: 44px; font-size: 15px;" @click="login" :loading="loading">登录</el-button>
        </el-form>
        <div class="login-footer">RedScope v1.1</div>
        <div style="text-align: center; margin-top: 12px;">
          <span style="font-size: 11px; color: var(--rs-text-secondary); cursor: pointer; opacity: 0.7;" @click="switchToV2">体验新版界面 ✨</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import api from '../stores/api'

const router = useRouter()
const route = useRoute()
const form = ref({ username: '', password: '' })
const loading = ref(false)

function getErrorMsg(e, fallback) {
  const data = e.response?.data
  return data?.detail || data?.error || data?.message || fallback
}

const login = async () => {
  if (!form.value.username || !form.value.password) { ElMessage.warning('请输入用户名和密码'); return }
  loading.value = true
  try {
    const res = await api.post('/auth/login', form.value)
    localStorage.setItem('token', res.access_token)
    router.push(route.query.redirect || '/')
  } catch (e) { ElMessage.error(getErrorMsg(e, '登录失败')) }
  finally { loading.value = false }
}

const switchToV2 = () => {
  localStorage.setItem('rs_ui_version', 'v2')
  router.push('/v2/login')
}
</script>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: #060a12;
}
.login-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 20% 50%, rgba(59, 130, 246, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 20%, rgba(239, 68, 68, 0.06) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 80%, rgba(139, 92, 246, 0.05) 0%, transparent 50%);
}
.login-container { position: relative; z-index: 1; }
.login-card {
  width: 420px;
  padding: 40px 36px 32px;
  border: 1px solid rgba(255,255,255,0.06);
  background: rgba(15, 21, 32, 0.85);
  backdrop-filter: blur(20px);
}
.login-brand {
  text-align: center;
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 4px;
}
.brand-red { color: #ef4444; }
.brand-scope { color: rgba(241, 245, 249, 0.6); }
.login-subtitle {
  text-align: center;
  color: var(--rs-text-secondary);
  font-size: 13px;
  margin-top: 8px;
  letter-spacing: 2px;
}
.login-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 11px;
  color: var(--rs-text-secondary);
  opacity: 0.5;
}
</style>
