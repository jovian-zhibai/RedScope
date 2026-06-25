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
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import api from '../stores/api'
const projects = ref([]); const pid = ref(null)
onMounted(async () => { try { const r = await api.get('/projects'); projects.value = r.items || [] } catch {} })
</script>
