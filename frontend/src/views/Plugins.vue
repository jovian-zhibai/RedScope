<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>工具管理</h2>
      <div style="display: flex; gap: 8px;">
        <el-select v-model="filterCategory" placeholder="分类筛选" clearable size="small" style="width: 120px;">
          <el-option value="recon" label="侦察" /><el-option value="vuln_scan" label="漏扫" />
          <el-option value="brute" label="爆破" /><el-option value="fuzz" label="模糊" /><el-option value="custom" label="自定义" />
        </el-select>
        <el-button size="small" @click="showAdd = true"><el-icon><Plus /></el-icon> 添加自定义工具</el-button>
        <el-button type="primary" size="small" @click="reloadPlugins"><el-icon><Refresh /></el-icon> 重新加载</el-button>
      </div>
    </div>
    <el-table :data="filteredPlugins" style="width: 100%;">
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

    <!-- Add Custom Tool Dialog -->
    <el-dialog v-model="showAdd" title="添加自定义工具" width="640px">
      <el-form :model="toolForm" label-width="100px">
        <el-form-item label="工具名称" required><el-input v-model="toolForm.name" placeholder="如 my-scanner (英文,无空格)" /></el-form-item>
        <el-form-item label="显示名称" required><el-input v-model="toolForm.display_name" placeholder="如 我的扫描器" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="toolForm.description" /></el-form-item>
        <el-form-item label="分类">
          <el-select v-model="toolForm.category">
            <el-option value="recon" label="侦察" /><el-option value="vuln_scan" label="漏扫" />
            <el-option value="brute" label="爆破" /><el-option value="fuzz" label="模糊测试" />
            <el-option value="custom" label="自定义" />
          </el-select>
        </el-form-item>
        <el-form-item label="运行模式">
          <el-radio-group v-model="toolForm.run_mode">
            <el-radio value="docker">Docker 容器</el-radio>
            <el-radio value="local">本地命令</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="toolForm.run_mode === 'docker'" label="Docker 镜像"><el-input v-model="toolForm.docker_image" placeholder="如 my-tool:latest" /></el-form-item>
        <el-form-item v-if="toolForm.run_mode === 'local'" label="本地路径">
          <el-input v-model="toolForm.local_binary" placeholder="如 /usr/local/bin/my-tool 或 python3 /opt/scripts/scan.py" />
          <div style="font-size: 11px; color: var(--rs-text-secondary); margin-top: 4px;">支持: 二进制、Python脚本、Shell脚本</div>
        </el-form-item>
        <el-form-item label="执行命令" required>
          <el-input v-model="toolForm.command" placeholder="如 my-tool scan {target} -o /output/result.json" />
          <div style="font-size: 11px; color: var(--rs-text-secondary); margin-top: 4px;">可用变量: {target} {url} {domain} {extra_args}</div>
        </el-form-item>
        <el-form-item label="输出格式">
          <el-select v-model="toolForm.output_format">
            <el-option value="json" /><el-option value="xml" /><el-option value="text" /><el-option value="csv" />
          </el-select>
        </el-form-item>
        <el-form-item label="输出路径"><el-input v-model="toolForm.output_path" placeholder="/output/result.json" /></el-form-item>
        <el-form-item label="支持代理"><el-switch v-model="toolForm.proxy_supported" /></el-form-item>
        <el-form-item v-if="toolForm.proxy_supported" label="代理参数"><el-input v-model="toolForm.proxy_flag" placeholder="如 --proxy {proxy_url}" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="addTool" :loading="adding">添加工具</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const plugins = ref([])
const filterCategory = ref('')
const filteredPlugins = computed(() => {
  if (!filterCategory.value) return plugins.value
  return plugins.value.filter(p => p.category === filterCategory.value)
})
const showAdd = ref(false)
const adding = ref(false)
const toolForm = ref({
  name: '', display_name: '', description: '', category: 'custom',
  run_mode: 'docker', docker_image: '', local_binary: '',
  command: '', output_format: 'json', output_path: '/output/result.json',
  proxy_supported: false, proxy_flag: '',
})

const load = async () => { const res = await api.get('/plugins'); plugins.value = res.items || [] }
const reloadPlugins = async () => { const res = await api.post('/plugins/reload'); ElMessage.success(`已加载 ${res.count} 个插件`); await load() }
const togglePlugin = async (row) => {
  try { await api.put(`/plugins/${row.id || row.name}/toggle`); await load() }
  catch (e) { ElMessage.error('操作失败') }
}

const addTool = async () => {
  if (!toolForm.value.name || !toolForm.value.command) {
    ElMessage.warning('请填写工具名称和执行命令')
    return
  }
  if (toolForm.value.run_mode === 'docker' && !toolForm.value.docker_image) {
    ElMessage.warning('Docker 模式请填写镜像名称')
    return
  }
  if (toolForm.value.run_mode === 'local' && !toolForm.value.local_binary) {
    ElMessage.warning('本地模式请填写命令路径')
    return
  }
  adding.value = true
  try {
    await api.post('/plugins/custom', toolForm.value)
    showAdd.value = false
    ElMessage.success('工具已添加，正在重新加载...')
    toolForm.value = { name: '', display_name: '', description: '', category: 'custom', docker_image: '', command: '', output_format: 'json', output_path: '/output/result.json', proxy_supported: false, proxy_flag: '' }
    await reloadPlugins()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '添加失败') }
  finally { adding.value = false }
}

onMounted(load)
</script>
