import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '总览' } },

  // 工作台
  { path: '/projects', name: 'Projects', component: () => import('../views/Projects.vue'), meta: { title: '项目管理' } },
  { path: '/projects/:id', name: 'ProjectDetail', component: () => import('../views/ProjectDetail.vue'), meta: { title: '项目详情' } },
  { path: '/projects/:id/assets', name: 'Assets', component: () => import('../views/Assets.vue'), meta: { title: '资产管理' } },
  { path: '/projects/:id/scanning', name: 'Scanning', component: () => import('../views/Scanning.vue'), meta: { title: '扫描任务' } },
  { path: '/projects/:id/findings', name: 'Findings', component: () => import('../views/Findings.vue'), meta: { title: '漏洞管理' } },
  { path: '/projects/:id/operations', name: 'Operations', component: () => import('../views/Operations.vue'), meta: { title: '作战管理' } },
  { path: '/projects/:id/testing', name: 'ManualTesting', component: () => import('../views/ManualTesting.vue'), meta: { title: '手工测试' } },
  { path: '/projects/:id/redblue', name: 'RedBlue', component: () => import('../views/RedBlue.vue'), meta: { title: '红蓝对抗' } },
  { path: '/projects/:id/llm-test', name: 'LLMTest', component: () => import('../views/LLMTest.vue'), meta: { title: 'LLM安全测试' } },

  // 全局视图
  { path: '/assets', name: 'AssetsGlobal', component: () => import('../views/AssetsGlobal.vue'), meta: { title: '资产管理' } },
  { path: '/scans', name: 'ScansGlobal', component: () => import('../views/ScansGlobal.vue'), meta: { title: '扫描任务' } },
  { path: '/vulns', name: 'VulnsGlobal', component: () => import('../views/VulnsGlobal.vue'), meta: { title: '漏洞管理' } },
  // 旧路由兼容
  { path: '/warroom', redirect: '/projects' },
  { path: '/redblue', redirect: '/projects' },
  { path: '/testing', redirect: '/projects' },

  // 智能
  { path: '/ai', name: 'AIAssistant', component: () => import('../views/AIAssistant.vue'), meta: { title: 'AI 助手' } },
  { path: '/knowledge', name: 'Knowledge', component: () => import('../views/Knowledge.vue'), meta: { title: '漏洞情报' } },

  // 系统
  { path: '/plugins', name: 'Plugins', component: () => import('../views/Plugins.vue'), meta: { title: '工具管理' } },
  { path: '/workflow', name: 'Workflow', component: () => import('../views/Workflow.vue'), meta: { title: '工单管理' } },
  { path: '/baseline', name: 'Baseline', component: () => import('../views/Baseline.vue'), meta: { title: '基线合规' } },
  { path: '/users', redirect: '/settings' },
  { path: '/tenants', redirect: '/settings' },
  { path: '/settings', name: 'Settings', component: () => import('../views/Settings.vue'), meta: { title: '系统管理' } },
  { path: '/profile', name: 'Profile', component: () => import('../views/Profile.vue'), meta: { title: '个人设置' } },
  { path: '/notifications', redirect: '/profile' },

  // 独立页面
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { title: '登录', noAuth: true, noLayout: true } },
  { path: '/portal', name: 'ClientPortal', component: () => import('../views/ClientPortal.vue'), meta: { title: '客户门户', noAuth: true, noLayout: true } },

  // ═══ V2 新版界面 ═══
  {
    path: '/v2',
    component: () => import('../layouts/LayoutV2.vue'),
    children: [
      { path: '', name: 'DashboardV2', component: () => import('../views/v2/DashboardV2.vue'), meta: { title: 'SITUATION OVERVIEW' } },
      { path: 'projects', name: 'ProjectsV2', component: () => import('../views/Projects.vue'), meta: { title: 'PROJECTS' } },
      { path: 'projects/:id', name: 'ProjectDetailV2', component: () => import('../views/ProjectDetail.vue'), meta: { title: 'PROJECT DETAIL' } },
      { path: 'projects/:id/assets', name: 'AssetsDetailV2', component: () => import('../views/Assets.vue'), meta: { title: 'ASSETS' } },
      { path: 'projects/:id/scanning', name: 'ScanningDetailV2', component: () => import('../views/Scanning.vue'), meta: { title: 'SCAN OPERATIONS' } },
      { path: 'projects/:id/findings', name: 'FindingsDetailV2', component: () => import('../views/Findings.vue'), meta: { title: 'VULNERABILITIES' } },
      { path: 'projects/:id/operations', name: 'OperationsDetailV2', component: () => import('../views/Operations.vue'), meta: { title: 'OPERATIONS' } },
      { path: 'projects/:id/testing', name: 'TestingDetailV2', component: () => import('../views/ManualTesting.vue'), meta: { title: 'MANUAL TESTING' } },
      { path: 'projects/:id/redblue', name: 'RedBlueDetailV2', component: () => import('../views/RedBlue.vue'), meta: { title: 'RED vs BLUE' } },
      { path: 'projects/:id/llm-test', name: 'LLMTestDetailV2', component: () => import('../views/LLMTest.vue'), meta: { title: 'LLM SECURITY' } },
      { path: 'scanning', name: 'ScanningV2', component: () => import('../views/ScansGlobal.vue'), meta: { title: 'SCAN OPERATIONS' } },
      { path: 'vulns', name: 'VulnsV2', component: () => import('../views/VulnsGlobal.vue'), meta: { title: 'VULNERABILITIES' } },
      { path: 'assets', name: 'AssetsV2', component: () => import('../views/AssetsGlobal.vue'), meta: { title: 'ASSETS' } },
      { path: 'ai', name: 'AIV2', component: () => import('../views/AIAssistant.vue'), meta: { title: 'AI ASSISTANT' } },
      { path: 'knowledge', name: 'KnowledgeV2', component: () => import('../views/Knowledge.vue'), meta: { title: 'INTEL' } },
      { path: 'plugins', name: 'PluginsV2', component: () => import('../views/Plugins.vue'), meta: { title: 'ENGINES' } },
      { path: 'settings', name: 'SettingsV2', component: () => import('../views/Settings.vue'), meta: { title: 'SETTINGS' } },
    ]
  },
  { path: '/v2/login', name: 'LoginV2', component: () => import('../views/v2/LoginV2.vue'), meta: { title: '登录', noAuth: true, noLayout: true } },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to, from, next) => {
  const uiVersion = localStorage.getItem('rs_ui_version')
  const isV2 = uiVersion === 'v2'

  if (to.meta.noAuth) {
    if (to.name === 'Login' && isV2) { next({ name: 'LoginV2', query: to.query }); return }
    if (to.name === 'LoginV2' && !isV2) { next({ name: 'Login', query: to.query }); return }
    next(); return
  }

  const token = localStorage.getItem('token')
  const loginTarget = isV2 ? 'LoginV2' : 'Login'

  if (!token) { next({ name: loginTarget, query: { redirect: to.fullPath } }); return }
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    if (payload.exp && payload.exp * 1000 < Date.now()) { localStorage.removeItem('token'); next({ name: loginTarget }); return }
  } catch { localStorage.removeItem('token'); next({ name: loginTarget }); return }

  if (to.path === '/' && isV2) { next('/v2'); return }

  next()
})

export default router
