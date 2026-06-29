<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api from '../api'
import { Database, Plus, RefreshCw, Save, Settings2 } from 'lucide-vue-next'

const dbStatus = ref(null)
const models = ref([])
const scenarios = ref([])
const selectedModelId = ref(null)
const selectedScenarioId = ref(null)
const isLoading = ref(false)
const message = ref('')
const errorMessage = ref('')

const modelForm = reactive({
  model_key: '',
  name: '',
  subsystem: 'perception',
  category: '3d_detection',
  framework: 'pytorch',
  version: 'v1',
  status: 'active',
  description: '',
  artifact_uri: '',
  image_uri: '',
  config_json: '{}',
  metrics_json: '{}'
})

const scenarioForm = reactive({
  scenario_key: '',
  name: '',
  dataset_source: 'nuscenes',
  unity_scene_name: '',
  status: 'active',
  description: '',
  default_config_json: '{\n  "max_samples": 8\n}'
})

const selectedModel = computed(() => models.value.find(item => item.id === selectedModelId.value) || null)
const selectedScenario = computed(() => scenarios.value.find(item => item.id === selectedScenarioId.value) || null)

const parseJsonField = (value, label) => {
  try {
    return value?.trim() ? JSON.parse(value) : {}
  } catch (error) {
    throw new Error(`${label} 不是合法 JSON`)
  }
}

const setNotice = (text) => {
  message.value = text
  errorMessage.value = ''
}

const setError = (text) => {
  errorMessage.value = text
  message.value = ''
}

const fetchAll = async () => {
  isLoading.value = true
  try {
    const [statusRes, modelRes, scenarioRes] = await Promise.all([
      api.get('/db/status'),
      api.get('/admin/models'),
      api.get('/admin/scenarios')
    ])
    dbStatus.value = statusRes.data
    models.value = modelRes.data.models || []
    scenarios.value = scenarioRes.data.scenarios || []
    if (!selectedModelId.value && models.value.length) selectModel(models.value[0])
    if (!selectedScenarioId.value && scenarios.value.length) selectScenario(scenarios.value[0])
  } catch (error) {
    console.error('Failed to load admin data:', error)
    setError('无法读取管理员数据，请确认后端 DATABASE_URL 已配置并已初始化数据库。')
  } finally {
    isLoading.value = false
  }
}

const initDatabase = async () => {
  isLoading.value = true
  try {
    await api.post('/admin/db/init')
    setNotice('数据库表结构和初始数据已准备好。')
    await fetchAll()
  } catch (error) {
    console.error('Failed to initialize database:', error)
    setError('数据库初始化失败，请检查 MySQL 连接串。')
  } finally {
    isLoading.value = false
  }
}

const resetModelForm = () => {
  selectedModelId.value = null
  Object.assign(modelForm, {
    model_key: '',
    name: '',
    subsystem: 'perception',
    category: '3d_detection',
    framework: 'pytorch',
    version: 'v1',
    status: 'active',
    description: '',
    artifact_uri: '',
    image_uri: '',
    config_json: '{}',
    metrics_json: '{}'
  })
}

const selectModel = (model) => {
  selectedModelId.value = model.id
  Object.assign(modelForm, {
    model_key: model.model_key || '',
    name: model.name || '',
    subsystem: model.subsystem || 'perception',
    category: model.category || 'general',
    framework: model.framework || '',
    version: model.version || 'v1',
    status: model.status || 'active',
    description: model.description || '',
    artifact_uri: model.artifact_uri || '',
    image_uri: model.image_uri || '',
    config_json: JSON.stringify(model.config_json || {}, null, 2),
    metrics_json: JSON.stringify(model.metrics_json || {}, null, 2)
  })
}

const saveModel = async () => {
  try {
    const payload = {
      ...modelForm,
      config_json: parseJsonField(modelForm.config_json, '模型配置'),
      metrics_json: parseJsonField(modelForm.metrics_json, '模型指标')
    }
    if (selectedModel.value) {
      const { model_key, ...patchPayload } = payload
      await api.patch(`/admin/models/${selectedModel.value.id}`, patchPayload)
      setNotice('模型已更新。')
    } else {
      await api.post('/admin/models', payload)
      setNotice('模型已新增。')
    }
    await fetchAll()
  } catch (error) {
    console.error('Failed to save model:', error)
    setError(error.message || error.response?.data?.detail || '模型保存失败。')
  }
}

