import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '总览' } },
  { path: '/projects', name: 'Projects', component: () => import('../views/Projects.vue'), meta: { title: '项目管理' } },
  { path: '/projects/:id', name: 'ProjectDetail', component: () => import('../views/ProjectDetail.vue'), meta: { title: '项目详情' } },
  { path: '/projects/:id/assets', name: 'Assets', component: () => import('../views/Assets.vue'), meta: { title: '资产管理' } },
  { path: '/projects/:id/scanning', name: 'Scanning', component: () => import('../views/Scanning.vue'), meta: { title: '扫描任务' } },
  { path: '/projects/:id/findings', name: 'Findings', component: () => import('../views/Findings.vue'), meta: { title: '漏洞管理' } },
  { path: '/projects/:id/operations', name: 'Operations', component: () => import('../views/Operations.vue'), meta: { title: '作战管理' } },
  { path: '/knowledge', name: 'Knowledge', component: () => import('../views/Knowledge.vue'), meta: { title: '漏洞情报' } },
  { path: '/plugins', name: 'Plugins', component: () => import('../views/Plugins.vue'), meta: { title: '工具管理' } },
  { path: '/workflow', name: 'Workflow', component: () => import('../views/Workflow.vue'), meta: { title: '工单管理' } },
  { path: '/baseline', name: 'Baseline', component: () => import('../views/Baseline.vue'), meta: { title: '基线合规' } },
  { path: '/tenants', name: 'Tenants', component: () => import('../views/Tenants.vue'), meta: { title: '租户管理' } },
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { title: '登录', noAuth: true, noLayout: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  if (to.meta.noAuth) {
    next()
    return
  }
  const token = localStorage.getItem('token')
  if (!token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }
  // Check token expiry (JWT payload is base64)
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      localStorage.removeItem('token')
      next({ name: 'Login' })
      return
    }
  } catch (e) {
    localStorage.removeItem('token')
    next({ name: 'Login' })
    return
  }
  next()
})

export default router
