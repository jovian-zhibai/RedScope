<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>工单管理</h2>
      <el-button type="primary" @click="showCreate = true"><el-icon><Plus /></el-icon> 新建工单</el-button>
    </div>
    <el-table :data="orders" style="width: 100%;" @row-click="selectOrder">
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
        <span style="margin-left: 12px; color: var(--rs-text-secondary);">{{ selectedOrder.order_type }}</span>
      </div>
      <div style="margin-bottom: 16px;">
        <el-button v-for="next in validTransitions[selectedOrder.status] || []" :key="next" size="small" :type="next === 'rejected' ? 'danger' : 'primary'" @click="transition(next)">
          {{ statusLabels[next] }}
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const orders = ref([]); const showCreate = ref(false); const showDetail = ref(false); const selectedOrder = ref(null)
const form = ref({ title: '', order_type: 'pentest_request', priority: 'normal', description: '' })
const typeLabels = { pentest_request: '渗透测试', retest_request: '复测', baseline_check: '基线检查', hw_exercise: '护网演练', emergency_response: '应急响应', report_review: '报告审核' }
const statusLabels = { pending: '待审批', approved: '已审批', in_progress: '执行中', review: '待复核', completed: '已完成', rejected: '已驳回' }
const validTransitions = { pending: ['approved', 'rejected'], approved: ['in_progress'], in_progress: ['review', 'completed'], review: ['completed', 'in_progress'] }

const load = async () => { const res = await api.get('/workflow'); orders.value = res.items || [] }
const create = async () => { await api.post('/workflow', form.value); showCreate.value = false; ElMessage.success('工单已创建'); await load() }
const selectOrder = (row) => { selectedOrder.value = row; showDetail.value = true }
const transition = async (status) => { await api.put(`/workflow/${selectedOrder.value.id}/transition`, { new_status: status }); showDetail.value = false; await load() }
onMounted(load)
</script>
