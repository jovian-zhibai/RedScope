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
      localStorage.removeItem('token')
      window.location.href = '/login'
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
