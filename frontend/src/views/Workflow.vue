<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>工单管理</h2>
      <el-button type="primary" @click="showCreate = true"><el-icon><Plus /></el-icon> 新建工单</el-button>
    </div>

    <div style="display: flex; gap: 8px; margin-bottom: 12px;">
      <el-select v-model="filterStatus" placeholder="状态" clearable size="small" style="width: 120px;" @change="load">
        <el-option value="pending" label="待审批" /><el-option value="approved" label="已审批" />
        <el-option value="in_progress" label="执行中" /><el-option value="completed" label="已完成" />
        <el-option value="rejected" label="已驳回" />
      </el-select>
      <el-select v-model="filterType" placeholder="类型" clearable size="small" style="width: 140px;" @change="load">
        <el-option v-for="(v,k) in typeLabels" :key="k" :value="k" :label="v" />
      </el-select>
      <el-checkbox v-model="showAll" label="显示所有人的工单" size="small" @change="load" />
    </div>

    <el-table :data="filteredOrders" style="width: 100%;" @row-click="selectOrder">
      <el-table-column prop="title" label="工单标题" min-width="200" />
      <el-table-column prop="order_type" label="类型" width="140">
        <template #default="{ row }"><el-tag size="small">{{ typeLabels[row.order_type] || row.order_type }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="priority" label="优先级" width="100">
        <template #default="{ row }"><span class="severity-badge" :class="row.priority === 'urgent' ? 'critical' : row.priority === 'high' ? 'high' : 'medium'">{{ row.priority }}</span></template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="{pending:'warning',approved:'success',in_progress:'primary',review:'info',completed:'success',rejected:'danger'}[row.status]" size="small">
            {{ statusLabels[row.status] || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="120"><template #default="{ row }">{{ row.created_at?.split('T')[0] }}</template></el-table-column>
    </el-table>

    <el-dialog v-model="showCreate" title="新建工单" width="520px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="类型"><el-select v-model="form.order_type">
          <el-option value="pentest_request" label="渗透测试申请" /><el-option value="retest_request" label="复测申请" />
          <el-option value="baseline_check" label="基线检查" /><el-option value="hw_exercise" label="护网演练" />
          <el-option value="emergency_response" label="应急响应" /><el-option value="report_review" label="报告审核" />
        </el-select></el-form-item>
        <el-form-item label="优先级"><el-select v-model="form.priority">
          <el-option value="urgent" label="紧急" /><el-option value="high" label="高" /><el-option value="normal" label="普通" /><el-option value="low" label="低" />
        </el-select></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreate = false">取消</el-button><el-button type="primary" @click="create">提交</el-button></template>
    </el-dialog>

    <el-dialog v-model="showDetail" :title="selectedOrder?.title" width="600px" v-if="selectedOrder">
      <div style="margin-bottom: 16px;">
        <el-tag :type="{pending:'warning',approved:'success',in_progress:'primary',review:'info',completed:'success',rejected:'danger'}[selectedOrder.status]">
          {{ statusLabels[selectedOrder.status] }}
        </el-tag>
        <span style="margin-left: 12px; color: var(--rs-text-secondary);">{{ typeLabels[selectedOrder.order_type] }}</span>
      </div>
      <div v-if="selectedOrder.description" style="margin-bottom: 16px; color: var(--rs-text-secondary); font-size: 13px; white-space: pre-wrap;">{{ selectedOrder.description }}</div>
      <div style="margin-bottom: 16px;">
        <el-button v-for="next in validTransitions[selectedOrder.status] || []" :key="next" size="small" :type="next === 'rejected' ? 'danger' : 'primary'" @click="transition(next)">
          {{ statusLabels[next] }}
        </el-button>
      </div>

      <!-- Comments -->
      <div style="border-top: 1px solid var(--rs-border); padding-top: 12px;">
        <h4 style="margin-bottom: 8px;">评论</h4>
        <div v-for="c in orderComments" :key="c.id" style="padding: 8px 0; border-bottom: 1px solid var(--rs-border); font-size: 13px;">
          <div>{{ c.content }}</div>
          <div style="font-size: 11px; color: var(--rs-text-secondary); margin-top: 4px;">{{ c.username || '用户#' + c.user_id }} · {{ c.created_at?.replace('T', ' ').slice(0, 19) }}</div>
        </div>
        <el-empty v-if="!orderComments.length" description="暂无评论" :image-size="40" />
        <div style="display: flex; gap: 8px; margin-top: 8px;">
          <el-input v-model="newComment" placeholder="添加评论..." size="small" @keyup.enter="addComment" />
          <el-button size="small" type="primary" @click="addComment" :disabled="!newComment.trim()">发送</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const orders = ref([]); const showCreate = ref(false); const showDetail = ref(false); const selectedOrder = ref(null)
const filterStatus = ref(''); const filterType = ref(''); const showAll = ref(true)
const form = ref({ title: '', order_type: 'pentest_request', priority: 'normal', description: '' })
const orderComments = ref([]); const newComment = ref('')
const typeLabels = { pentest_request: '渗透测试', retest_request: '复测', baseline_check: '基线检查', hw_exercise: '护网演练', emergency_response: '应急响应', report_review: '报告审核' }
const statusLabels = { pending: '待审批', approved: '已审批', in_progress: '执行中', review: '待复核', completed: '已完成', rejected: '已驳回' }
const validTransitions = { pending: ['approved', 'rejected'], approved: ['in_progress'], in_progress: ['review', 'completed'], review: ['completed', 'in_progress'] }

const filteredOrders = computed(() => {
  let list = orders.value
  if (filterStatus.value) list = list.filter(o => o.status === filterStatus.value)
  if (filterType.value) list = list.filter(o => o.order_type === filterType.value)
  return list
})

const load = async () => {
  try {
    const params = showAll.value ? {} : { mine: true }
    if (filterStatus.value) params.status = filterStatus.value
    const res = await api.get('/workflow', { params })
    orders.value = res.items || []
  } catch (e) { ElMessage.error('加载失败') }
}
const create = async () => {
  if (!form.value.title) { ElMessage.warning('请输入工单标题'); return }
  try {
    await api.post('/workflow', form.value)
    showCreate.value = false
    ElMessage.success('工单已创建')
    await load()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '创建失败') }
}
const selectOrder = async (row) => {
  try {
    const detail = await api.get(`/workflow/${row.id}`)
    selectedOrder.value = detail
    orderComments.value = detail.comments || []
  } catch {
    selectedOrder.value = row
    orderComments.value = []
  }
  showDetail.value = true
}
const transition = async (status) => {
  try {
    await api.put(`/workflow/${selectedOrder.value.id}/transition`, { new_status: status })
    showDetail.value = false
    await load()
  } catch (e) { ElMessage.error('状态变更失败') }
}
const addComment = async () => {
  if (!newComment.value.trim()) return
  try {
    await api.post(`/workflow/${selectedOrder.value.id}/comments`, { content: newComment.value })
    newComment.value = ''
    const detail = await api.get(`/workflow/${selectedOrder.value.id}`)
    orderComments.value = detail.comments || []
  } catch (e) { ElMessage.error('评论失败') }
}
onMounted(load)
</script>
