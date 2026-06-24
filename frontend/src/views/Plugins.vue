<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>工具管理</h2>
      <el-button type="primary" size="small" @click="reloadPlugins"><el-icon><Refresh /></el-icon> 重新加载</el-button>
    </div>
    <el-table :data="plugins" style="width: 100%;">
      <el-table-column prop="display_name" label="工具名称" width="150" />
      <el-table-column prop="version" label="版本" width="100" />
      <el-table-column prop="description" label="描述" min-width="250" />
      <el-table-column prop="category" label="分类" width="100">
        <template #default="{ row }">
          <el-tag size="small">{{ {recon:'侦察',vuln_scan:'漏扫',brute:'爆破',fuzz:'模糊',crawl:'爬虫',custom:'自定义'}[row.category] || row.category }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="docker_image" label="Docker镜像" width="250" />
      <el-table-column prop="proxy_supported" label="代理" width="80">
        <template #default="{ row }">{{ row.proxy_supported ? '✅' : '❌' }}</template>
      </el-table-column>
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch :model-value="row.is_enabled !== false" @change="togglePlugin(row)" size="small" />
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../stores/api'
const plugins = ref([])
const load = async () => { const res = await api.get('/plugins'); plugins.value = res.items || [] }
const reloadPlugins = async () => { const res = await api.post('/plugins/reload'); ElMessage.success(`已加载 ${res.count} 个插件`); await load() }
const togglePlugin = async (row) => {
  try {
    await api.put(`/plugins/${row.id || row.name}/toggle`)
    await load()
  } catch (e) { ElMessage.error('操作失败') }
}
onMounted(load)
</script>
