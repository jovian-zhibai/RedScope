<template>
  <div class="v2-login-page">
    <div class="v2-login-bg"></div>
    <div class="v2-login-grid"></div>
    <div style="position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--rs2-accent) 0%,var(--rs2-danger) 100%);opacity:0.7;"></div>
    <div class="v2-login-card">
      <div style="text-align:center;font-family:var(--rs2-mono);font-size:28px;font-weight:900;letter-spacing:4px;">
        <span style="color:var(--rs2-danger);">RED</span><span style="color:var(--rs2-text-secondary);">SCOPE</span>
      </div>
      <div style="text-align:center;font-size:10px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:var(--rs2-text-muted);margin-top:8px;">
        渗透测试一体化工作台
      </div>
      <el-form :model="form" @submit.prevent="login" style="margin-top: 32px;">
        <el-form-item>
          <div style="width:100%;">
            <div style="margin-bottom:5px;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--rs2-text-muted);">用户名</div>
            <el-input v-model="form.username" placeholder="输入用户名" size="large" />
          </div>
        </el-form-item>
        <el-form-item>
          <div style="width:100%;">
            <div style="margin-bottom:5px;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--rs2-text-muted);">密码</div>
            <el-input v-model="form.password" placeholder="输入密码" type="password" size="large" show-password />
          </div>
        </el-form-item>
        <el-button type="primary" style="width:100%;height:42px;font-size:11px;font-weight:800;letter-spacing:2px;border-radius:2px;" @click="login" :loading="loading">
          登录
        </el-button>
      </el-form>
      <div style="text-align:center;margin-top:24px;font-family:var(--rs2-mono);font-size:9px;color:var(--rs2-text-muted);">
        REDSCOPE v2.0 · STEEL INTEL
      </div>
      <div style="text-align:center;margin-top:12px;">
        <span style="font-size:11px;color:var(--rs2-text-muted);cursor:pointer;" @click="switchToV1">使用旧版界面 →</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../../stores/api'

const router = useRouter()
const route = useRoute()
const form = ref({ username: '', password: '' })
const loading = ref(false)

const login = async () => {
  if (!form.value.username || !form.value.password) { ElMessage.warning('请输入用户名和密码'); return }
  loading.value = true
  try {
    const res = await api.post('/auth/login', form.value)
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('rs_ui_version', 'v2')
    router.push(route.query.redirect || '/v2')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally { loading.value = false }
}

const switchToV1 = () => {
  localStorage.setItem('rs_ui_version', 'v1')
  router.push('/login')
}
</script>
