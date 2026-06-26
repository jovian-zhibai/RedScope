<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>手工测试</h2>
      <el-select v-model="pid" placeholder="选择项目" size="small" style="width: 240px;" @change="go">
        <el-option v-for="p in projects" :key="p.id" :value="p.id" :label="p.name" />
      </el-select>
    </div>
    <div v-if="loading" style="text-align: center; padding: 60px; color: var(--rs-text-secondary);">加载中...</div>
    <div v-else-if="!projects.length" style="text-align: center; padding: 40px;">
      <div style="font-size: 48px; margin-bottom: 16px;">📋</div>
      <div style="color: var(--rs-text-secondary); margin-bottom: 12px;">暂无项目</div>
      <el-button type="primary" size="small" @click="$router.push('/projects?action=create')">新建项目</el-button>
    </div>

    <div v-if="playbooks.length" style="margin-top: 24px;">
      <h3 style="margin-bottom: 12px;">Playbook 库（跨项目）</h3>
      <el-table :data="playbooks" style="width: 100%;">
        <el-table-column prop="title" label="名称" min-width="200" />
        <el-table-column prop="commands_count" label="命令数" width="100" />
        <el-table-column prop="project_id" label="来源项目" width="100" />
        <el-table-column prop="recorded_at" label="录制时间" width="160">
          <template #default="{ row }">{{ row.recorded_at?.replace('T', ' ').slice(0, 16) }}</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../stores/api'
const router = useRouter()
const projects = ref([]); const pid = ref(null); const playbooks = ref([]); const loading = ref(true)
const go = () => { if (pid.value) router.push(`/projects/${pid.value}/testing`) }
onMounted(async () => {
  try {
    const r = await api.get('/projects'); projects.value = r.items || []
    if (projects.value.length === 1) { pid.value = projects.value[0].id; go() }
  } catch {}
  try { const r = await api.get('/playbooks'); playbooks.value = r.items || [] } catch {}
  loading.value = false
})
</script>
