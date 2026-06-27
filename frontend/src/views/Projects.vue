<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
      <h2>项目管理</h2>
      <div style="display: flex; gap: 8px;">
        <el-button size="small" @click="showTemplates = true">从模板创建</el-button>
        <el-button type="primary" @click="showCreate = true">
          <el-icon><Plus /></el-icon> 新建项目
        </el-button>
      </div>
    </div>

    <el-table :data="pagedProjects" style="width: 100%;" row-class-name="dark-row" @row-click="goToProject">
      <el-table-column prop="name" label="项目名称" min-width="200" />
      <el-table-column prop="mode" label="模式" width="100">
        <template #default="{ row }">
          <span class="severity-badge" :class="row.mode === 'combat' ? 'critical' : row.mode === 'range' ? 'medium' : 'low'">
            {{ {combat: '实战', range: '靶场', research: '研究'}[row.mode] }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="client_name" label="客户" width="150" />
      <el-table-column prop="asset_count" label="资产" width="80" />
      <el-table-column prop="finding_count" label="漏洞" width="80" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : row.status === 'completed' ? 'info' : 'warning'" size="small">
            {{ {active: '进行中', paused: '已暂停', completed: '已完成', archived: '已归档'}[row.status] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="auth_end_date" label="授权截止" width="120" />
      <el-table-column prop="created_at" label="创建时间" width="120">
        <template #default="{ row }">{{ row.created_at?.split('T')[0] }}</template>
      </el-table-column>
    </el-table>
    <el-pagination v-if="projects.length > pageSize" :current-page="currentPage" :page-size="pageSize" :total="projects.length" @current-change="currentPage = $event" layout="prev, pager, next, total" style="margin-top: 12px; justify-content: flex-end;" />

    <el-dialog v-model="showCreate" title="新建项目" width="560px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" placeholder="如: XX公司渗透测试" />
        </el-form-item>
        <el-form-item label="项目模式" required>
          <el-radio-group v-model="form.mode">
            <el-radio-button value="combat">🎯 实战模式</el-radio-button>
            <el-radio-button value="range">🏋️ 靶场模式</el-radio-button>
            <el-radio-button value="research">🔬 研究模式</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <template v-if="form.mode === 'combat'">
          <el-form-item label="客户名称">
            <el-input v-model="form.client_name" />
          </el-form-item>
          <el-form-item label="授权开始">
            <el-date-picker v-model="form.auth_start_date" type="date" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="授权截止">
            <el-date-picker v-model="form.auth_end_date" type="date" value-format="YYYY-MM-DD" />
          </el-form-item>
        </template>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createProject" :loading="creating">创建项目</el-button>
      </template>
    </el-dialog>

    <!-- Templates Dialog -->
    <el-dialog v-model="showTemplates" title="从模板创建项目" width="600px">
      <div v-if="templates.length" style="margin-bottom: 16px;">
        <div v-for="t in templates" :key="t.id" class="card" style="padding: 12px; margin-bottom: 8px; cursor: pointer; display: flex; justify-content: space-between; align-items: center;"
          :style="{ borderLeft: selectedTemplate === t.id ? '3px solid var(--rs-accent)' : '' }"
          @click="selectedTemplate = t.id">
          <div>
            <strong>{{ t.name }}</strong>
            <div style="font-size: 12px; color: var(--rs-text-secondary);">{{ t.description || t.mode }}</div>
          </div>
          <el-tag size="small">{{ {combat:'实战',range:'靶场',research:'研究'}[t.mode] || t.mode }}</el-tag>
        </div>
      </div>
      <el-empty v-else description="暂无模板。在项目详情页可将项目保存为模板。" />
      <el-form v-if="selectedTemplate" label-width="80px" style="margin-top: 12px;">
        <el-form-item label="项目名称"><el-input v-model="templateProjectName" placeholder="新项目名称" /></el-form-item>
        <el-form-item label="客户名称"><el-input v-model="templateClientName" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTemplates = false">取消</el-button>
        <el-button type="primary" :disabled="!selectedTemplate" @click="createFromTemplate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../stores/api'
import { useVersionPrefix } from '../composables/useVersionPrefix'

const router = useRouter()
const route = useRoute()
const { p } = useVersionPrefix()
const projects = ref([])
const showCreate = ref(false)
const creating = ref(false)
const form = ref({ name: '', mode: 'combat', description: '', client_name: '', auth_start_date: '', auth_end_date: '' })
const showTemplates = ref(false)
const templates = ref([])
const selectedTemplate = ref(null)
const templateProjectName = ref('')
const templateClientName = ref('')
const pageSize = ref(20)
const currentPage = ref(1)
const pagedProjects = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return projects.value.slice(start, start + pageSize.value)
})

const loadProjects = async () => {
  try {
    const res = await api.get('/projects')
    projects.value = res.items || []
  } catch (e) { ElMessage.error('加载项目失败') }
}

const createProject = async () => {
  creating.value = true
  try {
    const res = await api.post('/projects', form.value)
    showCreate.value = false
    form.value = { name: '', mode: 'combat', description: '', client_name: '', auth_start_date: '', auth_end_date: '' }
    router.push(p(`/projects/${res.id}`))
  } finally { creating.value = false }
}

const goToProject = (row) => router.push(p(`/projects/${row.id}`))

const loadTemplates = async () => {
  try { const res = await api.get('/templates'); templates.value = res.items || [] } catch {}
}

const createFromTemplate = async () => {
  if (!selectedTemplate.value) return
  try {
    const res = await api.post(`/templates/apply/${selectedTemplate.value}`, {
      name: templateProjectName.value || '新项目',
      client_name: templateClientName.value,
    })
    showTemplates.value = false
    ElMessage.success(`项目已创建: ${res.name}`)
    router.push(p(`/projects/${res.id}`))
  } catch (e) { ElMessage.error('创建失败') }
}

onMounted(async () => {
  await loadProjects()
  await loadTemplates()
  if (route.query.action === 'create') showCreate.value = true
})
</script>
