<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>资产列表</h2>
      <div style="display: flex; gap: 8px;">
        <el-input v-model="searchText" placeholder="搜索主机/IP..." size="small" style="width: 200px;" @input="filterAssets" />
        <el-button type="primary" size="small" @click="showAdd = true"><el-icon><Plus /></el-icon> 添加资产</el-button>
      </div>
    </div>

    <div class="stat-grid" style="margin-bottom: 16px;">
      <div class="stat-card info"><div class="stat-label">总资产</div><div class="stat-value">{{ assets.length }}</div></div>
      <div class="stat-card success"><div class="stat-label">存活</div><div class="stat-value">{{ assets.filter(a => a.is_alive).length }}</div></div>
      <div class="stat-card warning"><div class="stat-label">范围内</div><div class="stat-value">{{ assets.filter(a => a.scope_status === 'in_scope').length }}</div></div>
      <div class="stat-card critical"><div class="stat-label">核心资产</div><div class="stat-value">{{ assets.filter(a => a.importance === 'critical').length }}</div></div>
    </div>

    <el-table :data="pagedAssets" style="width: 100%;" @row-click="openDetail">
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
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" @click.stop="quickScan(row)">扫描</el-button>
          <el-button size="small" type="danger" @click.stop="deleteAsset(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Asset Detail Drawer -->
    <el-pagination v-if="displayAssets.length > pageSize" :current-page="currentPage" :page-size="pageSize" :total="displayAssets.length" @current-change="currentPage = $event" layout="prev, pager, next, total" style="margin-top: 12px; justify-content: flex-end;" />

    <el-drawer v-model="showDetail" :title="detailAsset?.host" size="500px">
      <div v-if="detailAsset" style="padding: 0 8px;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
          <div class="card" style="padding: 12px;">
            <div style="font-size: 12px; color: var(--rs-text-secondary);">类型</div>
            <div>{{ detailAsset.asset_type }}</div>
          </div>
          <div class="card" style="padding: 12px;">
            <div style="font-size: 12px; color: var(--rs-text-secondary);">端口</div>
            <div>{{ detailAsset.port || '-' }}</div>
          </div>
          <div class="card" style="padding: 12px;">
            <div style="font-size: 12px; color: var(--rs-text-secondary);">应用</div>
            <div>{{ detailAsset.application || '-' }} {{ detailAsset.app_version || '' }}</div>
          </div>
          <div class="card" style="padding: 12px;">
            <div style="font-size: 12px; color: var(--rs-text-secondary);">服务</div>
            <div>{{ detailAsset.server || '-' }}</div>
          </div>
          <div class="card" style="padding: 12px;">
            <div style="font-size: 12px; color: var(--rs-text-secondary);">操作系统</div>
            <div>{{ detailAsset.os || '-' }}</div>
          </div>
          <div class="card" style="padding: 12px;">
            <div style="font-size: 12px; color: var(--rs-text-secondary);">存活</div>
            <div>{{ detailAsset.is_alive ? '🟢 存活' : '🔴 不可达' }}</div>
          </div>
        </div>

        <h4 style="margin: 16px 0 8px;">快捷操作</h4>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <el-button size="small" type="primary" @click="quickScan(detailAsset)">端口扫描</el-button>
          <el-button size="small" @click="quickScan(detailAsset, 'deep')">深度扫描</el-button>
        </div>

        <div v-if="detailAsset.fingerprints" style="margin-top: 16px;">
          <h4 style="margin-bottom: 8px;">指纹信息</h4>
          <pre style="font-size: 12px; background: var(--rs-bg-secondary); padding: 12px; border-radius: 6px; overflow: auto;">{{ JSON.stringify(detailAsset.fingerprints, null, 2) }}</pre>
        </div>
      </div>
    </el-drawer>

    <!-- Add Asset Dialog -->
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
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../stores/api'

const route = useRoute()
const router = useRouter()
const pid = route.params.id
const assets = ref([])
const showAdd = ref(false)
const showDetail = ref(false)
const detailAsset = ref(null)
const searchText = ref('')
const form = ref({ asset_type: 'ip', host: '', port: null, importance: 'normal' })

const displayAssets = computed(() => {
  let list = assets.value
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    list = list.filter(a =>
      a.host?.toLowerCase().includes(q) || a.application?.toLowerCase().includes(q) || a.server?.toLowerCase().includes(q)
    )
  }
  return list
})

const pageSize = ref(20)
const currentPage = ref(1)
const pagedAssets = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return displayAssets.value.slice(start, start + pageSize.value)
})

const load = async () => {
  try {
    const res = await api.get(`/projects/${pid}/assets`)
    assets.value = res.items || []
  } catch (e) { ElMessage.error('加载资产失败') }
}

const addAsset = async () => {
  await api.post(`/projects/${pid}/assets`, form.value)
  showAdd.value = false
  await load()
}

const openDetail = (row) => {
  detailAsset.value = row
  showDetail.value = true
}

const deleteAsset = async (row) => {
  await ElMessageBox.confirm(`确认删除资产「${row.host}」？`, '删除确认', { type: 'warning' })
  await api.delete(`/projects/${pid}/assets/${row.id}`)
  ElMessage.success('已删除')
  await load()
}

const quickScan = async (asset, strategy = 'quick') => {
  try {
    await api.post(`/projects/${pid}/scans`, {
      task_name: `扫描 ${asset.host}`,
      scan_strategy: strategy,
      targets: [asset.host + (asset.port ? `:${asset.port}` : '')],
    })
    ElMessage.success('扫描任务已创建')
    showDetail.value = false
  } catch (e) { ElMessage.error('创建扫描失败') }
}

const filterAssets = () => {}

onMounted(load)
</script>
