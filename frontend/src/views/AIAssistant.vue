<template>
  <div style="display: flex; height: calc(100vh - 120px); gap: 16px;">
    <!-- Chat Panel -->
    <div style="flex: 1; display: flex; flex-direction: column;" class="card">
      <div style="padding: 16px; border-bottom: 1px solid var(--rs-border); display: flex; justify-content: space-between; align-items: center;">
        <h3 style="margin: 0;">AI 安全助手</h3>
        <div style="display: flex; gap: 8px;">
          <el-select v-model="projectId" placeholder="关联项目(可选)" clearable size="small" style="width: 180px;">
            <el-option v-for="p in projects" :key="p.id" :value="p.id" :label="p.name" />
          </el-select>
          <el-button size="small" @click="clearChat">清空对话</el-button>
        </div>
      </div>

      <!-- Messages -->
      <div ref="messagesRef" style="flex: 1; overflow-y: auto; padding: 16px;">
        <div v-if="!messages.length" style="text-align: center; color: var(--rs-text-secondary); padding: 40px;">
          <div style="font-size: 48px; margin-bottom: 16px;">🤖</div>
          <div style="font-size: 16px; margin-bottom: 8px;">RedScope AI 安全助手</div>
          <div style="font-size: 13px;">支持漏洞分析、扫描策略推荐、攻击路径推导、自然语言查询</div>
          <div style="display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 20px;">
            <el-button v-for="q in quickQuestions" :key="q" size="small" @click="sendMessage(q)">{{ q }}</el-button>
          </div>
        </div>

        <div v-for="(msg, i) in messages" :key="i" style="margin-bottom: 16px;">
          <div :style="{ textAlign: msg.role === 'user' ? 'right' : 'left' }">
            <div style="display: inline-block; max-width: 80%; text-align: left; padding: 12px 16px; border-radius: 12px;"
              :style="{ background: msg.role === 'user' ? 'var(--rs-accent)' : 'var(--rs-bg-secondary)', color: msg.role === 'user' ? '#fff' : 'var(--rs-text-primary)' }">
              <div style="white-space: pre-wrap; font-size: 13px; line-height: 1.6;">{{ msg.content }}</div>
            </div>
            <div style="font-size: 11px; color: var(--rs-text-secondary); margin-top: 4px;">{{ msg.time }}</div>
          </div>
        </div>

        <div v-if="thinking" style="margin-bottom: 16px;">
          <div style="display: inline-block; padding: 12px 16px; border-radius: 12px; background: var(--rs-bg-secondary);">
            <span style="color: var(--rs-text-secondary);">思考中...</span>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div style="padding: 12px 16px; border-top: 1px solid var(--rs-border); display: flex; gap: 8px;">
        <el-input v-model="input" placeholder="输入问题... (支持自然语言查询，如「找出所有未修复的严重漏洞」)" @keyup.enter="sendMessage()" :disabled="thinking" />
        <el-button type="primary" @click="sendMessage()" :disabled="!input.trim() || thinking" :loading="thinking">发送</el-button>
      </div>
    </div>

    <!-- Tools Sidebar -->
    <div style="width: 320px; display: flex; flex-direction: column; gap: 12px;">
      <!-- Smart Scan -->
      <div class="card" style="padding: 16px;">
        <h4 style="margin: 0 0 12px;">智能扫描推荐</h4>
        <div style="font-size: 12px; color: var(--rs-text-secondary); margin-bottom: 8px;">
          根据资产指纹自动推荐扫描工具和模板
        </div>
        <el-select v-model="scanProjectId" placeholder="选择项目" size="small" style="width: 100%; margin-bottom: 8px;">
          <el-option v-for="p in projects" :key="p.id" :value="p.id" :label="p.name" />
        </el-select>
        <el-button type="primary" size="small" style="width: 100%;" @click="getRecommendation" :loading="recommending">
          获取推荐
        </el-button>
        <div v-if="recommendations.length" style="margin-top: 12px;">
          <div v-for="r in recommendations" :key="r.tool" style="padding: 8px; margin-bottom: 6px; background: var(--rs-bg-secondary); border-radius: 6px;">
            <div style="display: flex; justify-content: space-between;">
              <strong style="font-size: 13px;">{{ r.tool }}</strong>
              <el-tag size="small" type="warning">优先级 {{ r.priority }}</el-tag>
            </div>
            <div style="font-size: 12px; color: var(--rs-text-secondary); margin-top: 4px;">{{ r.reason }}</div>
            <div v-if="r.templates?.length" style="margin-top: 4px; display: flex; gap: 4px; flex-wrap: wrap;">
              <el-tag v-for="t in r.templates.slice(0, 3)" :key="t" size="small" type="info">{{ t }}</el-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- Attack Path -->
      <div class="card" style="padding: 16px;">
        <h4 style="margin: 0 0 12px;">攻击路径推导</h4>
        <div style="font-size: 12px; color: var(--rs-text-secondary); margin-bottom: 8px;">
          根据已有漏洞和控制点推导攻击路径
        </div>
        <el-select v-model="attackProjectId" placeholder="选择项目" size="small" style="width: 100%; margin-bottom: 8px;">
          <el-option v-for="p in projects" :key="p.id" :value="p.id" :label="p.name" />
        </el-select>
        <el-button type="danger" size="small" style="width: 100%;" @click="inferAttackPath" :loading="inferring">
          推导攻击路径
        </el-button>
        <div v-if="attackPath" style="margin-top: 12px; font-size: 12px; white-space: pre-wrap; max-height: 300px; overflow-y: auto; background: var(--rs-bg-secondary); padding: 12px; border-radius: 6px;">
          {{ attackPath }}
        </div>
      </div>

      <!-- NL Query -->
      <div class="card" style="padding: 16px;">
        <h4 style="margin: 0 0 12px;">自然语言查询</h4>
        <el-input v-model="nlQuery" placeholder="如：上周的严重漏洞" size="small" @keyup.enter="runNLQuery" />
        <el-button size="small" style="width: 100%; margin-top: 8px;" @click="runNLQuery" :loading="querying">
          查询
        </el-button>
        <div v-if="nlResults.length" style="margin-top: 8px;">
          <div style="font-size: 12px; color: var(--rs-text-secondary); margin-bottom: 4px;">{{ nlDescription }} ({{ nlResults.length }} 条)</div>
          <div v-for="r in nlResults.slice(0, 10)" :key="r.id" style="padding: 6px; border-bottom: 1px solid var(--rs-border); font-size: 12px;">
            <span v-if="r.severity" class="severity-badge" :class="r.severity" style="margin-right: 4px;">{{ r.severity }}</span>
            {{ r.title || r.host }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const messages = ref([])
const input = ref('')
const thinking = ref(false)
const messagesRef = ref(null)
const projects = ref([])
const projectId = ref(null)

const scanProjectId = ref(null)
const recommendations = ref([])
const recommending = ref(false)

const attackProjectId = ref(null)
const attackPath = ref('')
const inferring = ref(false)

const nlQuery = ref('')
const nlResults = ref([])
const nlDescription = ref('')
const querying = ref(false)

const quickQuestions = [
  '帮我检查配置',
  '如何检测 SQL 注入？',
  '发现 Tomcat 8.5，推荐哪些 PoC？',
  'Spring Boot Actuator 暴露怎么利用？',
  'NTLM Relay 攻击步骤？',
  'CTF: 帮我分析这道 Web 题',
]

onMounted(async () => {
  try { const res = await api.get('/projects'); projects.value = res.items || [] } catch {}
})

const sendMessage = async (text) => {
  const msg = text || input.value.trim()
  if (!msg) return
  input.value = ''

  const now = new Date().toLocaleTimeString()
  messages.value.push({ role: 'user', content: msg, time: now })
  await scrollToBottom()

  thinking.value = true
  try {
    const history = messages.value.slice(-10).map(m => ({ role: m.role, content: m.content }))
    const res = await api.post('/ai/chat', { message: msg, project_id: projectId.value, history })
    messages.value.push({ role: 'assistant', content: res.reply, time: new Date().toLocaleTimeString() })
  } catch (e) {
    messages.value.push({ role: 'assistant', content: 'AI 请求失败，请检查 LLM API 配置。', time: new Date().toLocaleTimeString() })
  }
  thinking.value = false
  await scrollToBottom()
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
}

const clearChat = () => { messages.value = [] }

const getRecommendation = async () => {
  if (!scanProjectId.value) { ElMessage.warning('请选择项目'); return }
  recommending.value = true
  try {
    const res = await api.post(`/projects/${scanProjectId.value}/ai/recommend-scan`)
    recommendations.value = res.recommendations || []
    if (!recommendations.value.length) ElMessage.info('暂无推荐，请先添加资产')
  } catch (e) { ElMessage.error('推荐失败') }
  finally { recommending.value = false }
}

const inferAttackPath = async () => {
  if (!attackProjectId.value) { ElMessage.warning('请选择项目'); return }
  inferring.value = true
  try {
    const res = await api.post(`/projects/${attackProjectId.value}/ai/attack-path`)
    attackPath.value = res.attack_path || '暂无可推导的攻击路径'
  } catch (e) { ElMessage.error('推导失败') }
  finally { inferring.value = false }
}

const runNLQuery = async () => {
  if (!nlQuery.value.trim()) return
  querying.value = true
  try {
    const res = await api.post('/ai/query', { message: nlQuery.value, project_id: projectId.value })
    nlResults.value = res.results || []
    nlDescription.value = res.description || ''
  } catch (e) { ElMessage.error('查询失败') }
  finally { querying.value = false }
}
</script>