const resetScenarioForm = () => {
  selectedScenarioId.value = null
  Object.assign(scenarioForm, {
    scenario_key: '',
    name: '',
    dataset_source: 'nuscenes',
    unity_scene_name: '',
    status: 'active',
    description: '',
    default_config_json: '{\n  "max_samples": 8\n}'
  })
}

const selectScenario = (scenario) => {
  selectedScenarioId.value = scenario.id
  Object.assign(scenarioForm, {
    scenario_key: scenario.scenario_key || '',
    name: scenario.name || '',
    dataset_source: scenario.dataset_source || 'nuscenes',
    unity_scene_name: scenario.unity_scene_name || '',
    status: scenario.status || 'active',
    description: scenario.description || '',
    default_config_json: JSON.stringify(scenario.default_config_json || {}, null, 2)
  })
}

const saveScenario = async () => {
  try {
    const payload = {
      ...scenarioForm,
      default_config_json: parseJsonField(scenarioForm.default_config_json, '试验默认配置')
    }
    if (selectedScenario.value) {
      const { scenario_key, ...patchPayload } = payload
      await api.patch(`/admin/scenarios/${selectedScenario.value.id}`, patchPayload)
      setNotice('仿真试验已更新。')
    } else {
      await api.post('/admin/scenarios', payload)
      setNotice('仿真试验已新增。')
    }
    await fetchAll()
  } catch (error) {
    console.error('Failed to save scenario:', error)
    setError(error.message || error.response?.data?.detail || '仿真试验保存失败。')
  }
}

onMounted(fetchAll)
</script>

<template>
  <div class="admin-container animate-fade-in">
    <section class="admin-toolbar glass-panel">
      <div class="toolbar-title">
        <Database :size="24" />
        <div>
          <p class="eyebrow">Admin Console</p>
          <h2>模型与仿真试验管理</h2>
        </div>
      </div>
      <div class="toolbar-actions">
        <span class="db-pill" :class="{ online: dbStatus?.connected }">
          {{ dbStatus?.connected ? 'MySQL 在线' : 'MySQL 未连接' }}
        </span>
        <button class="tool-btn" :disabled="isLoading" @click="fetchAll">
          <RefreshCw :size="17" :class="{ spinning: isLoading }" />
          刷新
        </button>
        <button class="tool-btn primary" :disabled="isLoading" @click="initDatabase">
          <Settings2 :size="17" />
          初始化
        </button>
      </div>
    </section>

    <section v-if="message" class="notice-panel">{{ message }}</section>
    <section v-if="errorMessage" class="notice-panel error">{{ errorMessage }}</section>

    <section class="admin-grid">
      <div class="manager-panel glass-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Model Catalog</p>
            <h3>模型目录</h3>
          </div>
          <button class="icon-action" @click="resetModelForm" title="新增模型">
            <Plus :size="18" />
          </button>
        </div>

        <div class="split-layout">
          <div class="list-pane">
            <button
              v-for="model in models"
              :key="model.id"
              class="list-row"
              :class="{ active: selectedModelId === model.id }"
              @click="selectModel(model)"
            >
              <strong>{{ model.name }}</strong>
              <span>{{ model.subsystem }} / {{ model.status }}</span>
            </button>
          </div>

          <form class="edit-form" @submit.prevent="saveModel">
            <label>模型标识<input v-model="modelForm.model_key" class="form-control" :disabled="!!selectedModel" /></label>
            <label>模型名称<input v-model="modelForm.name" class="form-control" /></label>
            <div class="form-row">
              <label>子系统
                <select v-model="modelForm.subsystem" class="form-control">
                  <option value="preprocessing">preprocessing</option>
                  <option value="perception">perception</option>
                  <option value="decision">decision</option>
                  <option value="planning">planning</option>
                </select>
              </label>
              <label>状态
                <select v-model="modelForm.status" class="form-control">
                  <option value="active">active</option>
                  <option value="draft">draft</option>
                  <option value="disabled">disabled</option>
                  <option value="needs_checkpoint">needs_checkpoint</option>
                  <option value="unavailable">unavailable</option>
                </select>
              </label>
            </div>
            <div class="form-row">
              <label>分类<input v-model="modelForm.category" class="form-control" /></label>
              <label>框架<input v-model="modelForm.framework" class="form-control" /></label>
            </div>
            <label>模型文件/服务地址<input v-model="modelForm.artifact_uri" class="form-control" /></label>
            <label>描述<textarea v-model="modelForm.description" class="form-control" rows="3"></textarea></label>
            <label>配置 JSON<textarea v-model="modelForm.config_json" class="form-control mono" rows="5"></textarea></label>
            <label>指标 JSON<textarea v-model="modelForm.metrics_json" class="form-control mono" rows="5"></textarea></label>
            <button class="submit-btn" type="submit">
              <Save :size="17" />
              保存模型
            </button>
          </form>
        </div>
      </div>

      <div class="manager-panel glass-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Simulation Scenarios</p>
            <h3>仿真试验</h3>
          </div>
          <button class="icon-action" @click="resetScenarioForm" title="新增仿真试验">
            <Plus :size="18" />
          </button>
        </div>

        <div class="split-layout">
          <div class="list-pane">
            <button
              v-for="scenario in scenarios"
              :key="scenario.id"
              class="list-row"
              :class="{ active: selectedScenarioId === scenario.id }"
              @click="selectScenario(scenario)"
            >
              <strong>{{ scenario.name }}</strong>
              <span>{{ scenario.dataset_source }} / {{ scenario.status }}</span>
            </button>
          </div>

          <form class="edit-form" @submit.prevent="saveScenario">
            <label>试验标识<input v-model="scenarioForm.scenario_key" class="form-control" :disabled="!!selectedScenario" /></label>
            <label>试验名称<input v-model="scenarioForm.name" class="form-control" /></label>
            <div class="form-row">
              <label>数据来源
                <select v-model="scenarioForm.dataset_source" class="form-control">
                  <option value="nuscenes">nuscenes</option>
                  <option value="unity">unity</option>
                  <option value="mixed">mixed</option>
                </select>
              </label>
              <label>状态
                <select v-model="scenarioForm.status" class="form-control">
                  <option value="active">active</option>
                  <option value="draft">draft</option>
                  <option value="disabled">disabled</option>
                </select>
              </label>
            </div>
            <label>Unity 场景名<input v-model="scenarioForm.unity_scene_name" class="form-control" /></label>
            <label>描述<textarea v-model="scenarioForm.description" class="form-control" rows="3"></textarea></label>
            <label>默认配置 JSON<textarea v-model="scenarioForm.default_config_json" class="form-control mono" rows="7"></textarea></label>
            <button class="submit-btn" type="submit">
              <Save :size="17" />
              保存试验
            </button>
          </form>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.admin-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100%;
}

