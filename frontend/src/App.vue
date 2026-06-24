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
        <router-link to="/tenants" class="nav-item" active-class="active">
          <el-icon><OfficeBuilding /></el-icon> 租户管理
        </router-link>
      </nav>
      <div style="padding: 12px 20px; border-top: 1px solid var(--rs-border); font-size: 11px; color: var(--rs-text-secondary);">
        RedScope v1.0
      </div>
    </aside>
    <div class="main-content">
      <header class="topbar">
        <span style="color: var(--rs-text-secondary);">{{ $route.meta.title }}</span>
        <div style="display: flex; align-items: center; gap: 12px;">
          <el-input
            placeholder="搜索... (Ctrl+K)"
            size="small"
            style="width: 240px;"
            :prefix-icon="Search"
          />
          <el-avatar :size="28">A</el-avatar>
        </div>
      </header>
      <main class="page-content">
        <router-view />
      </main>
      <div v-if="showTerminal" class="terminal-panel">
        <div class="terminal-header">
          <span>终端</span>
          <el-button size="small" text @click="showTerminal = false">✕</el-button>
        </div>
        <TerminalPanel :session-id="'main'" />
      </div>
      <div v-if="!showTerminal" class="terminal-toggle" @click="showTerminal = true">
        ▲ 终端 (Ctrl+`)
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import TerminalPanel from './components/TerminalPanel.vue'

const showTerminal = ref(false)

const handleKeydown = (e) => {
  if (e.ctrlKey && e.key === '`') {
    e.preventDefault()
    showTerminal.value = !showTerminal.value
  }
  if (e.ctrlKey && e.key === 'k') {
    e.preventDefault()
    document.querySelector('.topbar input')?.focus()
  }
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))
</script>

<style scoped>
.terminal-panel {
  height: 300px;
  border-top: 1px solid var(--rs-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 12px;
  background: var(--rs-bg-secondary);
  border-bottom: 1px solid var(--rs-border);
  font-size: 12px;
  color: var(--rs-text-secondary);
}
.terminal-toggle {
  text-align: center;
  padding: 4px;
  font-size: 12px;
  color: var(--rs-text-secondary);
  cursor: pointer;
  border-top: 1px solid var(--rs-border);
  background: var(--rs-bg-secondary);
}
.terminal-toggle:hover {
  color: var(--rs-accent);
}
</style>
