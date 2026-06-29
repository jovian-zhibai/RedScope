<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>红蓝对抗</h2>
      <el-button type="primary" size="small" @click="showCreate = true"><el-icon><Plus /></el-icon> 新建演练</el-button>
    </div>

    <!-- Exercise List -->
    <div v-if="!currentExercise">
      <el-table :data="exercises" style="width: 100%;">
        <el-table-column prop="name" label="演练名称" min-width="200" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '进行中' : '已结束' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ row.created_at?.split('T')[0] }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="openScoreboard(row)">计分板</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!exercises.length" description="暂无演练，点击右上角创建" />
    </div>

    <!-- Scoreboard -->
    <div v-else>
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <el-button size="small" @click="currentExercise = null">← 返回列表</el-button>
        <div style="display: flex; gap: 8px;">
          <el-button size="small" type="primary" @click="showScore = true">提交得分</el-button>
          <el-button v-if="scoreboard?.exercise?.status === 'active'" size="small" type="danger" @click="endExercise">结束演练</el-button>
        </div>
      </div>

      <div v-if="scoreboard" style="text-align: center; margin-bottom: 24px;">
        <h3 style="color: var(--rs-text-primary);">{{ scoreboard.exercise.name }}</h3>
      </div>

      <!-- Score Summary -->
      <div v-if="scoreboard" style="display: grid; grid-template-columns: 1fr 80px 1fr; gap: 16px; margin-bottom: 24px;">
        <div class="card" style="padding: 20px; text-align: center; border-left: 4px solid var(--rs-danger);">
          <div style="font-size: 14px; color: var(--rs-danger); font-weight: bold;">{{ scoreboard.red_team.name }}</div>
          <div style="font-size: 48px; font-weight: bold; color: var(--rs-danger); margin: 8px 0;">{{ scoreboard.red_team.total_score }}</div>
          <div style="font-size: 12px; color: var(--rs-text-secondary);">{{ scoreboard.red_team.entries.length }} 条记录</div>
        </div>
        <div style="display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold; color: var(--rs-text-secondary);">VS</div>
        <div class="card" style="padding: 20px; text-align: center; border-left: 4px solid var(--rs-accent);">
          <div style="font-size: 14px; color: var(--rs-accent); font-weight: bold;">{{ scoreboard.blue_team.name }}</div>
          <div style="font-size: 48px; font-weight: bold; color: var(--rs-accent); margin: 8px 0;">{{ scoreboard.blue_team.total_score }}</div>
          <div style="font-size: 12px; color: var(--rs-text-secondary);">{{ scoreboard.blue_team.entries.length }} 条记录</div>
        </div>
      </div>

      <!-- Score Entries -->
      <div v-if="scoreboard" style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
        <div>
          <h4 style="color: var(--rs-danger); margin-bottom: 12px;">🔴 {{ scoreboard.red_team.name }} 得分明细</h4>
          <div v-for="e in scoreboard.red_team.entries" :key="e.id" class="card" style="padding: 10px; margin-bottom: 8px; border-left: 3px solid var(--rs-danger);">
            <div style="display: flex; justify-content: space-between;">
              <strong>{{ e.title }}</strong>
              <span style="color: var(--rs-danger); font-weight: bold;">+{{ e.points }}</span>
            </div>
            <div style="font-size: 12px; color: var(--rs-text-secondary); margin-top: 4px;">
              <el-tag size="small">{{ e.category }}</el-tag>
              <span v-if="e.description" style="margin-left: 8px;">{{ e.description }}</span>
            </div>
          </div>
          <el-empty v-if="!scoreboard.red_team.entries.length" description="暂无得分" :image-size="60" />
        </div>
        <div>
          <h4 style="color: var(--rs-accent); margin-bottom: 12px;">🔵 {{ scoreboard.blue_team.name }} 得分明细</h4>
          <div v-for="e in scoreboard.blue_team.entries" :key="e.id" class="card" style="padding: 10px; margin-bottom: 8px; border-left: 3px solid var(--rs-accent);">
            <div style="display: flex; justify-content: space-between;">
              <strong>{{ e.title }}</strong>
              <span style="color: var(--rs-accent); font-weight: bold;">+{{ e.points }}</span>
            </div>
            <div style="font-size: 12px; color: var(--rs-text-secondary); margin-top: 4px;">
              <el-tag size="small">{{ e.category }}</el-tag>
              <span v-if="e.description" style="margin-left: 8px;">{{ e.description }}</span>
            </div>
          </div>
          <el-empty v-if="!scoreboard.blue_team.entries.length" description="暂无得分" :image-size="60" />
        </div>
      </div>
    </div>

    <!-- Create Exercise Dialog -->
    <el-dialog v-model="showCreate" title="新建演练" width="420px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="演练名称"><el-input v-model="createForm.name" placeholder="如：2026年护网演练" /></el-form-item>
        <el-form-item label="红队名称"><el-input v-model="createForm.red_team_name" /></el-form-item>
        <el-form-item label="蓝队名称"><el-input v-model="createForm.blue_team_name" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createExercise">创建</el-button>
      </template>
    </el-dialog>

    <!-- Submit Score Dialog -->
    <el-dialog v-model="showScore" title="提交得分" width="480px">
      <el-form :model="scoreForm" label-width="80px">
        <el-form-item label="队伍">
          <el-radio-group v-model="scoreForm.team">
            <el-radio-button value="red">红队</el-radio-button>
            <el-radio-button value="blue">蓝队</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="scoreForm.category">
            <el-option value="getshell" label="GetShell" />
            <el-option value="vuln_critical" label="严重漏洞" />
            <el-option value="vuln_high" label="高危漏洞" />
            <el-option value="lateral_move" label="横向移动" />
            <el-option value="data_exfil" label="数据获取" />
            <el-option value="defense" label="防御成功" />
            <el-option value="detect" label="检测告警" />
            <el-option value="trace" label="溯源反制" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题"><el-input v-model="scoreForm.title" placeholder="得分事项" /></el-form-item>
        <el-form-item label="分数"><el-input-number v-model="scoreForm.points" :min="1" :max="1000" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="scoreForm.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showScore = false">取消</el-button>
        <el-button type="primary" @click="submitScore">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../stores/api'

