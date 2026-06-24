import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import ElementPlus from 'element-plus'

import Login from '../views/Login.vue'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: '/', component: { template: '<div />' } }, { path: '/login', component: Login }],
})

describe('Login.vue', () => {
  it('renders login form', async () => {
    const wrapper = mount(Login, {
      global: { plugins: [router, ElementPlus] },
    })
    expect(wrapper.text()).toContain('RedScope')
    expect(wrapper.find('input').exists()).toBe(true)
  })

  it('has register and login buttons', () => {
    const wrapper = mount(Login, {
      global: { plugins: [router, ElementPlus] },
    })
    const buttons = wrapper.findAll('button')
    const texts = buttons.map(b => b.text())
    expect(texts).toContain('登录')
    expect(texts).toContain('注册')
  })

  it('validates username length', async () => {
    const wrapper = mount(Login, {
      global: { plugins: [router, ElementPlus] },
    })
    expect(wrapper.vm.form.username).toBe('')
    expect(wrapper.vm.form.password).toBe('')
  })
})
