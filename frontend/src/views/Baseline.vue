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
          <el-button size="small" type="primary" @click="openRunDialog(b.key, b.name)">执行检查</el-button>
        </div>
      </div>
    </div>

    <!-- Manual Check Results Submission -->
    <div v-if="manualChecks.length" class="card" style="padding: 16px; margin-bottom: 16px;">
      <h3 style="margin-bottom: 12px;">手动检查 — {{ lastRunName }} <el-tag size="small" type="warning">手动模式</el-tag></h3>
      <div style="font-size: 13px; color: var(--rs-text-secondary); margin-bottom: 12px;">请在目标主机上执行每项检查命令，将实际输出填入对应行，然后点击"提交评估"</div>
      <el-table :data="manualChecks" style="width: 100%;">
        <el-table-column prop="title" label="检查项" width="200" />
        <el-table-column prop="command" label="执行命令" min-width="300">
          <template #default="{ row }"><code style="font-size: 12px; color: var(--rs-accent);">{{ row.command }}</code></template>
        </el-table-column>
        <el-table-column prop="expected" label="期望" width="120" />
        <el-table-column label="实际输出" width="200">
          <template #default="{ row }"><el-input v-model="row.actual_output" size="small" placeholder="粘贴命令输出" /></template>
        </el-table-column>
      </el-table>
      <el-button type="primary" style="margin-top: 12px;" @click="submitEvaluation" :loading="evaluating">提交评估</el-button>
    </div>

    <!-- Results -->
    <div v-if="scanResults.length" class="card" style="padding: 16px; margin-bottom: 16px;">
      <h3 style="margin-bottom: 12px;">检查结果 — {{ lastRunName }}</h3>
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

    <!-- Run Dialog -->
    <el-dialog v-model="showRun" :title="`执行基线检查 — ${runName}`" width="480px">
      <el-form label-width="80px">
        <el-form-item label="目标主机">
          <el-input v-model="runTarget" placeholder="IP 地址 (如 192.168.1.100)" />
        </el-form-item>
        <el-form-item label="SSH 端口">
          <el-input-number v-model="runPort" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="认证方式">
          <el-radio-group v-model="runAuthType">
            <el-radio value="password">密码</el-radio>
            <el-radio value="key">密钥</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="用户名"><el-input v-model="runUser" placeholder="root" /></el-form-item>
        <el-form-item v-if="runAuthType === 'password'" label="密码"><el-input v-model="runPassword" type="password" show-password /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRun = false">取消</el-button>
        <el-button type="primary" @click="runBaseline" :loading="running">开始检查</el-button>
      </template>
    </el-dialog>

    <!-- Detail Dialog -->
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
const scanResults = ref([]); const lastRunName = ref('')
const showRun = ref(false); const running = ref(false)
const runKey = ref(''); const runName = ref('')
const runTarget = ref(''); const runPort = ref(22); const runAuthType = ref('password')
const runUser = ref('root'); const runPassword = ref('')
const manualChecks = ref([]); const evaluating = ref(false)

const load = async () => {
  try { const res = await api.get('/baseline/baselines'); baselines.value = res.items || [] }
  catch (e) { ElMessage.error('加载失败') }
}

const selectBaseline = async (key) => {
  const res = await api.get(`/baseline/baselines/${key}`)
  detailName.value = res.name; detailItems.value = res.items || []; showDetail.value = true
}

const openRunDialog = (key, name) => {
  runKey.value = key; runName.value = name; showRun.value = true
}

const runBaseline = async () => {
  if (!runTarget.value) { ElMessage.warning('请输入目标主机 IP'); return }
  running.value = true
  try {
    const res = await api.post(`/baseline/baselines/${runKey.value}/run`, {
      target: runTarget.value, port: runPort.value,
      auth_type: runAuthType.value, username: runUser.value,
      password: runPassword.value,
    })
    if (res.status === 'manual_mode') {
      manualChecks.value = (res.checks || []).map(c => ({ ...c, actual_output: '' }))
      lastRunName.value = runName.value
      showRun.value = false
      ElMessage.info('手动模式: 请逐项执行检查命令并填写结果')
    } else {
      scanResults.value = res.results || []
      lastRunName.value = runName.value
      showRun.value = false
    }
  } catch (e) { ElMessage.error('执行失败') }
  finally { running.value = false }
}

const submitEvaluation = async () => {
  const results = manualChecks.value.map(c => ({ item_id: c.id, actual_output: c.actual_output || '' }))
  evaluating.value = true
  try {
    const res = await api.post('/baseline/baselines/evaluate', { baseline_key: runKey.value, results })
    scanResults.value = (res.results || []).map(r => ({
      ...r, status: r.passed ? 'pass' : 'fail',
    }))
    lastRunName.value = `${runName.value} (合规率 ${res.compliance_rate}%)`
    manualChecks.value = []
    ElMessage.success(`评估完成: ${res.passed}/${res.total} 项合规`)
  } catch (e) { ElMessage.error('评估失败') }
  finally { evaluating.value = false }
}

onMounted(load)
</script>
