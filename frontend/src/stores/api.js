import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401) {
      const url = err.config?.url || ''
      if (!url.includes('/auth/login') && !url.includes('/portal/login')) {
        localStorage.removeItem('token')
        const isV2 = localStorage.getItem('rs_ui_version') === 'v2'
        window.location.href = isV2 ? '/v2/login' : '/login'
      }
    }
    return Promise.reject(err)
  }
)

export default api

export function logSessionActivity(projectId, action, detail = '') {
  const sessionId = sessionStorage.getItem(`rs_active_session_${projectId}`)
  if (!sessionId) return
  api.post(`/projects/${projectId}/sessions/${sessionId}/activity`, { action, detail }).catch(() => {})
}
