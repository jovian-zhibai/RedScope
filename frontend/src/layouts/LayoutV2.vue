<template>
  <div class="v2-layout">
    <div class="v2-threat-bar"></div>

    <aside class="v2-sidebar">
      <div class="v2-sidebar-logo">
        <div class="v2-logo-icon">R</div>
        <div class="v2-logo-text"><span style="color: var(--rs2-danger);">RED</span><span style="color: var(--rs2-text-secondary);">SCOPE</span></div>
      </div>
      <nav style="padding: 8px 0; flex: 1; overflow-y: auto;">
        <div class="v2-nav-label">作战</div>
        <router-link to="/v2" class="v2-nav-item" exact>
          <el-icon><DataBoard /></el-icon>
          <span class="v2-nav-text">态势总览</span>
        </router-link>
        <router-link to="/v2/scanning" class="v2-nav-item">
          <el-icon><VideoPlay /></el-icon>
          <span class="v2-nav-text">扫描任务</span>
        </router-link>
        <router-link to="/v2/vulns" class="v2-nav-item">
          <el-icon><Warning /></el-icon>
          <span class="v2-nav-text">漏洞管理</span>
        </router-link>
        <router-link to="/v2/assets" class="v2-nav-item">
          <el-icon><Monitor /></el-icon>
          <span class="v2-nav-text">资产管理</span>
        </router-link>

        <div class="v2-nav-label">管理</div>
        <router-link to="/v2/projects" class="v2-nav-item" active-class="active">
          <el-icon><FolderOpened /></el-icon>
          <span class="v2-nav-text">项目管理</span>
        </router-link>
        <router-link to="/v2/ai" class="v2-nav-item">
          <el-icon><MagicStick /></el-icon>
          <span class="v2-nav-text">AI 助手</span>
        </router-link>
        <router-link to="/v2/knowledge" class="v2-nav-item">
          <el-icon><Document /></el-icon>
          <span class="v2-nav-text">漏洞情报</span>
        </router-link>
        <router-link to="/v2/plugins" class="v2-nav-item">
          <el-icon><SetUp /></el-icon>
          <span class="v2-nav-text">工具引擎</span>
        </router-link>

        <div class="v2-nav-label">系统</div>
        <router-link to="/v2/settings" class="v2-nav-item">
          <el-icon><Setting /></el-icon>
          <span class="v2-nav-text">系统设置</span>
        </router-link>
      </nav>
      <div class="v2-sidebar-footer" style="cursor: pointer;" @click="switchToV1">
        <span style="opacity: 0.6;">←</span>
        <span class="v2-nav-text" style="margin-left: 8px;">返回旧版</span>
      </div>
    </aside>

    <header class="v2-topbar">
      <div class="v2-topbar-left">
        <template v-for="(crumb, i) in breadcrumbs" :key="i">
          <span v-if="i > 0" style="color: var(--rs2-text-muted); margin: 0 2px;">/</span>
          <span v-if="crumb.path && i < breadcrumbs.length - 1" style="cursor: pointer; transition: color 0.12s;" :style="{ color: 'var(--rs2-text-secondary)' }" @click="$router.push(crumb.path)" @mouseenter="$event.target.style.color='var(--rs2-accent)'" @mouseleave="$event.target.style.color='var(--rs2-text-secondary)'">{{ crumb.label }}</span>
          <span v-else style="color: var(--rs2-accent); font-weight: 600;">{{ crumb.label }}</span>
        </template>
      </div>
      <div class="v2-topbar-right">
        <div class="v2-search-bar" style="position: relative;">
          <el-input v-model="searchQuery" placeholder="搜索项目/漏洞/资产... (Ctrl+K)" size="small" style="width: 260px;" @input="onSearch" @focus="showSearchResults = true" @blur="hideSearch" />
          <div v-if="showSearchResults && hasResults" class="v2-search-dropdown">
            <div v-if="searchResults.projects.length">
              <div class="v2-search-section">PROJECTS</div>
              <div v-for="r in searchResults.projects" :key="'p'+r.id" class="v2-search-item" @mousedown="goTo(`/v2/projects/${r.id}`)">{{ r.name }}</div>
            </div>
            <div v-if="searchResults.findings.length">
              <div class="v2-search-section">VULNS</div>
              <div v-for="r in searchResults.findings" :key="'f'+r.id" class="v2-search-item" @mousedown="goTo(`/v2/projects/${r.project_id}/findings`)">
                <span class="v2-sev" :class="r.severity" style="margin-right: 6px;">{{ r.severity }}</span>{{ r.title }}
              </div>
            </div>
            <div v-if="searchResults.assets.length">
              <div class="v2-search-section">ASSETS</div>
              <div v-for="r in searchResults.assets" :key="'a'+r.id" class="v2-search-item" @mousedown="goTo(`/v2/projects/${r.project_id}/assets`)">{{ r.host }}</div>
            </div>
            <div v-if="searchResults.knowledge.length">
              <div class="v2-search-section">INTEL</div>
              <div v-for="r in searchResults.knowledge" :key="'k'+r.id" class="v2-search-item" @mousedown="goTo('/v2/knowledge')">{{ r.cve_id }} {{ r.title }}</div>
            </div>
          </div>
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
          <span style="display:flex;align-items:center;gap:4px;font-family:var(--rs2-mono);font-size:9px;color:var(--rs2-text-muted);"><span class="v2-status-dot green"></span>DB</span>
          <span style="display:flex;align-items:center;gap:4px;font-family:var(--rs2-mono);font-size:9px;color:var(--rs2-text-muted);"><span class="v2-status-dot green"></span>REDIS</span>
          <span style="display:flex;align-items:center;gap:4px;font-family:var(--rs2-mono);font-size:9px;color:var(--rs2-text-muted);"><span class="v2-status-dot amber"></span>SCAN</span>
        </div>
        <el-button size="small" circle @click="toggleTheme" style="background:var(--rs2-bg-card);border-color:var(--rs2-border);color:var(--rs2-text-secondary);width:26px;height:26px;font-size:13px;">
          {{ isDark ? '☀' : '☽' }}
        </el-button>
        <el-dropdown trigger="click">
          <div style="width:26px;height:26px;border-radius:2px;background:var(--rs2-accent);display:flex;align-items:center;justify-content:center;font-family:var(--rs2-mono);font-weight:700;font-size:11px;color:#fff;cursor:pointer;">
            {{ userInitial }}
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="$router.push('/v2/settings')">个人设置</el-dropdown-item>
              <el-dropdown-item divided @click="switchToV1">返回旧版</el-dropdown-item>
              <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <div class="v2-main">
      <router-view @quick-create="showQuickCreate = true" />
    </div>

    <el-dialog v-model="showQuickCreate" title="新建项目" width="520px">
      <el-form :model="quickForm" label-width="100px">
        <el-form-item label="项目名称" required><el-input v-model="quickForm.name" placeholder="如：XX公司渗透测试" /></el-form-item>
        <el-form-item label="项目模式">
          <el-radio-group v-model="quickForm.mode">
            <el-radio-button value="combat">实战</el-radio-button>
            <el-radio-button value="range">靶场</el-radio-button>
            <el-radio-button value="research">研究</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="quickForm.mode === 'combat'" label="客户名称"><el-input v-model="quickForm.client_name" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showQuickCreate = false">取消</el-button>
        <el-button type="primary" @click="quickCreateProject" :loading="quickCreating">创建并进入</el-button>
      </template>
    </el-dialog>

    <div v-if="showTerminal" class="v2-terminal-panel">
      <div class="v2-terminal-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span v-for="(s, i) in termSessions" :key="s"
            style="cursor: pointer; padding: 2px 8px; border-radius: 2px; font-size: 10px; font-family: var(--rs2-mono);"
            :style="{ background: activeSession === s ? 'var(--rs2-accent)' : 'transparent', color: activeSession === s ? '#fff' : 'var(--rs2-text-muted)' }"
            @click="activeSession = s">
            {{ s }}
            <span v-if="termSessions.length > 1" style="margin-left: 4px; opacity: 0.6;" @click.stop="closeSession(i)">×</span>
          </span>
          <span style="cursor: pointer; font-size: 13px; color: var(--rs2-text-muted);" @click="addSession">+</span>
        </div>
        <el-button size="small" text @click="showTerminal = false" style="color: var(--rs2-text-muted);">✕</el-button>
      </div>
      <TerminalPanel :key="activeSession" :session-id="activeSession" />
    </div>

    <div class="v2-terminal-bar" @click="showTerminal = !showTerminal">
      {{ showTerminal ? '▼ 收起终端' : '▲ 终端 (Ctrl+`)' }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../stores/api'
import TerminalPanel from '../components/TerminalPanel.vue'

const router = useRouter()
const route = useRoute()
const isDark = ref(localStorage.getItem('rs_theme') !== 'light')
const showTerminal = ref(false)
const searchQuery = ref('')
const showSearchResults = ref(false)
const searchResults = ref({ projects: [], assets: [], findings: [], knowledge: [] })

const showQuickCreate = ref(false)
const quickCreating = ref(false)
const quickForm = ref({ name: '', mode: 'combat', client_name: '' })

const termSessions = ref(['main'])
const activeSession = ref('main')
let sessionCounter = 1

const addSession = () => { sessionCounter++; const name = `shell-${sessionCounter}`; termSessions.value.push(name); activeSession.value = name }
const closeSession = (index) => {
  const removed = termSessions.value.splice(index, 1)
  if (activeSession.value === removed[0]) activeSession.value = termSessions.value[Math.min(index, termSessions.value.length - 1)] || 'main'
  if (termSessions.value.length === 0) { termSessions.value = ['main']; activeSession.value = 'main' }
}

const toggleTheme = () => {
  isDark.value = !isDark.value
  document.documentElement.className = isDark.value ? 'dark' : 'light'
  localStorage.setItem('rs_theme', isDark.value ? 'dark' : 'light')
}

const userInitial = computed(() => {
  try { const token = localStorage.getItem('token'); if (!token) return 'U'; const payload = JSON.parse(atob(token.split('.')[1])); return (payload.username || 'U')[0].toUpperCase() } catch { return 'U' }
})

const hasResults = computed(() =>
  searchResults.value.projects.length || searchResults.value.assets.length ||
  searchResults.value.findings.length || searchResults.value.knowledge.length
)

const switchToV1 = () => {
  localStorage.setItem('rs_ui_version', 'v1')
  router.push('/')
}

const logout = () => { localStorage.removeItem('token'); router.push('/login') }

const projectNameCache = ref({})
const breadcrumbs = computed(() => {
  const crumbs = [{ label: 'REDSCOPE', path: '/v2' }]
  const path = route.path
  const projectId = route.params.id

  if (path.startsWith('/v2/projects') && projectId) {
    crumbs.push({ label: 'PROJECTS', path: '/v2/projects' })
    crumbs.push({ label: projectNameCache.value[projectId] || `#${projectId}`, path: `/v2/projects/${projectId}` })
    const sub = path.split('/').slice(4)[0]
    if (sub) {
      const subLabels = { assets: 'ASSETS', scanning: 'SCAN OPS', findings: 'VULNS', operations: 'OPS', testing: 'TESTING', redblue: 'RED vs BLUE', 'llm-test': 'LLM SEC' }
      crumbs.push({ label: subLabels[sub] || sub.toUpperCase() })
    }
  } else if (route.meta.title) {
    crumbs.push({ label: route.meta.title })
  }
  return crumbs
})

watch(() => route.params.id, async (id) => {
  if (id && !projectNameCache.value[id]) {
    try {
      const res = await api.get(`/projects/${id}`)
      projectNameCache.value[id] = res.name
    } catch {}
  }
}, { immediate: true })

const goTo = (path) => { showSearchResults.value = false; searchQuery.value = ''; router.push(path) }
const hideSearch = () => { setTimeout(() => { showSearchResults.value = false }, 200) }

let searchTimer = null
const onSearch = () => {
  clearTimeout(searchTimer)
  if (searchQuery.value.length < 2) { searchResults.value = { projects: [], assets: [], findings: [], knowledge: [] }; return }
  searchTimer = setTimeout(async () => {
    try { searchResults.value = await api.get('/search', { params: { q: searchQuery.value } }) } catch {}
  }, 300)
}

const quickCreateProject = async () => {
  if (!quickForm.value.name) { ElMessage.warning('请输入项目名称'); return }
  quickCreating.value = true
  try {
    const res = await api.post('/projects', quickForm.value)
    showQuickCreate.value = false
    ElMessage.success('项目已创建')
    router.push(`/v2/projects/${res.id}`)
  } catch (e) { ElMessage.error('创建失败') }
  finally { quickCreating.value = false }
}

const handleKeydown = (e) => {
  if (e.ctrlKey && e.key === '`') { e.preventDefault(); showTerminal.value = !showTerminal.value }
  if (e.ctrlKey && e.key === 'k') { e.preventDefault(); document.querySelector('.v2-search-bar input')?.focus() }
  if (e.ctrlKey && e.key === 'n') { e.preventDefault(); showQuickCreate.value = true }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  document.documentElement.className = isDark.value ? 'dark' : 'light'
})
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))
</script>
