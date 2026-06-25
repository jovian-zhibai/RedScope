<template>
  <div>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="代理隧道" name="proxy">
        <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
          <h3>代理节点</h3>
          <el-button size="small" type="primary" @click="showAddProxy = true"><el-icon><Plus /></el-icon> 添加节点</el-button>
        </div>
        <el-table :data="proxies">
          <el-table-column prop="name" label="名称" width="120" />
          <el-table-column prop="proxy_type" label="类型" width="80" />
          <el-table-column label="地址" width="200"><template #default="{ row }">{{ row.host }}:{{ row.port }}</template></el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <span>{{ {online:'🟢',offline:'🔴',unstable:'🟡',unknown:'⚪'}[row.status] }} {{ row.status }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="latency_ms" label="延迟" width="80"><template #default="{ row }">{{ row.latency_ms ? row.latency_ms + 'ms' : '-' }}</template></el-table-column>
          <el-table-column prop="reachable_cidrs" label="可达网段" min-width="200"><template #default="{ row }">{{ (row.reachable_cidrs || []).join(', ') }}</template></el-table-column>
          <el-table-column prop="tunnel_tool" label="隧道工具" width="100" />
        </el-table>

        <!-- Tunnel Helper -->
        <div style="margin-top: 16px;">
          <h4 style="margin-bottom: 8px;">隧道搭建命令生成</h4>
          <div style="display: flex; gap: 8px; margin-bottom: 8px;">
            <el-select v-model="tunnelTool" size="small" style="width: 120px;">
              <el-option value="frp" /><el-option value="chisel" /><el-option value="ssh" /><el-option value="suo5" />
            </el-select>
            <el-input v-model="tunnelVps" size="small" placeholder="VPS IP" style="width: 140px;" />
            <el-input-number v-model="tunnelVpsPort" size="small" :min="1" :max="65535" style="width: 120px;" />
            <el-button size="small" type="primary" @click="getTunnelHelper">生成命令</el-button>
          </div>
          <div v-if="tunnelCommands" style="background: var(--rs-bg-secondary); padding: 12px; border-radius: 6px;">
            <div v-if="tunnelCommands.server"><strong style="font-size: 12px;">服务端:</strong><pre style="font-size: 12px; margin: 4px 0 8px; white-space: pre-wrap;">{{ tunnelCommands.server }}</pre></div>
            <div v-if="tunnelCommands.client"><strong style="font-size: 12px;">客户端:</strong><pre style="font-size: 12px; margin: 4px 0; white-space: pre-wrap;">{{ tunnelCommands.client }}</pre></div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="凭据管理" name="credentials">
        <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
          <h3>凭据列表</h3>
          <el-button size="small" type="primary" @click="showAddCred = true"><el-icon><Plus /></el-icon> 添加凭据</el-button>
        </div>
        <el-table :data="credentials">
          <el-table-column prop="cred_type" label="类型" width="120" />
          <el-table-column prop="username" label="用户名" width="150" />
          <el-table-column prop="secret_masked" label="密码/Hash" width="200" />
          <el-table-column prop="domain" label="域" width="120" />
          <el-table-column prop="source" label="来源" width="150" />
          <el-table-column prop="source_host" label="来源主机" width="150" />
          <el-table-column prop="reuse_count" label="复用" width="60" />
          <el-table-column prop="is_cracked" label="已破解" width="70"><template #default="{ row }">{{ row.is_cracked ? '✅' : '❌' }}</template></el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="已控主机" name="hosts">
        <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
          <h3>已控主机</h3>
          <el-button size="small" type="primary" @click="showAddHost = true"><el-icon><Plus /></el-icon> 添加主机</el-button>
        </div>
        <el-table :data="hosts">
          <el-table-column prop="ip" label="IP" width="150" />
          <el-table-column prop="hostname" label="主机名" width="150" />
          <el-table-column prop="access_level" label="权限" width="120">
            <template #default="{ row }">
              <span class="severity-badge" :class="row.access_level === 'domain_admin' ? 'critical' : row.access_level === 'root' || row.access_level === 'system' ? 'high' : 'medium'">
                {{ row.access_level }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="shell_type" label="Shell类型" width="120" />
          <el-table-column prop="persistence" label="维持方式" width="150" />
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">{{ {active:'🟢',lost:'🔴',cleaned:'⚪'}[row.status] }}</template>
          </el-table-column>
          <el-table-column prop="entry_method" label="入侵方式" min-width="200" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" @click="openUploadFile(row)">记录文件</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- Upload File Record Dialog -->
        <el-dialog v-model="showUploadFile" title="记录上传文件" width="420px">
          <el-form :model="uploadFileForm" label-width="80px">
            <el-form-item label="文件路径"><el-input v-model="uploadFileForm.path" placeholder="/tmp/frpc" /></el-form-item>
            <el-form-item label="描述"><el-input v-model="uploadFileForm.description" placeholder="frp客户端,用于建立隧道" /></el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showUploadFile = false">取消</el-button>
            <el-button type="primary" @click="recordUploadFile">记录</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <el-tab-pane label="攻击时间线" name="timeline">
        <h3 style="margin-bottom: 12px;">攻击时间线</h3>
        <el-timeline>
          <el-timeline-item v-for="t in timeline" :key="t.id" :timestamp="t.timestamp" placement="top"
            :type="t.result === 'success' ? 'success' : 'danger'">
            <div class="card" style="padding: 12px;">
              <div style="display: flex; justify-content: space-between;">
                <div><strong>{{ t.action }}</strong></div>
                <el-tag size="small" v-if="t.attck_id">{{ t.attck_id }}</el-tag>
              </div>
              <div style="font-size: 12px; color: var(--rs-text-secondary); margin-top: 4px;">
                {{ t.phase }} · {{ t.target_host || '' }} · {{ t.auto_generated ? '自动记录' : '手动记录' }}
              </div>
            </div>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-if="!timeline.length" description="暂无时间线记录" />
      </el-tab-pane>

      <el-tab-pane label="战后清理" name="cleanup">
        <h3 style="margin-bottom: 12px;">清理检查清单 ({{ cleanupStats.cleaned }}/{{ cleanupStats.total }})</h3>
        <el-progress :percentage="cleanupStats.progress" :stroke-width="8" style="margin-bottom: 16px;" />
        <div v-for="item in cleanupItems" :key="item.id" style="display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--rs-border);">
          <el-checkbox :model-value="item.is_cleaned" @change="markCleaned(item.id)" />
          <span :style="{ textDecoration: item.is_cleaned ? 'line-through' : 'none', color: item.is_cleaned ? 'var(--rs-text-secondary)' : 'var(--rs-text-primary)' }">
            {{ item.description }}
          </span>
          <el-tag size="small">{{ item.item_type }}</el-tag>
          <span v-if="item.file_path" style="font-size: 12px; color: var(--rs-text-secondary);">{{ item.file_path }}</span>
        </div>
      </el-tab-pane>

      <el-tab-pane label="战果" name="loots">
        <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
          <h3>战果记录</h3>
          <el-button size="small" type="primary" @click="showAddLoot = true"><el-icon><Plus /></el-icon> 记录战果</el-button>
        </div>
        <el-table :data="loots">
          <el-table-column prop="loot_type" label="类型" width="120" />
          <el-table-column prop="title" label="标题" min-width="250" />
          <el-table-column prop="impact" label="影响" width="80"><template #default="{ row }"><span class="severity-badge" :class="row.impact">{{ row.impact }}</span></template></el-table-column>
          <el-table-column prop="description" label="描述" min-width="200" />
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- Dialogs omitted for brevity but follow same pattern as other pages -->
    <el-dialog v-model="showAddProxy" title="添加代理节点" width="520px">
      <el-form :model="proxyForm" label-width="100px">
        <el-form-item label="名称"><el-input v-model="proxyForm.name" /></el-form-item>
        <el-form-item label="类型"><el-select v-model="proxyForm.proxy_type"><el-option value="socks5" /><el-option value="socks4" /><el-option value="http" /><el-option value="ssh_tunnel" /></el-select></el-form-item>
        <el-form-item label="地址"><el-input v-model="proxyForm.host" /></el-form-item>
        <el-form-item label="端口"><el-input-number v-model="proxyForm.port" /></el-form-item>
        <el-form-item label="可达网段"><el-input v-model="proxyForm.cidrs_text" placeholder="每行一个CIDR" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="隧道工具"><el-select v-model="proxyForm.tunnel_tool" clearable><el-option value="frp" /><el-option value="chisel" /><el-option value="ssh" /><el-option value="suo5" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="showAddProxy = false">取消</el-button><el-button type="primary" @click="addProxy">添加</el-button></template>
    </el-dialog>

    <el-dialog v-model="showAddCred" title="添加凭据" width="480px">
      <el-form :model="credForm" label-width="80px">
        <el-form-item label="类型"><el-select v-model="credForm.cred_type"><el-option value="password" label="明文密码" /><el-option value="hash_ntlm" label="NTLM Hash" /><el-option value="ssh_key" label="SSH密钥" /><el-option value="cookie" label="Cookie" /><el-option value="token" label="Token" /></el-select></el-form-item>
        <el-form-item label="用户名"><el-input v-model="credForm.username" /></el-form-item>
        <el-form-item label="密码/值"><el-input v-model="credForm.secret" type="password" show-password /></el-form-item>
        <el-form-item label="来源"><el-input v-model="credForm.source" placeholder="如: 配置文件、mimikatz" /></el-form-item>
        <el-form-item label="来源主机"><el-input v-model="credForm.source_host" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showAddCred = false">取消</el-button><el-button type="primary" @click="addCredential">添加</el-button></template>
    </el-dialog>

    <el-dialog v-model="showAddHost" title="添加已控主机" width="520px">
      <el-form :model="hostForm" label-width="80px">
        <el-form-item label="IP"><el-input v-model="hostForm.ip" /></el-form-item>
        <el-form-item label="主机名"><el-input v-model="hostForm.hostname" /></el-form-item>
        <el-form-item label="权限"><el-select v-model="hostForm.access_level"><el-option value="user" /><el-option value="admin" /><el-option value="root" /><el-option value="system" label="SYSTEM" /><el-option value="domain_admin" label="域管理员" /></el-select></el-form-item>
        <el-form-item label="Shell类型"><el-select v-model="hostForm.shell_type"><el-option value="reverse_shell" /><el-option value="webshell" /><el-option value="ssh" /><el-option value="rdp" /><el-option value="beacon" /></el-select></el-form-item>
        <el-form-item label="入侵方式"><el-input v-model="hostForm.entry_method" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showAddHost = false">取消</el-button><el-button type="primary" @click="addHost">添加</el-button></template>
    </el-dialog>

    <el-dialog v-model="showAddLoot" title="记录战果" width="480px">
      <el-form :model="lootForm" label-width="80px">
        <el-form-item label="类型"><el-select v-model="lootForm.loot_type"><el-option value="database" label="数据库" /><el-option value="config" label="配置文件" /><el-option value="source_code" label="源代码" /><el-option value="document" label="文档" /><el-option value="credential_file" label="凭据文件" /></el-select></el-form-item>
        <el-form-item label="标题"><el-input v-model="lootForm.title" /></el-form-item>
        <el-form-item label="影响"><el-select v-model="lootForm.impact"><el-option value="critical" label="严重" /><el-option value="high" label="高" /><el-option value="medium" label="中" /></el-select></el-form-item>
        <el-form-item label="描述"><el-input v-model="lootForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showAddLoot = false">取消</el-button><el-button type="primary" @click="addLoot">添加</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../stores/api'

const route = useRoute()
const pid = route.params.id
const activeTab = ref('proxy')

const proxies = ref([]); const credentials = ref([]); const hosts = ref([])
const timeline = ref([]); const cleanupItems = ref([]); const cleanupStats = ref({ total: 0, cleaned: 0, progress: 0 })
const loots = ref([])

const showAddProxy = ref(false); const showAddCred = ref(false); const showAddHost = ref(false); const showAddLoot = ref(false)
const showUploadFile = ref(false); const uploadFileHostId = ref(null)
const uploadFileForm = ref({ path: '', description: '' })
const proxyForm = ref({ name: '', proxy_type: 'socks5', host: '', port: 1080, cidrs_text: '', tunnel_tool: '' })
const credForm = ref({ cred_type: 'password', username: '', secret: '', source: '', source_host: '' })
const hostForm = ref({ ip: '', hostname: '', access_level: 'root', shell_type: 'reverse_shell', entry_method: '' })
const lootForm = ref({ loot_type: 'database', title: '', impact: 'high', description: '' })

const loadAll = async () => {
  const [p, c, h, t, cl, l] = await Promise.all([
    api.get(`/projects/${pid}/ops/proxy`), api.get(`/projects/${pid}/ops/credentials`),
    api.get(`/projects/${pid}/ops/hosts`), api.get(`/projects/${pid}/ops/timeline`),
    api.get(`/projects/${pid}/ops/cleanup`), api.get(`/projects/${pid}/ops/loots`),
  ])
  proxies.value = p.items || []; credentials.value = c.items || []; hosts.value = h.items || []
  timeline.value = t.items || []; cleanupItems.value = cl.items || []
  cleanupStats.value = { total: cl.total, cleaned: cl.cleaned, progress: cl.progress }
  loots.value = l.items || []
}

const addProxy = async () => {
  const cidrs = proxyForm.value.cidrs_text.split('\n').filter(Boolean)
  await api.post(`/projects/${pid}/ops/proxy`, { ...proxyForm.value, reachable_cidrs: cidrs })
  showAddProxy.value = false; await loadAll()
}
const addCredential = async () => { await api.post(`/projects/${pid}/ops/credentials`, credForm.value); showAddCred.value = false; await loadAll() }
const addHost = async () => { await api.post(`/projects/${pid}/ops/hosts`, hostForm.value); showAddHost.value = false; await loadAll() }
const addLoot = async () => { await api.post(`/projects/${pid}/ops/loots`, lootForm.value); showAddLoot.value = false; await loadAll() }
const markCleaned = async (id) => { await api.put(`/projects/${pid}/ops/cleanup/${id}/mark`); await loadAll() }

const openUploadFile = (host) => { uploadFileHostId.value = host.id; uploadFileForm.value = { path: '', description: '' }; showUploadFile.value = true }
const recordUploadFile = async () => {
  if (!uploadFileForm.value.path) return
  await api.post(`/projects/${pid}/ops/hosts/${uploadFileHostId.value}/upload-file`, uploadFileForm.value)
  showUploadFile.value = false
  await loadAll()
}

const tunnelTool = ref('frp')
const tunnelVps = ref('')
const tunnelVpsPort = ref(7000)
const tunnelCommands = ref(null)

const getTunnelHelper = async () => {
  try {
    tunnelCommands.value = await api.get(`/projects/${pid}/ops/proxy/tunnel-helper`, { params: { tool: tunnelTool.value, vps_ip: tunnelVps.value || '1.2.3.4', vps_port: tunnelVpsPort.value } })
  } catch (e) { tunnelCommands.value = null }
}

onMounted(loadAll)
</script>