const route = useRoute()
const pid = route.params.id
const exercises = ref([])
const currentExercise = ref(null)
const scoreboard = ref(null)

const showCreate = ref(false)
const createForm = ref({ name: '', red_team_name: '红队', blue_team_name: '蓝队' })

const showScore = ref(false)
const scoreForm = ref({ team: 'red', category: 'vuln_high', title: '', points: 100, description: '' })

const loadExercises = async () => {
  try {
    const res = await api.get(`/projects/${pid}/redblue`)
    exercises.value = res.items || []
  } catch (e) { ElMessage.error('加载演练列表失败') }
}

const createExercise = async () => {
  if (!createForm.value.name) { ElMessage.warning('请输入演练名称'); return }
  try {
    await api.post(`/projects/${pid}/redblue`, createForm.value)
    showCreate.value = false
    createForm.value = { name: '', red_team_name: '红队', blue_team_name: '蓝队' }
    await loadExercises()
    ElMessage.success('演练已创建')
  } catch (e) { ElMessage.error(e.response?.data?.detail || '创建失败') }
}

const openScoreboard = async (exercise) => {
  currentExercise.value = exercise
  scoreboard.value = await api.get(`/projects/${pid}/redblue/${exercise.id}/scoreboard`)
}

const submitScore = async () => {
  if (!scoreForm.value.title) { ElMessage.warning('请填写得分事项'); return }
  try {
    await api.post(`/projects/${pid}/redblue/${currentExercise.value.id}/score`, scoreForm.value)
    showScore.value = false
    scoreForm.value = { team: 'red', category: 'vuln_high', title: '', points: 100, description: '' }
    scoreboard.value = await api.get(`/projects/${pid}/redblue/${currentExercise.value.id}/scoreboard`)
    ElMessage.success('得分已提交')
  } catch (e) { ElMessage.error(e.response?.data?.detail || '提交失败') }
}

const endExercise = async () => {
  await ElMessageBox.confirm('确认结束演练？结束后无法再提交得分。', '结束演练', { type: 'warning' })
  await api.post(`/projects/${pid}/redblue/${currentExercise.value.id}/end`)
  scoreboard.value = await api.get(`/projects/${pid}/redblue/${currentExercise.value.id}/scoreboard`)
  ElMessage.success('演练已结束')
}

onMounted(loadExercises)
</script>
