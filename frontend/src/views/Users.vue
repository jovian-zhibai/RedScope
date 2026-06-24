<template>
  <div>
    <h2 style="margin-bottom: 16px;">用户管理</h2>
    <el-table :data="users" style="width: 100%;">
      <el-table-column prop="username" label="用户名" width="120" />
      <el-table-column prop="display_name" label="显示名" width="150" />
      <el-table-column prop="role" label="角色" width="120">
        <template #default="{ row }">
          <el-select :model-value="row.role" size="small" @change="updateUser(row.id, { role: $event })">
            <el-option value="admin" label="管理员" /><el-option value="leader" label="组长" />
            <el-option value="engineer" label="工程师" /><el-option value="viewer" label="观察者" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column prop="email" label="邮箱" min-width="180" />
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-switch :model-value="row.is_active" @change="updateUser(row.id, { is_active: $event })" size="small" />
        </template>
      </el-table-column>
      <el-table-column prop="last_login_at" label="最后登录" width="120">
        <template #default="{ row }">{{ row.last_login_at?.split('T')[0] || '从未' }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="120">
        <template #default="{ row }">{{ row.created_at?.split('T')[0] }}</template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const users = ref([])
const load = async () => {
  try { const res = await api.get('/auth/users'); users.value = res.items || [] }
  catch (e) { ElMessage.error(e.response?.data?.detail || '无权限') }
}
const updateUser = async (id, data) => {
  try { await api.put(`/auth/users/${id}`, data); ElMessage.success('已更新'); await load() }
  catch (e) { ElMessage.error('更新失败') }
}
onMounted(load)
</script>