.admin-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 28px;
  border-radius: 8px;
}

.toolbar-title {
  display: flex;
  align-items: center;
  gap: 14px;
}

.toolbar-title svg {
  color: var(--accent-color);
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--text-secondary);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

h2,
h3 {
  margin: 0;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.db-pill {
  padding: 8px 10px;
  border: 1px solid rgba(248, 113, 113, 0.35);
  border-radius: 999px;
  color: #fecaca;
  background: rgba(127, 29, 29, 0.18);
  font-size: 0.82rem;
}

.db-pill.online {
  color: #bbf7d0;
  border-color: rgba(34, 197, 94, 0.35);
  background: rgba(20, 83, 45, 0.22);
}

.tool-btn,
.submit-btn,
.icon-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 40px;
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.06);
  cursor: pointer;
}

.tool-btn {
  padding: 0 14px;
}

.tool-btn.primary,
.submit-btn {
  border-color: rgba(59, 130, 246, 0.45);
  background: rgba(59, 130, 246, 0.22);
}

.tool-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.icon-action {
  width: 40px;
}

.notice-panel {
  padding: 14px 18px;
  border: 1px solid rgba(34, 197, 94, 0.35);
  border-radius: 8px;
  color: #bbf7d0;
  background: rgba(20, 83, 45, 0.2);
}

.notice-panel.error {
  color: #fecaca;
  border-color: rgba(248, 113, 113, 0.35);
  background: rgba(127, 29, 29, 0.2);
}

.admin-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.manager-panel {
  padding: 24px;
  border-radius: 8px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.split-layout {
  display: grid;
  grid-template-columns: minmax(220px, 0.42fr) minmax(420px, 1fr);
  gap: 18px;
}

.list-pane {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 640px;
  overflow: auto;
}

.list-row {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 12px;
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.04);
  cursor: pointer;
  text-align: left;
}

.list-row.active {
  border-color: rgba(59, 130, 246, 0.55);
  background: rgba(59, 130, 246, 0.14);
}

.list-row span {
  color: var(--text-secondary);
  font-size: 0.82rem;
}

.edit-form {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.edit-form label {
  display: grid;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 0.86rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.mono {
  font-family: Consolas, 'Courier New', monospace;
  font-size: 0.86rem;
}

.submit-btn {
  width: fit-content;
  padding: 0 18px;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1100px) {
  .admin-toolbar,
  .toolbar-actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .split-layout,
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
