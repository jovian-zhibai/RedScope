<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>租户管理</h2>
      <el-button type="primary" @click="showCreate = true"><el-icon><Plus /></el-icon> 新建租户</el-button>
    </div>
    <el-table :data="tenants" style="width: 100%;" @row-click="selectTenant">
      <el-table-column prop="name" label="租户名称" min-width="200" />
      <el-table-column prop="slug" label="标识" width="120" />
      <el-table-column prop="user_count" label="用户数" width="100" />
      <el-table-column prop="max_users" label="用户上限" width="100" />
      <el-table-column prop="max_projects" label="项目上限" width="100" />
      <el-table-column prop="is_active" label="状态" width="80"><template #default="{ row }">{{ row.is_active ? '🟢' : '🔴' }}</template></el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button size="small" type="danger" @click.stop="deleteTenant(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Tenant User Management -->
    <el-drawer v-model="showUsers" :title="`${selectedTenant?.name} - 用户管理`" size="500px">
      <div v-if="selectedTenant" style="padding: 0 8px;">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <el-input v-model="newUserId" placeholder="用户ID" size="small" style="width: 120px;" />
          <el-select v-model="newUserRole" size="small" style="width: 120px;">
            <el-option value="admin" label="管理员" /><el-option value="member" label="成员" />
          </el-select>
          <el-button size="small" type="primary" @click="addTenantUser">添加用户</el-button>
        </div>
        <el-table :data="tenantUsers" style="width: 100%;">
          <el-table-column prop="user_id" label="用户ID" width="80" />
          <el-table-column prop="username" label="用户名" min-width="120" />
          <el-table-column prop="role" label="角色" width="100" />
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button size="small" type="danger" @click="removeTenantUser(row.user_id)">移除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!tenantUsers.length" description="暂无用户" />
      </div>
    </el-drawer>

    <el-dialog v-model="showCreate" title="新建租户" width="480px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="标识"><el-input v-model="form.slug" placeholder="英文标识如 company-a" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" /></el-form-item>
        <el-form-item label="用户上限"><el-input-number v-model="form.max_users" :min="1" /></el-form-item>
        <el-form-item label="项目上限"><el-input-number v-model="form.max_projects" :min="1" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreate = false">取消</el-button><el-button type="primary" @click="create">创建</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../stores/api'

const tenants = ref([]); const showCreate = ref(false); const showUsers = ref(false)
const selectedTenant = ref(null); const tenantUsers = ref([])
const newUserId = ref(''); const newUserRole = ref('member')
const form = ref({ name: '', slug: '', description: '', max_users: 50, max_projects: 100 })

const load = async () => {
  try { const res = await api.get('/tenants'); tenants.value = res.items || [] }
  catch (e) { ElMessage.error('加载失败') }
}

const create = async () => { await api.post('/tenants', form.value); showCreate.value = false; await load() }

const selectTenant = async (row) => {
  selectedTenant.value = row; showUsers.value = true
  try { const res = await api.get(`/tenants/${row.id}/users`); tenantUsers.value = res.items || [] }
  catch (e) { tenantUsers.value = [] }
}

const addTenantUser = async () => {
  if (!newUserId.value) return
  try {
    await api.post(`/tenants/${selectedTenant.value.id}/users`, { user_id: parseInt(newUserId.value), role: newUserRole.value })
    ElMessage.success('已添加')
    await selectTenant(selectedTenant.value)
  } catch (e) { ElMessage.error('添加失败') }
}

const removeTenantUser = async (userId) => {
  await ElMessageBox.confirm('确认移除该用户？', '移除确认', { type: 'warning' })
  await api.delete(`/tenants/${selectedTenant.value.id}/users/${userId}`)
  await selectTenant(selectedTenant.value)
}

const deleteTenant = async (row) => {
  await ElMessageBox.confirm(`确认删除租户「${row.name}」？`, '删除确认', { type: 'warning' })
  await api.delete(`/tenants/${row.id}`)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>
