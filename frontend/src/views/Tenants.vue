<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>租户管理</h2>
      <el-button type="primary" @click="showCreate = true"><el-icon><Plus /></el-icon> 新建租户</el-button>
    </div>
    <el-table :data="tenants" style="width: 100%;">
      <el-table-column prop="name" label="租户名称" min-width="200" />
      <el-table-column prop="slug" label="标识" width="120" />
      <el-table-column prop="user_count" label="用户数" width="100" />
      <el-table-column prop="max_users" label="用户上限" width="100" />
      <el-table-column prop="max_projects" label="项目上限" width="100" />
      <el-table-column prop="is_active" label="状态" width="80"><template #default="{ row }">{{ row.is_active ? '🟢' : '🔴' }}</template></el-table-column>
    </el-table>

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
import api from '../stores/api'
const tenants = ref([]); const showCreate = ref(false)
const form = ref({ name: '', slug: '', description: '', max_users: 50, max_projects: 100 })
const load = async () => { const res = await api.get('/tenants'); tenants.value = res.items || [] }
const create = async () => { await api.post('/tenants', form.value); showCreate.value = false; await load() }
onMounted(load)
</script>
