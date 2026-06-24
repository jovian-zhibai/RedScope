<template>
  <div style="max-width: 600px;">
    <h2 style="margin-bottom: 20px;">个人设置</h2>
    <div class="card" style="padding: 20px; margin-bottom: 16px;">
      <h3 style="margin-bottom: 16px;">基本信息</h3>
      <el-form :model="profile" label-width="80px">
        <el-form-item label="用户名"><el-input :model-value="profile.username" disabled /></el-form-item>
        <el-form-item label="角色"><el-tag>{{ profile.role }}</el-tag></el-form-item>
        <el-form-item label="显示名"><el-input v-model="profile.display_name" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="profile.email" /></el-form-item>
        <el-form-item label="手机"><el-input v-model="profile.phone" /></el-form-item>
        <el-form-item><el-button type="primary" @click="saveProfile" :loading="saving">保存</el-button></el-form-item>
      </el-form>
    </div>
    <div class="card" style="padding: 20px;">
      <h3 style="margin-bottom: 16px;">修改密码</h3>
      <el-form :model="pwdForm" label-width="80px">
        <el-form-item label="原密码"><el-input v-model="pwdForm.old_password" type="password" show-password /></el-form-item>
        <el-form-item label="新密码"><el-input v-model="pwdForm.new_password" type="password" show-password placeholder="至少8位，含字母+数字" /></el-form-item>
        <el-form-item label="确认密码"><el-input v-model="pwdForm.confirm" type="password" show-password /></el-form-item>
        <el-form-item>
          <el-button type="warning" @click="changePassword" :loading="changingPwd">修改密码</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const profile = ref({ username: '', display_name: '', email: '', phone: '', role: '' })
const pwdForm = ref({ old_password: '', new_password: '', confirm: '' })
const saving = ref(false)
const changingPwd = ref(false)

onMounted(async () => {
  try { profile.value = await api.get('/auth/me') } catch (e) { ElMessage.error('加载失败') }
})

const saveProfile = async () => {
  saving.value = true
  try {
    await api.put('/auth/me', { display_name: profile.value.display_name, email: profile.value.email, phone: profile.value.phone })
    ElMessage.success('保存成功')
  } catch (e) { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

const changePassword = async () => {
  if (pwdForm.value.new_password !== pwdForm.value.confirm) { ElMessage.warning('两次密码不一致'); return }
  if (pwdForm.value.new_password.length < 8) { ElMessage.warning('新密码至少8位'); return }
  changingPwd.value = true
  try {
    await api.post('/auth/change-password', { old_password: pwdForm.value.old_password, new_password: pwdForm.value.new_password })
    ElMessage.success('密码修改成功')
    pwdForm.value = { old_password: '', new_password: '', confirm: '' }
  } catch (e) { ElMessage.error(e.response?.data?.detail || '修改失败') }
  finally { changingPwd.value = false }
}
</script>
