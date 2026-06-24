<template>
  <div class="topology-container">
    <h3 style="margin-bottom: 16px;">网络拓扑</h3>
    <div class="topo-graph">
      <!-- Attacker node -->
      <div class="topo-node attacker">
        <div class="node-icon">💻</div>
        <div class="node-label">你的机器</div>
      </div>

      <template v-for="(node, idx) in proxyChain" :key="node.id">
        <div class="topo-edge">
          <div class="edge-line"></div>
          <div class="edge-label">{{ node.tunnel_tool || node.proxy_type }}</div>
        </div>
        <div class="topo-node proxy" :class="node.status">
          <div class="node-icon">🔗</div>
          <div class="node-label">{{ node.name }}</div>
          <div class="node-detail">{{ node.host }}:{{ node.port }}</div>
          <div class="node-status">
            {{ {online:'🟢',offline:'🔴',unstable:'🟡',unknown:'⚪'}[node.status] }}
            {{ node.latency_ms ? node.latency_ms + 'ms' : '' }}
          </div>
          <div class="node-cidrs">
            <span v-for="cidr in node.reachable_cidrs" :key="cidr" class="cidr-tag">{{ cidr }}</span>
          </div>
        </div>
      </template>

      <!-- Compromised hosts grouped by proxy -->
      <div v-if="hosts.length" class="hosts-section">
        <div class="topo-edge"><div class="edge-line dashed"></div></div>
        <div class="hosts-grid">
          <div v-for="host in hosts" :key="host.id" class="topo-node host" :class="host.status">
            <div class="node-icon">🖥️</div>
            <div class="node-label">{{ host.ip }}</div>
            <div class="node-detail">{{ host.hostname }}</div>
            <div class="node-status">
              <span class="severity-badge" :class="host.access_level === 'domain_admin' ? 'critical' : host.access_level === 'root' ? 'high' : 'medium'">
                {{ host.access_level }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../stores/api'

const props = defineProps({ projectId: Number })
const proxyChain = ref([])
const hosts = ref([])

onMounted(async () => {
  try {
    const [p, h] = await Promise.all([
      api.get(`/projects/${props.projectId}/ops/proxy`),
      api.get(`/projects/${props.projectId}/ops/hosts`),
    ])
    proxyChain.value = p.items || []
    hosts.value = h.items || []
  } catch (e) { /* empty */ }
})
</script>

<style scoped>
.topology-container { padding: 16px; }

.topo-graph {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
}

.topo-node {
  background: var(--rs-bg-card);
  border: 2px solid var(--rs-border);
  border-radius: 12px;
  padding: 12px 20px;
  text-align: center;
  min-width: 160px;
}
.topo-node.attacker { border-color: var(--rs-accent); }
.topo-node.proxy.online { border-color: var(--rs-success); }
.topo-node.proxy.offline { border-color: var(--rs-danger); opacity: 0.6; }
.topo-node.proxy.unstable { border-color: var(--rs-warning); }
.topo-node.host.active { border-color: var(--rs-success); }
.topo-node.host.lost { border-color: var(--rs-danger); opacity: 0.6; }

.node-icon { font-size: 24px; margin-bottom: 4px; }
.node-label { font-weight: bold; font-size: 13px; }
.node-detail { font-size: 11px; color: var(--rs-text-secondary); }
.node-status { margin-top: 4px; font-size: 12px; }

.node-cidrs { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 4px; justify-content: center; }
.cidr-tag { background: var(--rs-bg-secondary); padding: 1px 6px; border-radius: 4px; font-size: 11px; color: var(--rs-text-secondary); }

.topo-edge { display: flex; flex-direction: column; align-items: center; height: 40px; }
.edge-line { width: 2px; height: 24px; background: var(--rs-border); }
.edge-line.dashed { border-left: 2px dashed var(--rs-border); width: 0; }
.edge-label { font-size: 11px; color: var(--rs-text-secondary); }

.hosts-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
  max-width: 600px;
}
.hosts-section { width: 100%; display: flex; flex-direction: column; align-items: center; }
</style>
