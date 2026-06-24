<template>
  <div>
    <h2 style="margin-bottom: 16px;">手工测试</h2>
    <el-tabs v-model="activeTab">
      <!-- Checklists -->
      <el-tab-pane label="测试清单" name="checklists">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <el-button type="primary" size="small" @click="initBuiltin" :loading="initing">初始化内置清单</el-button>
          <el-select v-model="selectedChecklist" placeholder="选择清单" size="small" style="width: 220px;" @change="loadChecklistDetail">
            <el-option v-for="c in checklists" :key="c.id" :value="c.id" :label="`${c.name} (${c.item_count}项)`" />
          </el-select>
        </div>

        <div v-if="checklistItems.length">
          <div style="margin-bottom: 12px; color: var(--rs-text-secondary); font-size: 13px;">
            已完成 {{ checkedCount }} / {{ checklistItems.length }} 项
            <el-progress :percentage="Math.round(checkedCount / checklistItems.length * 100)" :stroke-width="6" style="margin-top: 4px;" />
          </div>
          <el-table :data="checklistItems" style="width: 100%;" row-key="index">
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag v-if="row.result === 'vuln'" type="danger" size="small">有漏洞</el-tag>
                <el-tag v-else-if="row.result === 'safe'" type="success" size="small">安全</el-tag>
                <el-tag v-else-if="row.result === 'na'" type="info" size="small">N/A</el-tag>
                <el-tag v-else size="small">待测</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="测试项" min-width="200" />
            <el-table-column prop="category" label="分类" width="100" />
            <el-table-column prop="method" label="测试方法" min-width="300">
              <template #default="{ row }">
                <span style="font-size: 12px; color: var(--rs-text-secondary);">{{ row.method }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="severity" label="等级" width="80">
              <template #default="{ row }"><span class="severity-badge" :class="row.severity">{{ row.severity }}</span></template>
            </el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button-group size="small">
                  <el-button :type="row.result === 'vuln' ? 'danger' : ''" @click="markResult(row, 'vuln')">有漏洞</el-button>
                  <el-button :type="row.result === 'safe' ? 'success' : ''" @click="markResult(row, 'safe')">安全</el-button>
                  <el-button :type="row.result === 'na' ? 'info' : ''" @click="markResult(row, 'na')">N/A</el-button>
                </el-button-group>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-else-if="selectedChecklist" description="清单为空" />
        <el-empty v-else description="请选择或初始化测试清单" />
      </el-tab-pane>

      <!-- Payloads -->
      <el-tab-pane label="Payload 武器库" name="payloads">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <el-select v-model="payloadCategory" placeholder="按分类筛选" size="small" clearable style="width: 160px;" @change="loadPayloads">
            <el-option v-for="c in ['sqli','xss','rce','lfi','ssrf','xxe','auth','file_upload']" :key="c" :value="c" :label="c.toUpperCase()" />
          </el-select>
          <el-button type="primary" size="small" @click="showPayloadForm = true"><el-icon><Plus /></el-icon> 添加 Payload</el-button>
        </div>
        <el-table :data="payloads" style="width: 100%;">
          <el-table-column prop="name" label="名称" min-width="180" />
          <el-table-column prop="category" label="分类" width="100">
            <template #default="{ row }"><el-tag size="small">{{ row.category }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="content" label="Payload" min-width="350">
            <template #default="{ row }">
              <code style="font-size: 12px; color: var(--rs-danger); background: var(--rs-bg-secondary); padding: 2px 6px; border-radius: 3px; word-break: break-all;">{{ row.content }}</code>
            </template>
          </el-table-column>
          <el-table-column prop="applicable_scene" label="适用场景" width="150" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" @click="copyPayload(row.content)">复制</el-button>
              <el-button size="small" type="danger" @click="deletePayload(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!payloads.length" description="暂无 Payload" />

        <el-dialog v-model="showPayloadForm" title="添加 Payload" width="520px">
          <el-form :model="payloadForm" label-width="100px">
            <el-form-item label="名称"><el-input v-model="payloadForm.name" /></el-form-item>
            <el-form-item label="分类">
              <el-select v-model="payloadForm.category">
                <el-option v-for="c in ['sqli','xss','rce','lfi','ssrf','xxe','auth','file_upload']" :key="c" :value="c" :label="c.toUpperCase()" />
              </el-select>
            </el-form-item>
            <el-form-item label="Payload"><el-input v-model="payloadForm.content" type="textarea" :rows="4" /></el-form-item>
            <el-form-item label="适用场景"><el-input v-model="payloadForm.applicable_scene" /></el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showPayloadForm = false">取消</el-button>
            <el-button type="primary" @click="createPayload">保存</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <!-- Notes -->
      <el-tab-pane label="测试笔记" name="notes">
        <div style="margin-bottom: 16px;">
          <el-input v-model="newNote" type="textarea" :rows="3" placeholder="记录测试过程、发现、思路..." />
          <el-button type="primary" size="small" style="margin-top: 8px;" @click="createNote" :disabled="!newNote.trim()">添加笔记</el-button>
        </div>
        <div v-for="n in notes" :key="n.id" class="card" style="padding: 12px; margin-bottom: 8px;">
          <div style="white-space: pre-wrap; font-size: 13px;">{{ n.content }}</div>
          <div style="font-size: 11px; color: var(--rs-text-secondary); margin-top: 8px;">{{ n.created_at }}</div>
        </div>
        <el-empty v-if="!notes.length" description="暂无笔记" />
      </el-tab-pane>

      <!-- Task Assignments -->
      <el-tab-pane label="任务分工" name="assignments">
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <el-button type="primary" size="small" @click="showAssignForm = true"><el-icon><Plus /></el-icon> 分配任务</el-button>
        </div>
        <el-table :data="assignments" style="width: 100%;">
          <el-table-column prop="module_name" label="测试模块" min-width="180" />
          <el-table-column prop="assigned_to" label="负责人" width="120" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : 'warning'" size="small">
                {{ row.status === 'completed' ? '已完成' : '进行中' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="started_at" label="开始时间" width="160" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button v-if="row.status !== 'completed'" size="small" type="success" @click="completeAssignment(row.id)">完成</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!assignments.length" description="暂无任务分工" />

        <el-dialog v-model="showAssignForm" title="分配任务" width="420px">
          <el-form :model="assignForm" label-width="80px">
            <el-form-item label="模块"><el-input v-model="assignForm.module_name" placeholder="如：SQL注入测试" /></el-form-item>
            <el-form-item label="负责人"><el-input v-model="assignForm.assigned_to" placeholder="用户名" /></el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showAssignForm = false">取消</el-button>
            <el-button type="primary" @click="createAssignment">分配</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const route = useRoute()
const pid = route.params.id
const activeTab = ref('checklists')

// Checklists
const checklists = ref([])
const selectedChecklist = ref(null)
const checklistItems = ref([])
const checklistResults = ref({})
const initing = ref(false)

const checkedCount = computed(() => checklistItems.value.filter(i => i.result).length)

const loadChecklists = async () => {
  const res = await api.get('/testing/checklists')
  checklists.value = res.items || []
}

const initBuiltin = async () => {
  initing.value = true
  try {
    const res = await api.post('/testing/checklists/init-builtin')
    ElMessage.success(`已初始化 ${res.initialized} 个内置清单`)
    await loadChecklists()
  } finally { initing.value = false }
}

const loadChecklistDetail = async (id) => {
  if (!id) return
  const [detail, results] = await Promise.all([
    api.get(`/testing/checklists/${id}`),
    api.get(`/testing/checklists/${id}/results`, { params: { project_id: pid } }),
  ])
  const resultMap = {}
  for (const r of (results.items || [])) { resultMap[r.item_index] = r.result }
  checklistItems.value = (detail.items || []).map((item, i) => ({ ...item, index: i, result: resultMap[i] || null }))
}

const markResult = async (row, result) => {
  row.result = result
  await api.post(`/testing/checklists/${selectedChecklist.value}/results`, {
    project_id: parseInt(pid), item_index: row.index, result,
  })
}

// Payloads
const payloads = ref([])
const payloadCategory = ref('')
const showPayloadForm = ref(false)
const payloadForm = ref({ name: '', category: 'sqli', content: '', applicable_scene: '' })

const loadPayloads = async () => {
  const params = payloadCategory.value ? { category: payloadCategory.value } : {}
  const res = await api.get('/testing/payloads', { params })
  payloads.value = res.items || []
}

const createPayload = async () => {
  await api.post('/testing/payloads', payloadForm.value)
  showPayloadForm.value = false
  payloadForm.value = { name: '', category: 'sqli', content: '', applicable_scene: '' }
  await loadPayloads()
}

const deletePayload = async (id) => {
  await api.delete(`/testing/payloads/${id}`)
  await loadPayloads()
}

const copyPayload = (content) => {
  navigator.clipboard.writeText(content)
  ElMessage.success('已复制')
}

// Notes
const notes = ref([])
const newNote = ref('')

const loadNotes = async () => {
  const res = await api.get('/testing/notes', { params: { project_id: pid } })
  notes.value = res.items || []
}

const createNote = async () => {
  await api.post('/testing/notes', { project_id: parseInt(pid), content: newNote.value })
  newNote.value = ''
  await loadNotes()
}

// Assignments
const assignments = ref([])
const showAssignForm = ref(false)
const assignForm = ref({ module_name: '', assigned_to: '' })

const loadAssignments = async () => {
  const res = await api.get('/testing/assignments', { params: { project_id: pid } })
  assignments.value = res.items || []
}

const createAssignment = async () => {
  await api.post('/testing/assignments', { project_id: parseInt(pid), ...assignForm.value })
  showAssignForm.value = false
  assignForm.value = { module_name: '', assigned_to: '' }
  await loadAssignments()
}

const completeAssignment = async (id) => {
  await api.put(`/testing/assignments/${id}/complete`)
  await loadAssignments()
}

onMounted(async () => {
  await Promise.all([loadChecklists(), loadPayloads(), loadNotes(), loadAssignments()])
})
</script>
