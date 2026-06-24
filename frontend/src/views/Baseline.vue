<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>基线合规扫描</h2>
    </div>
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-bottom: 24px;">
      <div v-for="b in baselines" :key="b.key" class="card" style="padding: 16px;">
        <h3>{{ b.name }}</h3>
        <div style="color: var(--rs-text-secondary); margin: 8px 0;">{{ b.item_count }} 项检查</div>
        <div style="display: flex; gap: 8px;">
          <el-button size="small" @click="selectBaseline(b.key)">查看详情</el-button>
          <el-button size="small" type="primary" @click="runBaseline(b.key)">执行检查</el-button>
        </div>
      </div>
    </div>

    <!-- Results -->
    <div v-if="scanResults.length" class="card" style="padding: 16px; margin-bottom: 16px;">
      <h3 style="margin-bottom: 12px;">检查结果</h3>
      <div class="stat-grid" style="margin-bottom: 12px;">
        <div class="stat-card success"><div class="stat-label">通过</div><div class="stat-value">{{ scanResults.filter(r => r.status === 'pass').length }}</div></div>
        <div class="stat-card critical"><div class="stat-label">未通过</div><div class="stat-value">{{ scanResults.filter(r => r.status === 'fail').length }}</div></div>
        <div class="stat-card warning"><div class="stat-label">警告</div><div class="stat-value">{{ scanResults.filter(r => r.status === 'warn').length }}</div></div>
        <div class="stat-card info"><div class="stat-label">跳过</div><div class="stat-value">{{ scanResults.filter(r => r.status === 'skip').length }}</div></div>
      </div>
      <el-table :data="scanResults" style="width: 100%;">
        <el-table-column prop="title" label="检查项" min-width="250" />
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column prop="status" label="结果" width="80">
          <template #default="{ row }">
            <el-tag :type="{pass:'success',fail:'danger',warn:'warning',skip:'info'}[row.status]" size="small">
              {{ {pass:'通过',fail:'不合规',warn:'警告',skip:'跳过'}[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="severity" label="等级" width="80">
          <template #default="{ row }"><span class="severity-badge" :class="row.severity">{{ row.severity }}</span></template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" min-width="200">
          <template #default="{ row }"><span style="font-size: 12px; color: var(--rs-text-secondary);">{{ row.detail }}</span></template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showDetail" :title="detailName" width="800px">
      <el-table :data="detailItems" style="width: 100%;">
        <el-table-column prop="id" label="编号" width="100" />
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column prop="title" label="检查项" min-width="200" />
        <el-table-column prop="severity" label="等级" width="80">
          <template #default="{ row }"><span class="severity-badge" :class="row.severity">{{ row.severity }}</span></template>
        </el-table-column>
        <el-table-column prop="check_command" label="检查命令" min-width="300">
          <template #default="{ row }"><code style="font-size: 12px; color: var(--rs-accent);">{{ row.check_command }}</code></template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const baselines = ref([]); const showDetail = ref(false); const detailName = ref(''); const detailItems = ref([])
const scanResults = ref([])

const load = async () => {
  try { const res = await api.get('/baseline/baselines'); baselines.value = res.items || [] }
  catch (e) { ElMessage.error('加载失败') }
}

const selectBaseline = async (key) => {
  const res = await api.get(`/baseline/baselines/${key}`)
  detailName.value = res.name; detailItems.value = res.items || []; showDetail.value = true
}

const runBaseline = async (key) => {
  ElMessage.info('正在执行基线检查...')
  try {
    const res = await api.post(`/baseline/baselines/${key}/run`)
    scanResults.value = res.results || []
    const failed = scanResults.value.filter(r => r.status === 'fail').length
    if (failed > 0) ElMessage.warning(`检查完成: ${failed} 项不合规`)
    else ElMessage.success('所有检查项均合规')
  } catch (e) { ElMessage.error('执行失败') }
}

onMounted(load)
</script>
