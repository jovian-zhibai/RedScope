<template>
  <div v-if="$route.meta.noLayout"><router-view /></div>
  <div v-else class="layout">
    <aside class="sidebar">
      <div class="logo">⚡ RedScope</div>
      <nav class="nav-menu">
        <router-link to="/" class="nav-item" active-class="active" exact>
          <el-icon><DataBoard /></el-icon> 总览
        </router-link>

        <div class="nav-section">工作台</div>
        <router-link to="/projects" class="nav-item" active-class="active">
          <el-icon><FolderOpened /></el-icon> 项目管理
        </router-link>
        <router-link to="/assets" class="nav-item" active-class="active">
          <el-icon><Monitor /></el-icon> 资产管理
        </router-link>
        <router-link to="/scans" class="nav-item" active-class="active">
          <el-icon><VideoPlay /></el-icon> 扫描任务
        </router-link>
        <router-link to="/vulns" class="nav-item" active-class="active">
          <el-icon><Warning /></el-icon> 漏洞管理
        </router-link>

        <div class="nav-section">红队作战</div>
        <router-link to="/warroom" class="nav-item" active-class="active">
          <el-icon><Aim /></el-icon> 作战管理
        </router-link>
        <router-link to="/redblue" class="nav-item" active-class="active">
          <el-icon><TrophyBase /></el-icon> 红蓝对抗
        </router-link>
        <router-link to="/testing" class="nav-item" active-class="active">
          <el-icon><EditPen /></el-icon> 手工测试
        </router-link>

        <div class="nav-section">智能</div>
        <router-link to="/ai" class="nav-item" active-class="active">
          <el-icon><MagicStick /></el-icon> AI 助手
        </router-link>
        <router-link to="/knowledge" class="nav-item" active-class="active">
          <el-icon><Document /></el-icon> 漏洞情报
        </router-link>

        <div class="nav-section">系统</div>
        <router-link to="/plugins" class="nav-item" active-class="active">
          <el-icon><SetUp /></el-icon> 工具管理
        </router-link>
        <router-link to="/workflow" class="nav-item" active-class="active">
          <el-icon><Tickets /></el-icon> 工单管理
        </router-link>
        <router-link to="/users" class="nav-item" active-class="active">
          <el-icon><User /></el-icon> 用户管理
        </router-link>
        <router-link to="/settings" class="nav-item" active-class="active">
          <el-icon><Setting /></el-icon> 设置
        </router-link>
      </nav>
      <div style="padding: 12px 24px; border-top: 1px solid var(--rs-border); font-size: 11px; color: var(--rs-text-secondary);">
        RedScope v1.1
      </div>
    </aside>
    <div class="main-content">
      <header class="topbar">
        <span style="color: var(--rs-text-secondary); font-size: 13px;">{{ $route.meta.title }}</span>
        <div style="display: flex; align-items: center; gap: 12px;">
          <div style="position: relative;">
            <el-input v-model="searchQuery" placeholder="搜索项目/漏洞/资产... (Ctrl+K)" size="small" style="width: 300px;" :prefix-icon="Search" @input="onSearch" @focus="showSearchResults = true" @blur="hideSearch" />
            <div v-if="showSearchResults && hasResults" class="search-dropdown">
              <div v-if="searchResults.projects.length">
                <div class="search-section">项目</div>
                <div v-for="r in searchResults.projects" :key="'p'+r.id" class="search-item" @mousedown="goTo(`/projects/${r.id}`)">{{ r.name }}</div>
              </div>
              <div v-if="searchResults.findings.length">
                <div class="search-section">漏洞</div>
                <div v-for="r in searchResults.findings" :key="'f'+r.id" class="search-item" @mousedown="goTo(`/projects/${r.project_id}/findings`)">
                  <span class="severity-badge" :class="r.severity" style="margin-right: 6px;">{{ r.severity }}</span>{{ r.title }}
                </div>
              </div>
              <div v-if="searchResults.assets.length">
                <div class="search-section">资产</div>
                <div v-for="r in searchResults.assets" :key="'a'+r.id" class="search-item" @mousedown="goTo(`/projects/${r.project_id}/assets`)">{{ r.host }}</div>
              </div>
              <div v-if="searchResults.knowledge.length">
                <div class="search-section">情报</div>
                <div v-for="r in searchResults.knowledge" :key="'k'+r.id" class="search-item" @mousedown="goTo('/knowledge')">{{ r.cve_id }} {{ r.title }}</div>
              </div>
            </div>
          </div>
          <el-button size="small" circle @click="toggleTheme" :title="isDark ? '切换亮色' : '切换暗色'">
            {{ isDark ? '☀️' : '🌙' }}
          </el-button>
          <el-dropdown trigger="click">
            <el-avatar :size="30" style="cursor: pointer; background: var(--rs-accent);">{{ userInitial }}</el-avatar>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="$router.push('/settings')">系统设置</el-dropdown-item>
                <el-dropdown-item @click="$router.push('/settings?tab=profile')">个人信息</el-dropdown-item>
                <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <main class="page-content">
        <router-view />

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
      </main>
      <div v-if="showTerminal" class="terminal-panel">
        <div class="terminal-header">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span v-for="(s, i) in termSessions" :key="s"
              style="cursor: pointer; padding: 2px 8px; border-radius: 3px; font-size: 11px;"
              :style="{ background: activeSession === s ? 'var(--rs-accent)' : 'transparent', color: activeSession === s ? '#fff' : 'var(--rs-text-secondary)' }"
              @click="activeSession = s">
              {{ s }}
              <span v-if="termSessions.length > 1" style="margin-left: 4px; opacity: 0.6;" @click.stop="closeSession(i)">×</span>
            </span>
            <span style="cursor: pointer; font-size: 14px; color: var(--rs-text-secondary);" @click="addSession">+</span>
          </div>
          <el-button size="small" text @click="showTerminal = false">✕</el-button>
        </div>
        <TerminalPanel :key="activeSession" :session-id="activeSession" />
      </div>
      <div v-if="!showTerminal" class="terminal-toggle" @click="showTerminal = true">
        ▲ 终端 (Ctrl+`)
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import TerminalPanel from './components/TerminalPanel.vue'
import api from './stores/api'

const router = useRouter()
const showTerminal = ref(false)
const isDark = ref(localStorage.getItem('rs_theme') !== 'light')

const toggleTheme = () => {
  isDark.value = !isDark.value
  document.documentElement.className = isDark.value ? 'dark' : 'light'
  localStorage.setItem('rs_theme', isDark.value ? 'dark' : 'light')
}
const termSessions = ref(['main'])
const activeSession = ref('main')
let sessionCounter = 1

const addSession = () => { sessionCounter++; const name = `shell-${sessionCounter}`; termSessions.value.push(name); activeSession.value = name }
const closeSession = (index) => {
  const removed = termSessions.value.splice(index, 1)
  if (activeSession.value === removed[0]) activeSession.value = termSessions.value[Math.min(index, termSessions.value.length - 1)] || 'main'
  if (termSessions.value.length === 0) { termSessions.value = ['main']; activeSession.value = 'main' }
}

const showQuickCreate = ref(false)
const quickCreating = ref(false)
const quickForm = ref({ name: '', mode: 'combat', client_name: '' })

const searchQuery = ref('')
const showSearchResults = ref(false)
const searchResults = ref({ projects: [], assets: [], findings: [], knowledge: [] })

const userInitial = computed(() => {
  try { const token = localStorage.getItem('token'); if (!token) return 'U'; const payload = JSON.parse(atob(token.split('.')[1])); return (payload.username || 'U')[0].toUpperCase() }
  catch { return 'U' }
})

const hasResults = computed(() =>
  searchResults.value.projects.length || searchResults.value.assets.length ||
  searchResults.value.findings.length || searchResults.value.knowledge.length
)

let searchTimer = null
const onSearch = () => {
  clearTimeout(searchTimer)
  if (searchQuery.value.length < 2) { searchResults.value = { projects: [], assets: [], findings: [], knowledge: [] }; return }
  searchTimer = setTimeout(async () => {
    try { searchResults.value = await api.get('/search', { params: { q: searchQuery.value } }) } catch {}
  }, 300)
}

const hideSearch = () => { setTimeout(() => { showSearchResults.value = false }, 200) }
const goTo = (path) => { showSearchResults.value = false; searchQuery.value = ''; router.push(path) }
const logout = () => { localStorage.removeItem('token'); router.push('/login') }

const quickCreateProject = async () => {
  if (!quickForm.value.name) { ElMessage.warning('请输入项目名称'); return }
  quickCreating.value = true
  try {
    const res = await api.post('/projects', quickForm.value)
    showQuickCreate.value = false
    ElMessage.success('项目已创建')
    router.push(`/projects/${res.id}`)
  } catch (e) { ElMessage.error('创建失败') }
  finally { quickCreating.value = false }
}

const handleKeydown = (e) => {
  if (e.ctrlKey && e.key === '`') { e.preventDefault(); showTerminal.value = !showTerminal.value }
  if (e.ctrlKey && e.key === 'k') { e.preventDefault(); document.querySelector('.topbar input')?.focus() }
  if (e.ctrlKey && e.key === 'n') { e.preventDefault(); showQuickCreate.value = true }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  document.documentElement.className = isDark.value ? 'dark' : 'light'
})
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))
</script>
