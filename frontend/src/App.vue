<template>
  <div v-if="$route.meta.noLayout"><router-view /></div>
  <div v-else class="layout">
    <aside class="sidebar">
      <div class="logo">⚡ RedScope</div>
      <nav class="nav-menu">
        <router-link to="/" class="nav-item" active-class="active" exact>
          <el-icon><DataBoard /></el-icon> 总览
        </router-link>
        <router-link to="/projects" class="nav-item" active-class="active">
          <el-icon><FolderOpened /></el-icon> 项目管理
        </router-link>
        <router-link to="/knowledge" class="nav-item" active-class="active">
          <el-icon><Document /></el-icon> 漏洞情报
        </router-link>
        <router-link to="/plugins" class="nav-item" active-class="active">
          <el-icon><SetUp /></el-icon> 工具管理
        </router-link>
        <router-link to="/baseline" class="nav-item" active-class="active">
          <el-icon><Checked /></el-icon> 基线合规
        </router-link>
        <router-link to="/workflow" class="nav-item" active-class="active">
          <el-icon><Tickets /></el-icon> 工单管理
        </router-link>
        <div style="padding: 8px 20px; font-size: 11px; color: var(--rs-text-secondary); margin-top: 8px;">管理</div>
        <router-link to="/users" class="nav-item" active-class="active">
          <el-icon><User /></el-icon> 用户管理
        </router-link>
        <router-link to="/notifications" class="nav-item" active-class="active">
          <el-icon><Bell /></el-icon> 通知设置
        </router-link>
        <router-link to="/tenants" class="nav-item" active-class="active">
          <el-icon><OfficeBuilding /></el-icon> 租户管理
        </router-link>
        <a href="/portal" class="nav-item" target="_blank" style="text-decoration: none;">
          <el-icon><Link /></el-icon> 客户门户
        </a>
      </nav>
      <div style="padding: 12px 20px; border-top: 1px solid var(--rs-border); font-size: 11px; color: var(--rs-text-secondary);">
        RedScope v1.0
      </div>
    </aside>
    <div class="main-content">
      <header class="topbar">
        <span style="color: var(--rs-text-secondary);">{{ $route.meta.title }}</span>
        <div style="display: flex; align-items: center; gap: 12px;">
          <div style="position: relative;">
            <el-input
              v-model="searchQuery"
              placeholder="搜索... (Ctrl+K)"
              size="small"
              style="width: 280px;"
              :prefix-icon="Search"
              @input="onSearch"
              @focus="showSearchResults = true"
              @blur="hideSearch"
            />
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
                <div class="search-section">漏洞情报</div>
                <div v-for="r in searchResults.knowledge" :key="'k'+r.id" class="search-item" @mousedown="goTo('/knowledge')">{{ r.cve_id }} {{ r.title }}</div>
              </div>
            </div>
          </div>
          <el-dropdown trigger="click">
            <el-avatar :size="28" style="cursor: pointer;">{{ userInitial }}</el-avatar>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="$router.push('/profile')">个人设置</el-dropdown-item>
                <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <main class="page-content">
        <!-- Onboarding guide for new users -->
        <div v-if="showOnboarding && $route.path === '/'" class="card" style="padding: 20px; margin-bottom: 16px; border-left: 4px solid var(--rs-accent);">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <h3 style="margin: 0;">欢迎使用 RedScope</h3>
            <el-button size="small" text @click="dismissOnboarding">✕</el-button>
          </div>
          <div style="margin-top: 12px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">
            <div class="card" style="padding: 12px; cursor: pointer; text-align: center;" @click="$router.push('/projects')">
              <div style="font-size: 24px; margin-bottom: 8px;">1</div>
              <div style="font-weight: bold;">创建项目</div>
              <div style="font-size: 12px; color: var(--rs-text-secondary); margin-top: 4px;">选择实战/靶场/研究模式</div>
            </div>
            <div class="card" style="padding: 12px; cursor: pointer; text-align: center;" @click="$router.push('/plugins')">
              <div style="font-size: 24px; margin-bottom: 8px;">2</div>
              <div style="font-weight: bold;">配置工具</div>
              <div style="font-size: 12px; color: var(--rs-text-secondary); margin-top: 4px;">加载 Nmap/Nuclei 等引擎</div>
            </div>
            <div class="card" style="padding: 12px; text-align: center;">
              <div style="font-size: 24px; margin-bottom: 8px;">3</div>
              <div style="font-weight: bold;">添加资产</div>
              <div style="font-size: 12px; color: var(--rs-text-secondary); margin-top: 4px;">手动或 CSV/Nessus 导入</div>
            </div>
            <div class="card" style="padding: 12px; text-align: center;">
              <div style="font-size: 24px; margin-bottom: 8px;">4</div>
              <div style="font-weight: bold;">开始扫描</div>
              <div style="font-size: 12px; color: var(--rs-text-secondary); margin-top: 4px;">选引擎、定策略、出报告</div>
            </div>
          </div>
        </div>
        <router-view />
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
import TerminalPanel from './components/TerminalPanel.vue'
import api from './stores/api'

