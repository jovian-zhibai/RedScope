<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>扫描任务</h2>
      <el-select v-model="pid" placeholder="选择项目" size="small" style="width: 240px;" @change="load">
        <el-option v-for="p in projects" :key="p.id" :value="p.id" :label="p.name" />
      </el-select>
    </div>
    <div v-if="!pid" style="text-align: center; padding: 60px; color: var(--rs-text-secondary);">请先选择一个项目</div>
    <div v-else>
      <div style="margin-bottom: 12px;">
        <el-button type="primary" size="small" @click="$router.push(`/projects/${pid}/scanning`)">进入扫描管理 →</el-button>
      </div>
      <el-table :data="tasks" style="width: 100%;" @row-click="r => $router.push(`/projects/${pid}/scanning`)">
        <el-table-column prop="task_name" label="任务" min-width="200" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="{pending:'info',running:'warning',completed:'success',failed:'danger',stopped:'danger'}[row.status]" size="small">
              {{ {pending:'等待中',running:'运行中',completed:'已完成',failed:'失败',stopped:'已停止'}[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="120"><template #default="{ row }"><el-progress :percentage="row.progress" :stroke-width="6" /></template></el-table-column>
        <el-table-column prop="vulns_found" label="漏洞" width="80" />
      </el-table>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import api from '../stores/api'
const projects = ref([]); const pid = ref(null); const tasks = ref([])
onMounted(async () => { try { const r = await api.get('/projects'); projects.value = r.items || [] } catch {} })
const load = async () => { if (!pid.value) return; try { const r = await api.get(`/projects/${pid.value}/scans`); tasks.value = r.items || [] } catch { tasks.value = [] } }
</script>
