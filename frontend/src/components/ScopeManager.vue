<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
      <h3>边界管理</h3>
      <el-button size="small" type="primary" @click="showAdd = true" v-if="mode === 'combat'"><el-icon><Plus /></el-icon> 添加规则</el-button>
    </div>

    <el-alert v-if="mode === 'range'" type="info" show-icon :closable="false" style="margin-bottom: 12px;">
      靶场模式：边界检查已关闭，仅对公网IP进行提醒
    </el-alert>
    <el-alert v-if="mode === 'research'" type="info" show-icon :closable="false" style="margin-bottom: 12px;">
      研究模式：无边界限制
    </el-alert>

    <el-table :data="rules" style="width: 100%;" v-if="rules.length">
      <el-table-column prop="rule_type" label="类型" width="80">
        <template #default="{ row }">
          <el-tag :type="row.rule_type === 'include' ? 'success' : 'danger'" size="small">
            {{ row.rule_type === 'include' ? '白名单' : '黑名单' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="target_type" label="目标类型" width="100" />
      <el-table-column prop="target_value" label="目标值" min-width="200" />
      <el-table-column prop="description" label="备注" min-width="150" />
      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <el-button type="danger" size="small" text @click="deleteRule(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else description="暂无边界规则" />

    <el-dialog v-model="showAdd" title="添加边界规则" width="480px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="类型">
          <el-radio-group v-model="form.rule_type">
            <el-radio value="include">白名单(允许)</el-radio>
            <el-radio value="exclude">黑名单(禁止)</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="目标类型">
          <el-select v-model="form.target_type">
            <el-option value="domain" label="域名" /><el-option value="ip" label="IP" />
            <el-option value="cidr" label="CIDR网段" /><el-option value="url" label="URL" /><el-option value="port" label="端口" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标值"><el-input v-model="form.target_value" placeholder="如 *.example.com 或 192.168.1.0/24" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.description" placeholder="如: 客户支付系统不能碰" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="addRule">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../stores/api'

const props = defineProps({ projectId: Number, mode: String })
const rules = ref([])
const showAdd = ref(false)
const form = ref({ rule_type: 'include', target_type: 'cidr', target_value: '', description: '' })

const load = async () => { const res = await api.get(`/projects/${props.projectId}/scope`); rules.value = res.items || [] }
const addRule = async () => { await api.post(`/projects/${props.projectId}/scope`, form.value); showAdd.value = false; await load() }
const deleteRule = async (id) => { await api.delete(`/projects/${props.projectId}/scope/${id}`); await load() }
onMounted(load)
</script>
