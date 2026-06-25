<template>
  <div class="topology-container">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <h3>网络拓扑</h3>
      <el-button size="small" @click="loadData">刷新</el-button>
    </div>
    <div ref="chartRef" style="width: 100%; height: 500px; background: var(--rs-bg-secondary); border-radius: 8px;"></div>
    <div v-if="!proxyChain.length && !hosts.length" style="text-align: center; padding: 40px; color: var(--rs-text-secondary);">
      暂无代理或已控主机数据。添加代理节点和已控主机后，拓扑图将自动生成。
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import api from '../stores/api'

const props = defineProps({ projectId: Number })
const chartRef = ref(null)
const proxyChain = ref([])
const hosts = ref([])
let chartInstance = null

const loadData = async () => {
  try {
    const [p, h] = await Promise.all([
      api.get(`/projects/${props.projectId}/ops/proxy`),
      api.get(`/projects/${props.projectId}/ops/hosts`),
    ])
    proxyChain.value = p.items || []
    hosts.value = h.items || []
    await nextTick()
    renderChart()
  } catch (e) { /* empty */ }
}

const renderChart = () => {
  if (!chartRef.value) return
  if (typeof echarts === 'undefined') {
    renderFallbackCanvas()
    return
  }

  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(chartRef.value, 'dark')

  const nodes = []
  const links = []

  nodes.push({ id: 'attacker', name: '攻击机', category: 0, symbolSize: 50, symbol: 'roundRect' })

  proxyChain.value.forEach((p, i) => {
    const nid = `proxy_${p.id || i}`
    nodes.push({
      id: nid, name: `${p.name}\n${p.host}:${p.port}`, category: 1,
      symbolSize: 40, symbol: 'diamond',
      itemStyle: { color: p.status === 'online' ? '#67c23a' : p.status === 'offline' ? '#f56c6c' : '#e6a23c' },
    })
    links.push({ source: i === 0 ? 'attacker' : `proxy_${proxyChain.value[i - 1].id || (i - 1)}`, target: nid, label: { show: true, formatter: p.tunnel_tool || p.proxy_type } })
  })

  hosts.value.forEach((h, i) => {
    const nid = `host_${h.id || i}`
    const color = h.access_level === 'domain_admin' ? '#e74c3c' : h.access_level === 'root' || h.access_level === 'system' ? '#e67e22' : '#3498db'
    nodes.push({
      id: nid, name: `${h.ip}\n${h.hostname || ''}\n[${h.access_level}]`, category: 2,
      symbolSize: 35, symbol: 'rect',
      itemStyle: { color, opacity: h.status === 'active' ? 1 : 0.4 },
    })
    const lastProxy = proxyChain.value.length > 0 ? `proxy_${proxyChain.value[proxyChain.value.length - 1].id || (proxyChain.value.length - 1)}` : 'attacker'
    links.push({ source: lastProxy, target: nid, lineStyle: { type: 'dashed' } })
  })

  chartInstance.setOption({
    tooltip: { trigger: 'item' },
    legend: { data: ['攻击机', '代理节点', '已控主机'], textStyle: { color: '#999' } },
    series: [{
      type: 'graph', layout: 'force', roam: true, draggable: true,
      categories: [{ name: '攻击机' }, { name: '代理节点' }, { name: '已控主机' }],
      data: nodes, links,
      label: { show: true, fontSize: 10, color: '#ccc' },
      lineStyle: { color: '#555', width: 2, curveness: 0.1 },
      force: { repulsion: 300, edgeLength: [100, 200], gravity: 0.1 },
    }],
  })
}

const renderFallbackCanvas = () => {
  if (!chartRef.value) return
  const el = chartRef.value
  el.innerHTML = ''
  el.style.display = 'flex'
  el.style.flexDirection = 'column'
  el.style.alignItems = 'center'
  el.style.justifyContent = 'center'
  el.style.gap = '8px'

  const esc = (s) => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')

  const addNode = (emoji, label, detail, color) => {
    const d = document.createElement('div')
    d.style.cssText = `background: var(--rs-bg-card); border: 2px solid ${color}; border-radius: 10px; padding: 10px 20px; text-align: center; min-width: 140px;`
    d.innerHTML = `<div style="font-size:22px;">${esc(emoji)}</div><div style="font-weight:bold;font-size:12px;">${esc(label)}</div>${detail ? `<div style="font-size:11px;color:#999;">${esc(detail)}</div>` : ''}`
    el.appendChild(d)
  }
  const addEdge = (label) => {
    const d = document.createElement('div')
    d.style.cssText = 'text-align:center;'
    d.innerHTML = `<div style="width:2px;height:20px;background:#555;margin:0 auto;"></div><div style="font-size:11px;color:#999;">${esc(label || '↓')}</div>`
    el.appendChild(d)
  }

  addNode('💻', '攻击机', '', 'var(--rs-accent)')
  proxyChain.value.forEach(p => {
    addEdge(p.tunnel_tool || p.proxy_type)
    addNode('🔗', p.name, `${p.host}:${p.port}`, p.status === 'online' ? '#67c23a' : '#f56c6c')
  })
  if (hosts.value.length) {
    addEdge('')
    const grid = document.createElement('div')
    grid.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;justify-content:center;'
    hosts.value.forEach(h => {
      const d = document.createElement('div')
      const color = h.access_level === 'domain_admin' ? '#e74c3c' : '#3498db'
      d.style.cssText = `background:var(--rs-bg-card);border:2px solid ${color};border-radius:8px;padding:8px 14px;text-align:center;`
      d.innerHTML = `<div style="font-size:18px;">🖥️</div><div style="font-weight:bold;font-size:11px;">${esc(h.ip)}</div><div style="font-size:10px;color:#999;">[${esc(h.access_level)}]</div>`
      grid.appendChild(d)
    })
    el.appendChild(grid)
  }
}

let resizeObs = null
onMounted(async () => {
  await loadData()
  resizeObs = new ResizeObserver(() => { if (chartInstance) chartInstance.resize() })
  if (chartRef.value) resizeObs.observe(chartRef.value)
})
onUnmounted(() => {
  if (chartInstance) chartInstance.dispose()
  if (resizeObs) resizeObs.disconnect()
})
</script>

<style scoped>
.topology-container { padding: 16px; }
</style>