const router = useRouter()
const showTerminal = ref(false)
const termSessions = ref(['main'])
const activeSession = ref('main')
let sessionCounter = 1

const addSession = () => {
  sessionCounter++
  const name = `shell-${sessionCounter}`
  termSessions.value.push(name)
  activeSession.value = name
}

const closeSession = (index) => {
  const removed = termSessions.value.splice(index, 1)
  if (activeSession.value === removed[0]) {
    activeSession.value = termSessions.value[Math.min(index, termSessions.value.length - 1)] || 'main'
  }
  if (termSessions.value.length === 0) {
    termSessions.value = ['main']
    activeSession.value = 'main'
  }
}

const searchQuery = ref('')
const showSearchResults = ref(false)
const searchResults = ref({ projects: [], assets: [], findings: [], knowledge: [] })
const showOnboarding = ref(!localStorage.getItem('rs_onboarding_dismissed'))

const userInitial = computed(() => {
  try {
    const token = localStorage.getItem('token')
    if (!token) return 'U'
    const payload = JSON.parse(atob(token.split('.')[1]))
    return (payload.username || 'U')[0].toUpperCase()
  } catch { return 'U' }
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
    try {
      searchResults.value = await api.get('/search', { params: { q: searchQuery.value } })
    } catch (e) { /* empty */ }
  }, 300)
}

const hideSearch = () => { setTimeout(() => { showSearchResults.value = false }, 200) }

const goTo = (path) => {
  showSearchResults.value = false
  searchQuery.value = ''
  router.push(path)
}

const logout = () => { localStorage.removeItem('token'); router.push('/login') }

const dismissOnboarding = () => {
  showOnboarding.value = false
  localStorage.setItem('rs_onboarding_dismissed', '1')
}

const handleKeydown = (e) => {
  if (e.ctrlKey && e.key === '`') { e.preventDefault(); showTerminal.value = !showTerminal.value }
  if (e.ctrlKey && e.key === 'k') { e.preventDefault(); document.querySelector('.topbar input')?.focus() }
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))
</script>

<style scoped>
.terminal-panel { height: 300px; border-top: 1px solid var(--rs-border); display: flex; flex-direction: column; flex-shrink: 0; }
.terminal-header { display: flex; justify-content: space-between; align-items: center; padding: 4px 12px; background: var(--rs-bg-secondary); border-bottom: 1px solid var(--rs-border); font-size: 12px; color: var(--rs-text-secondary); }
.terminal-toggle { text-align: center; padding: 4px; font-size: 12px; color: var(--rs-text-secondary); cursor: pointer; border-top: 1px solid var(--rs-border); background: var(--rs-bg-secondary); }
.terminal-toggle:hover { color: var(--rs-accent); }
.search-dropdown { position: absolute; top: 100%; left: 0; right: 0; background: var(--rs-bg-secondary); border: 1px solid var(--rs-border); border-radius: 6px; margin-top: 4px; max-height: 400px; overflow-y: auto; z-index: 999; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
.search-section { padding: 6px 12px; font-size: 11px; color: var(--rs-text-secondary); text-transform: uppercase; }
.search-item { padding: 8px 12px; cursor: pointer; font-size: 13px; }
.search-item:hover { background: var(--rs-bg-primary); }
</style>
