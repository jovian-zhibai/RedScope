<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>资产列表</h2>
      <el-button type="primary" size="small" @click="showAdd = true"><el-icon><Plus /></el-icon> 添加资产</el-button>
    </div>
    <el-table :data="assets" style="width: 100%;">
      <el-table-column prop="host" label="主机" min-width="180" />
      <el-table-column prop="port" label="端口" width="80" />
      <el-table-column prop="application" label="应用" width="150" />
      <el-table-column prop="app_version" label="版本" width="100" />
      <el-table-column prop="server" label="服务" width="120" />
      <el-table-column prop="importance" label="重要性" width="100">
        <template #default="{ row }">
          <span class="severity-badge" :class="row.importance === 'critical' ? 'critical' : row.importance === 'low' ? 'low' : 'medium'">
            {{ {critical:'核心', normal:'一般', low:'低', deprecated:'废弃'}[row.importance] || row.importance }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="scope_status" label="范围" width="100">
        <template #default="{ row }">
          <el-tag :type="row.scope_status === 'in_scope' ? 'success' : row.scope_status === 'pending_confirm' ? 'warning' : 'danger'" size="small">
            {{ {in_scope:'范围内', out_of_scope:'范围外', pending_confirm:'待确认'}[row.scope_status] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_alive" label="存活" width="70">
        <template #default="{ row }">{{ row.is_alive ? '🟢' : '🔴' }}</template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showAdd" title="添加资产" width="480px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="类型">
          <el-select v-model="form.asset_type"><el-option value="ip" label="IP" /><el-option value="domain" label="域名" /><el-option value="url" label="URL" /></el-select>
        </el-form-item>
        <el-form-item label="主机"><el-input v-model="form.host" placeholder="IP或域名" /></el-form-item>
        <el-form-item label="端口"><el-input-number v-model="form.port" :min="1" :max="65535" /></el-form-item>
        <el-form-item label="重要性">
          <el-select v-model="form.importance"><el-option value="critical" label="核心" /><el-option value="normal" label="一般" /><el-option value="low" label="低" /></el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="addAsset">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../stores/api'

const route = useRoute()
const pid = route.params.id
const assets = ref([])
const showAdd = ref(false)
const form = ref({ asset_type: 'ip', host: '', port: null, importance: 'normal' })

const load = async () => { const res = await api.get(`/projects/${pid}/assets`); assets.value = res.items || [] }
const addAsset = async () => { await api.post(`/projects/${pid}/assets`, form.value); showAdd.value = false; await load() }
onMounted(load)
</script>
