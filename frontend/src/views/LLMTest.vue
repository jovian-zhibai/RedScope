<template>
  <div>
    <h2 style="margin-bottom: 16px;">LLM 安全测试</h2>
    <div class="card" style="padding: 20px; margin-bottom: 16px;">
      <el-form :model="form" label-width="100px">
        <el-form-item label="目标 URL"><el-input v-model="form.target_url" placeholder="LLM API 端点 (如 https://api.example.com/chat)" /></el-form-item>
        <el-form-item label="API Key"><el-input v-model="form.api_key" placeholder="可选" type="password" show-password /></el-form-item>
        <el-form-item label="自定义头">
          <el-input v-model="form.headers_text" type="textarea" :rows="2" placeholder='可选, JSON 格式: {"Authorization": "Bearer xxx"}' />
        </el-form-item>
        <el-form-item>
          <el-button type="danger" @click="runTest" :loading="running">开始 OWASP LLM Top 10 测试</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div v-if="results.length">
      <div class="stat-grid" style="margin-bottom: 16px;">
        <div class="stat-card success"><div class="stat-label">通过</div><div class="stat-value">{{ results.filter(r => r.passed).length }}</div></div>
        <div class="stat-card critical"><div class="stat-label">未通过</div><div class="stat-value">{{ results.filter(r => !r.passed).length }}</div></div>
        <div class="stat-card info"><div class="stat-label">总测试</div><div class="stat-value">{{ results.length }}</div></div>
      </div>

      <el-table :data="results" style="width: 100%;">
        <el-table-column prop="test_name" label="测试项" min-width="200" />
        <el-table-column prop="category" label="分类" width="150"><template #default="{ row }"><el-tag size="small">{{ row.category }}</el-tag></template></el-table-column>
        <el-table-column prop="passed" label="结果" width="80">
          <template #default="{ row }">
            <el-tag :type="row.passed ? 'success' : 'danger'" size="small">{{ row.passed ? '通过' : '未通过' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="risk_level" label="风险" width="80">
          <template #default="{ row }"><span v-if="!row.passed" class="severity-badge" :class="row.risk_level">{{ row.risk_level }}</span></template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" min-width="300">
          <template #default="{ row }"><span style="font-size: 12px; color: var(--rs-text-secondary);">{{ row.detail }}</span></template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../stores/api'

const route = useRoute()
const pid = route.params.id
const form = ref({ target_url: '', api_key: '', headers_text: '' })
const results = ref([])
const running = ref(false)

const runTest = async () => {
  if (!form.value.target_url) { ElMessage.warning('请输入目标 URL'); return }
  running.value = true
  try {
    let headers = null
    if (form.value.headers_text.trim()) {
      try { headers = JSON.parse(form.value.headers_text) } catch { ElMessage.warning('Headers 格式错误'); running.value = false; return }
    }
    const res = await api.post(`/projects/${pid}/llm-security-test`, {
      target_url: form.value.target_url,
      api_key: form.value.api_key,
      headers,
    })
    results.value = res.results || []
    const failed = res.failed || 0
    if (failed > 0) { ElMessage.warning(`测试完成: ${failed} 项未通过，已自动创建漏洞记录`) }
    else { ElMessage.success('所有测试均通过') }
  } catch (e) { ElMessage.error(e.response?.data?.detail || '测试执行失败') }
  finally { running.value = false }
}
</script>
