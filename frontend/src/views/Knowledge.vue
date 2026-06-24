<template>
  <div>
    <h2 style="margin-bottom: 16px;">漏洞情报库</h2>
    <div style="display: flex; gap: 12px; margin-bottom: 16px;">
      <el-input v-model="keyword" placeholder="搜索漏洞..." style="width: 300px;" @keyup.enter="search" />
      <el-select v-model="severity" placeholder="等级" clearable style="width: 120px;" @change="search">
        <el-option value="critical" label="严重" /><el-option value="high" label="高危" /><el-option value="medium" label="中危" />
      </el-select>
      <el-button type="primary" @click="search">搜索</el-button>
    </div>
    <el-table :data="items" style="width: 100%;">
      <el-table-column prop="title" label="漏洞名称" min-width="300" />
      <el-table-column prop="cve_id" label="CVE" width="160" />
      <el-table-column prop="cnvd_id" label="CNVD" width="160" />
      <el-table-column prop="severity" label="等级" width="90"><template #default="{ row }"><span class="severity-badge" :class="row.severity">{{ row.severity }}</span></template></el-table-column>
      <el-table-column prop="affected_software" label="影响软件" width="150" />
      <el-table-column prop="weapon_stage" label="武器化" width="120">
        <template #default="{ row }">
          <el-tag :type="{disclosed:'info',poc_available:'warning',exp_available:'danger',in_the_wild:'danger'}[row.weapon_stage]" size="small">
            {{ {disclosed:'已披露',poc_available:'有PoC',exp_available:'有EXP',in_the_wild:'在野利用',mass_exploitation:'大规模利用'}[row.weapon_stage] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="has_poc" label="PoC" width="60"><template #default="{ row }">{{ row.has_poc ? '✅' : '❌' }}</template></el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../stores/api'
const keyword = ref(''); const severity = ref(''); const items = ref([])
const search = async () => { const res = await api.get('/knowledge', { params: { keyword: keyword.value || undefined, severity: severity.value || undefined } }); items.value = res.items || [] }
onMounted(search)
</script>
