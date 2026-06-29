<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api'
import { Database, FileJson, RefreshCw } from 'lucide-vue-next'

const records = ref([])
const isLoading = ref(false)
const errorMessage = ref('')
const sourceMode = ref('files')

const normalizeDbRun = (run) => {
  const metrics = run.metrics_json || {}
  const config = run.request_config_json || {}
  return {
    run_id: run.run_uid,
    created_at: run.created_at,
    status: run.status,
    spec: {
      preprocessing: config.preprocessing_model || run.models?.preprocessing?.model_key,
      perception_model: config.perception_model || run.models?.perception?.model_key,
      decision_model: config.decision_model || run.models?.decision?.model_key,
      planning_model: config.planning_model || run.models?.planning?.model_key
    },
    reports: {
      perception: { metrics: metrics.perception || {} },
      decision: { metrics: metrics.decision || {} },
      planning: { metrics: metrics.planning || {} }
    },
    scenario_name: run.scenario?.name || '未绑定场景',
    result_summary: run.result_summary || '',
    run_record_path: run.run_record_path
  }
}

const fetchExperiments = async () => {
  isLoading.value = true
  errorMessage.value = ''

  try {
    try {
      const dbResponse = await api.get('/client/runs', { params: { user_id: 2, limit: 12 } })
      records.value = (dbResponse.data.runs || []).map(normalizeDbRun)
      sourceMode.value = 'mysql'
    } catch (dbError) {
      const response = await api.get('/experiments', { params: { limit: 12 } })
      records.value = response.data.records || []
      sourceMode.value = 'files'
    }
  } catch (error) {
    console.error('Failed to fetch experiment records:', error)
    errorMessage.value = '无法读取实验记录，请确认后端已启动。'
  } finally {
    isLoading.value = false
  }
}

onMounted(fetchExperiments)

const latestRecords = computed(() => records.value.slice(0, 12))
const sourceIcon = computed(() => sourceMode.value === 'mysql' ? Database : FileJson)
const sourceLabel = computed(() => sourceMode.value === 'mysql' ? 'MySQL 客户记录' : '本地 JSON 记录')

const specOf = (record) => record.spec || {}

const metricsOf = (record, subsystem) => {
  return record.reports?.[subsystem]?.metrics || {}
}

const percent = (value, fallback = 'n/a') => {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return fallback
  return `${(Number(value) * 100).toFixed(1)}%`
}

const fixed = (value, digits = 1, unit = '') => {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return 'n/a'
  return `${Number(value).toFixed(digits)}${unit}`
}

const obstacleCount = (record) => {
  const planning = metricsOf(record, 'planning')
  if (planning.visual_obstacle_count !== undefined) return planning.visual_obstacle_count
  if (Array.isArray(planning.visual_obstacles)) return planning.visual_obstacles.length
  return 'n/a'
}

const runLabel = (record) => record.run_id || record.id || 'unknown-run'
</script>

