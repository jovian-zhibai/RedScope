<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>基线合规扫描</h2>
    </div>
    <div class="stat-grid">
      <div v-for="b in baselines" :key="b.key" class="card" style="cursor: pointer;" @click="selectBaseline(b.key)">
        <h3>{{ b.name }}</h3>
        <div style="color: var(--rs-text-secondary); margin-top: 8px;">{{ b.item_count }} 项检查</div>
        <el-button type="primary" size="small" style="margin-top: 12px;">查看详情</el-button>
      </div>
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
import api from '../stores/api'

const baselines = ref([]); const showDetail = ref(false); const detailName = ref(''); const detailItems = ref([])

const load = async () => { const res = await api.get('/baseline/baselines'); baselines.value = res.items || [] }
const selectBaseline = async (key) => {
  const res = await api.get(`/baseline/baselines/${key}`)
  detailName.value = res.name; detailItems.value = res.items || []; showDetail.value = true
}
onMounted(load)
</script>
