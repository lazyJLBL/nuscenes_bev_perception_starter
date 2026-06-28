<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api'
import { RefreshCw, Server } from 'lucide-vue-next'

const health = ref(null)
const isLoading = ref(false)
const errorMessage = ref('')

const fetchHealth = async () => {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await api.get('/health')
    health.value = response.data
  } catch (error) {
    console.error('Failed to fetch backend health:', error)
    health.value = null
    errorMessage.value = '后端未连接，请检查 8010 端口服务。'
  } finally {
    isLoading.value = false
  }
}

onMounted(fetchHealth)

const capabilities = computed(() => {
  if (!health.value?.capabilities) return []
  return Object.entries(health.value.capabilities).map(([key, value]) => ({ key, value }))
})

const routes = computed(() => {
  if (!health.value) return []
  return [
    { label: 'CWD', value: health.value.cwd },
    { label: 'Project Root', value: health.value.project_root },
    { label: 'routes.py', value: health.value.routes_path },
    { label: 'planning.py', value: health.value.planning_path }
  ]
})
</script>

<template>
  <div class="system-container animate-fade-in">
    <section class="status-band glass-panel">
      <div class="status-title">
        <Server :size="26" />
        <div>
          <p class="eyebrow">Runtime Health</p>
          <h2>后端系统状态</h2>
        </div>
      </div>

      <button class="refresh-btn" :disabled="isLoading" @click="fetchHealth">
        <RefreshCw :size="18" :class="{ spinning: isLoading }" />
        刷新
      </button>
    </section>

    <section v-if="errorMessage" class="state-panel error-state">
      {{ errorMessage }}
    </section>

    <section v-else-if="isLoading && !health" class="state-panel">
      正在读取后端状态...
    </section>

    <section v-else-if="health" class="status-grid">
      <div class="runtime-card glass-panel">
        <label>Backend PID</label>
        <strong>{{ health.pid }}</strong>
        <p>{{ health.success ? 'Connected' : 'Unavailable' }}</p>
      </div>

      <div class="runtime-card glass-panel">
        <label>能力检查</label>
        <div class="capability-list">
          <span
            v-for="item in capabilities"
            :key="item.key"
            class="capability-pill"
            :class="{ enabled: item.value, disabled: !item.value }"
          >
            {{ item.key }}: {{ item.value ? 'on' : 'off' }}
          </span>
        </div>
      </div>

      <div class="path-panel glass-panel">
        <div v-for="item in routes" :key="item.label" class="path-row">
          <span>{{ item.label }}</span>
          <code>{{ item.value || 'n/a' }}</code>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.system-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100%;
}

.status-band {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28px 32px;
}

.status-title {
  display: flex;
  align-items: center;
  gap: 14px;
}

.status-title svg {
  color: var(--accent-color);
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--text-secondary);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.status-band h2 {
  margin: 0;
  font-size: 1.6rem;
}

.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 0 16px;
  border: 1px solid rgba(59, 130, 246, 0.35);
  border-radius: 8px;
  color: white;
  background: rgba(59, 130, 246, 0.18);
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

.status-grid {
  display: grid;
  grid-template-columns: minmax(220px, 0.7fr) minmax(320px, 1.3fr);
  gap: 16px;
}

.runtime-card,
.path-panel {
  padding: 24px;
  border-radius: 8px;
}

.runtime-card label {
  display: block;
  margin-bottom: 12px;
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.runtime-card strong {
  display: block;
  margin-bottom: 8px;
  color: var(--text-primary);
  font-size: 2rem;
}

.runtime-card p {
  margin: 0;
  color: var(--success-color);
}

.capability-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.capability-pill {
  padding: 8px 10px;
  border-radius: 999px;
  font-size: 0.82rem;
}

.capability-pill.enabled {
  color: #bbf7d0;
  background: rgba(16, 185, 129, 0.14);
  border: 1px solid rgba(16, 185, 129, 0.25);
}

.capability-pill.disabled {
  color: #fecaca;
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.25);
}

.path-panel {
  grid-column: 1 / -1;
}

.path-row {
  display: grid;
  grid-template-columns: 140px minmax(0, 1fr);
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
}

.path-row:last-child {
  border-bottom: 0;
}

.path-row span {
  color: var(--text-secondary);
}

.path-row code {
  color: var(--text-primary);
  overflow-wrap: anywhere;
}

@media (max-width: 900px) {
  .status-grid {
    grid-template-columns: 1fr;
  }

  .path-row {
    grid-template-columns: 1fr;
  }
}
</style>