<template>
  <div class="experiments-container animate-fade-in">
    <section class="summary-band glass-panel">
      <div>
        <p class="eyebrow">Experiment Records</p>
        <h2>我的仿真试验与结果</h2>
      </div>
      <div class="actions">
        <span class="source-pill">
          <component :is="sourceIcon" :size="16" />
          {{ sourceLabel }}
        </span>
        <button class="refresh-btn" :disabled="isLoading" @click="fetchExperiments">
          <RefreshCw :size="18" :class="{ spinning: isLoading }" />
          刷新
        </button>
      </div>
    </section>

    <section v-if="errorMessage" class="state-panel error-state">
      {{ errorMessage }}
    </section>

    <section v-else-if="isLoading" class="state-panel">
      正在读取实验记录...
    </section>

    <section v-else-if="latestRecords.length === 0" class="state-panel">
      暂无实验记录。请先回到实验沙盒运行一次 nuScenes 离线实验，或在管理员端创建仿真试验模板。
    </section>

    <section v-else class="records-grid">
      <article v-for="record in latestRecords" :key="runLabel(record)" class="record-card glass-panel">
        <div class="record-head">
          <div>
            <h3>{{ runLabel(record) }}</h3>
            <p>{{ record.created_at || 'unknown time' }}</p>
          </div>
          <span class="status-pill" :class="{ failed: record.status === 'failed' || record.status === 'unreadable' }">
            {{ record.status || 'completed' }}
          </span>
        </div>

        <div class="scenario-line">
          {{ record.scenario_name || 'nuScenes 离线实验' }}
        </div>

        <div class="pipeline-row">
          <span>{{ specOf(record).preprocessing || 'n/a' }}</span>
          <span>{{ specOf(record).perception_model || specOf(record).perception || 'n/a' }}</span>
          <span>{{ specOf(record).decision_model || specOf(record).decision || 'n/a' }}</span>
          <span>{{ specOf(record).planning_model || specOf(record).planning || 'n/a' }}</span>
        </div>

        <div class="metric-grid">
          <div>
            <label>障碍物</label>
            <strong>{{ obstacleCount(record) }}</strong>
          </div>
          <div>
            <label>Collision</label>
            <strong>{{ percent(metricsOf(record, 'planning').collision_rate) }}</strong>
          </div>
          <div>
            <label>ADE</label>
            <strong>{{ fixed(metricsOf(record, 'planning').ade, 2, ' m') }}</strong>
          </div>
          <div>
            <label>FDE</label>
            <strong>{{ fixed(metricsOf(record, 'planning').fde, 2, ' m') }}</strong>
          </div>
          <div>
            <label>Latency</label>
            <strong>{{ fixed(metricsOf(record, 'planning').latency_ms, 1, ' ms') }}</strong>
          </div>
          <div>
            <label>FPS</label>
            <strong>{{ fixed(metricsOf(record, 'perception').fps, 1) }}</strong>
          </div>
        </div>

        <p v-if="record.result_summary" class="summary-text">{{ record.result_summary }}</p>
        <p v-if="record.run_record_path" class="record-path">{{ record.run_record_path }}</p>
      </article>
    </section>
  </div>
</template>

<style scoped>
.experiments-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100%;
}

.summary-band {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28px 32px;
  border-radius: 8px;
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--text-secondary);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.summary-band h2 {
  margin: 0;
  font-size: 1.6rem;
}

.actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.source-pill,
.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 0 14px;
  border: 1px solid rgba(59, 130, 246, 0.35);
  border-radius: 8px;
  color: white;
  background: rgba(59, 130, 246, 0.18);
}

.refresh-btn {
  cursor: pointer;
}

.refresh-btn:disabled {
  opacity: 0.65;
  cursor: default;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.state-panel {
  padding: 28px 32px;
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  color: var(--text-secondary);
  background: rgba(15, 23, 42, 0.72);
}

.error-state {
  color: #fecaca;
  border-color: rgba(248, 113, 113, 0.4);
}

.records-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 16px;
}

.record-card {
  padding: 22px;
  border-radius: 8px;
}

.record-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.record-head h3 {
  margin: 0 0 6px;
  font-size: 1rem;
  word-break: break-word;
}

.record-head p,
.record-path,
.summary-text {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.84rem;
}

.status-pill {
  flex: 0 0 auto;
  padding: 6px 10px;
  border-radius: 999px;
  color: #bbf7d0;
  background: rgba(16, 185, 129, 0.16);
  border: 1px solid rgba(16, 185, 129, 0.28);
  font-size: 0.78rem;
}

.status-pill.failed {
  color: #fecaca;
  background: rgba(239, 68, 68, 0.16);
  border-color: rgba(239, 68, 68, 0.28);
}

.scenario-line {
  margin-bottom: 12px;
  color: var(--text-primary);
  font-weight: 600;
}

.pipeline-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 16px;
}

.pipeline-row span {
  min-height: 34px;
  padding: 8px;
  border-radius: 8px;
  color: #dbeafe;
  background: rgba(59, 130, 246, 0.12);
  border: 1px solid rgba(59, 130, 246, 0.2);
  font-size: 0.8rem;
  text-align: center;
  overflow-wrap: anywhere;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

.metric-grid div {
  padding: 12px;
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
}

.metric-grid label {
  display: block;
  margin-bottom: 6px;
  color: var(--text-secondary);
  font-size: 0.75rem;
}

.metric-grid strong {
  font-size: 1rem;
}

.summary-text {
  margin-bottom: 8px;
}

.record-path {
  word-break: break-all;
}

@media (max-width: 780px) {
  .summary-band,
  .actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .records-grid,
  .pipeline-row,
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
