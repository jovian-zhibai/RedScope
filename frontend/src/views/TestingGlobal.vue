<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>手工测试</h2>
      <el-select v-model="pid" placeholder="选择项目" size="small" style="width: 240px;" @change="pid && $router.push(`/projects/${pid}/testing`)">
        <el-option v-for="p in projects" :key="p.id" :value="p.id" :label="p.name" />
      </el-select>
    </div>
    <div v-if="!pid" style="text-align: center; padding: 60px; color: var(--rs-text-secondary);">
      <div style="font-size: 48px; margin-bottom: 16px;">📋</div>
      <div>选择一个项目进入手工测试（Checklist / Payload / 笔记 / 任务分工）</div>
    </div>

    <!-- Global Playbooks -->
    <div style="margin-top: 24px;">
      <h3 style="margin-bottom: 12px;">Playbook 库（跨项目）</h3>
      <el-table :data="playbooks" style="width: 100%;">
        <el-table-column prop="title" label="名称" min-width="200" />
        <el-table-column prop="commands_count" label="命令数" width="100" />
        <el-table-column prop="project_id" label="来源项目" width="100" />
        <el-table-column prop="recorded_at" label="录制时间" width="160">
          <template #default="{ row }">{{ row.recorded_at?.replace('T', ' ').slice(0, 16) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!playbooks.length" description="暂无 Playbook。在项目工作 Session 中可将终端录制保存为 Playbook。" :image-size="40" />
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import api from '../stores/api'
const projects = ref([]); const pid = ref(null); const playbooks = ref([])
onMounted(async () => {
  try { const r = await api.get('/projects'); projects.value = r.items || [] } catch {}
  try { const r = await api.get('/playbooks'); playbooks.value = r.items || [] } catch {}
})
</script>
