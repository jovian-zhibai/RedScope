import { describe, it, expect } from 'vitest'
import router from '../../router/index.js'

describe('Router configuration', () => {
  const routeNames = router.getRoutes().map(r => r.name)
  const routePaths = router.getRoutes().map(r => r.path)

  it('has all core routes', () => {
    const required = ['Dashboard', 'Projects', 'ProjectDetail', 'Assets', 'Scanning',
      'Findings', 'Operations', 'ManualTesting', 'RedBlue', 'LLMTest',
      'Knowledge', 'Plugins', 'Workflow', 'Baseline', 'Users', 'Tenants',
      'Profile', 'Notifications', 'Login', 'ClientPortal']
    for (const name of required) {
      expect(routeNames).toContain(name)
    }
  })

  it('login and portal are noAuth', () => {
    const login = router.getRoutes().find(r => r.name === 'Login')
    const portal = router.getRoutes().find(r => r.name === 'ClientPortal')
    expect(login.meta.noAuth).toBe(true)
    expect(portal.meta.noAuth).toBe(true)
  })

  it('portal is noLayout', () => {
    const portal = router.getRoutes().find(r => r.name === 'ClientPortal')
    expect(portal.meta.noLayout).toBe(true)
  })

  it('project sub-routes use :id param', () => {
    const projectRoutes = routePaths.filter(p => p.startsWith('/projects/:id/'))
    expect(projectRoutes.length).toBeGreaterThanOrEqual(6)
  })

  it('has at least 19 routes', () => {
    expect(router.getRoutes().length).toBeGreaterThanOrEqual(19)
  })
})
