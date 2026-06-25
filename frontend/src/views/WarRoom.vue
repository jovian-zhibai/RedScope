<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h2>作战管理</h2>
      <el-select v-model="pid" placeholder="选择项目" size="small" style="width: 240px;" @change="pid && $router.push(`/projects/${pid}/operations`)">
        <el-option v-for="p in projects" :key="p.id" :value="p.id" :label="p.name" />
      </el-select>
    </div>
    <div v-if="!pid" style="text-align: center; padding: 40px;">
      <div style="font-size: 48px; margin-bottom: 16px;">🎯</div>
      <div style="color: var(--rs-text-secondary); margin-bottom: 20px;">选择一个项目进入作战管理</div>
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; max-width: 600px; margin: 0 auto;">
        <div class="card onboard-step" @click="promptSelect('代理隧道')">
          <div style="font-size: 24px; margin-bottom: 8px;">🔗</div>
          <div style="font-weight: bold;">代理隧道</div>
          <div style="font-size: 12px; color: var(--rs-text-secondary);">SOCKS/HTTP 代理管理</div>
        </div>
        <div class="card onboard-step" @click="promptSelect('凭据管理')">
          <div style="font-size: 24px; margin-bottom: 8px;">🔑</div>
          <div style="font-weight: bold;">凭据管理</div>
          <div style="font-size: 12px; color: var(--rs-text-secondary);">密码/Hash/Token</div>
        </div>
        <div class="card onboard-step" @click="promptSelect('Shell看板')">
          <div style="font-size: 24px; margin-bottom: 8px;">🖥️</div>
          <div style="font-weight: bold;">Shell 看板</div>
          <div style="font-size: 12px; color: var(--rs-text-secondary);">已控主机管理</div>
        </div>
        <div class="card onboard-step" @click="promptSelect('攻击时间线')">
          <div style="font-size: 24px; margin-bottom: 8px;">📊</div>
          <div style="font-weight: bold;">攻击时间线</div>
          <div style="font-size: 12px; color: var(--rs-text-secondary);">ATT&CK 映射</div>
        </div>
        <div class="card onboard-step" @click="promptSelect('战后清理')">
          <div style="font-size: 24px; margin-bottom: 8px;">🧹</div>
          <div style="font-weight: bold;">战后清理</div>
          <div style="font-size: 12px; color: var(--rs-text-secondary);">清理检查清单</div>
        </div>
        <div class="card onboard-step" @click="promptSelect('战果记录')">
          <div style="font-size: 24px; margin-bottom: 8px;">🏆</div>
          <div style="font-weight: bold;">战果记录</div>
          <div style="font-size: 12px; color: var(--rs-text-secondary);">数据/配置/源码</div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../stores/api'
const router = useRouter()
const projects = ref([]); const pid = ref(null)
onMounted(async () => { try { const r = await api.get('/projects'); projects.value = r.items || [] } catch {} })
const promptSelect = (module) => {
  if (pid.value) { router.push(`/projects/${pid.value}/operations`); return }
  if (projects.value.length === 0) { ElMessage.info('请先创建一个项目'); return }
  ElMessage.info(`请先在上方选择一个项目，再进入${module}`)
}
</script>
