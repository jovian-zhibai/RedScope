<template>
  <div ref="termContainer" style="height: 100%; min-height: 300px; background: #0d1117; border-radius: 4px;"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

const props = defineProps({ sessionId: { type: String, default: 'default' } })
const termContainer = ref(null)
let terminal = null
let ws = null
let fitAddon = null

const sendResize = () => {
  if (!fitAddon || !ws || ws.readyState !== WebSocket.OPEN) return
  fitAddon.fit()
  const dims = fitAddon.proposeDimensions()
  if (dims) {
    ws.send(`\x1b[resize:${dims.cols}:${dims.rows}`)
  }
}

onMounted(() => {
  terminal = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, monospace",
    theme: {
      background: '#0d1117',
      foreground: '#e6edf3',
      cursor: '#58a6ff',
      selectionBackground: '#264f78',
      black: '#0d1117', red: '#f85149', green: '#3fb950', yellow: '#d29922',
      blue: '#58a6ff', magenta: '#bc8cff', cyan: '#39d353', white: '#e6edf3',
    },
  })

  fitAddon = new FitAddon()
  terminal.loadAddon(fitAddon)
  terminal.open(termContainer.value)
  fitAddon.fit()

  const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const token = localStorage.getItem('token')
  ws = new WebSocket(`${wsProtocol}//${location.host}/ws/terminal/${props.sessionId}?token=${token}`)

  ws.onopen = () => {
    terminal.write('\r\n\x1b[32m[RedScope Terminal]\x1b[0m 已连接到后端容器\r\n\x1b[33m提示: 如需连接宿主机，请使用 ssh user@host.docker.internal\x1b[0m\r\n\r\n')
    sendResize()
  }
  ws.onmessage = (e) => terminal.write(e.data)
  ws.onclose = (e) => {
    if (e.code === 4001) {
      terminal.write('\r\n\x1b[31m[认证失败] Token无效或已过期，请重新登录\x1b[0m\r\n')
    } else if (e.code === 4002) {
      terminal.write('\r\n\x1b[31m[连接被拒] 终端会话数已达上限\x1b[0m\r\n')
    } else {
      terminal.write('\r\n\x1b[31m[Connection Closed]\x1b[0m\r\n')
    }
  }
  ws.onerror = () => {
    terminal.write('\r\n\x1b[31m[连接失败] 无法连接到终端服务，请确认后端已启动\x1b[0m\r\n')
  }
  terminal.onData((data) => { if (ws.readyState === WebSocket.OPEN) ws.send(data) })

  window.addEventListener('resize', sendResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', sendResize)
  ws?.close()
  terminal?.dispose()
})
</script>
