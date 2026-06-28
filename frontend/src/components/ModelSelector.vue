<script setup>
import { ref, watch } from 'vue'
import AddModelModal from './AddModelModal.vue'

const props = defineProps({
  moduleId: String,
  initialModels: Array,
  available: Boolean
})

const emit = defineEmits(['model-changed'])

const models = ref([...props.initialModels])
const selectedModelId = ref(models.value.length > 0 ? models.value[0].id : null)
const isModalOpen = ref(false)

// Watch for prop changes (when switching modules)
watch(() => props.initialModels, (newVal) => {
  models.value = [...newVal]
  selectedModelId.value = models.value.length > 0 ? models.value[0].id : null
  emit('model-changed', selectedModelId.value)
}, { deep: true, immediate: true })

const selectModel = (id) => {
  selectedModelId.value = id
  emit('model-changed', id)
}

const handleAddModel = (newModel) => {
  const modelEntry = {
    id: newModel.id,
    name: newModel.name,
    status: 'testing',
    accuracy: 'N/A'
  }
  models.value.push(modelEntry)
  selectedModelId.value = modelEntry.id
  emit('model-changed', modelEntry.id)
  isModalOpen.value = false
}
</script>

<template>
  <div class="model-selector glass-panel">
    <div class="selector-header">
      <h3>可选模型列表</h3>
      <button v-if="available" class="btn btn-primary btn-sm" @click="isModalOpen = true">
        + 新增模型
      </button>
    </div>

    <div v-if="!available" class="unavailable-state">
      该模块暂时未开放模型选择。
    </div>
    
    <div v-else class="model-list">
      <div 
        v-for="model in models" 
        :key="model.id"
        class="model-card"
        :class="{ selected: selectedModelId === model.id }"
        @click="selectModel(model.id)"
      >
        <div class="model-info">
          <div class="model-name">{{ model.name }}</div>
          <div class="model-meta">
            <span class="badge" :class="model.status === 'active' ? 'badge-success' : 'badge-warning'">
              {{ model.status === 'active' ? '已部署' : '测试中' }}
            </span>
            <span class="accuracy" v-if="model.accuracy">准确率: {{ model.accuracy }}</span>
          </div>
        </div>
        <div class="radio-indicator">
          <div class="inner-circle" v-if="selectedModelId === model.id"></div>
        </div>
      </div>
      
      <div v-if="models.length === 0" class="no-models">
        暂无模型，请点击右上方添加。
      </div>
    </div>

    <!-- Modal for adding models -->
    <AddModelModal 
      v-if="isModalOpen" 
      :module-id="moduleId" 
      @close="isModalOpen = false" 
      @submit="handleAddModel" 
    />
  </div>
</template>

<style scoped>
.model-selector {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 24px;
}

.selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.selector-header h3 {
  font-size: 1.1rem;
  color: #e2e8f0;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 0.85rem;
}

.unavailable-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  font-style: italic;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.model-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.model-card:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.2);
}

.model-card.selected {
  background: rgba(59, 130, 246, 0.1);
  border-color: var(--accent-color);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.model-name {
  font-weight: 600;
  font-size: 1.05rem;
  color: #fff;
  margin-bottom: 8px;
}

.model-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.85rem;
}

.badge {
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 500;
}

.badge-success {
  background: rgba(16, 185, 129, 0.2);
  color: var(--success-color);
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.badge-warning {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.accuracy {
  color: var(--text-secondary);
}

.radio-indicator {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.model-card.selected .radio-indicator {
  border-color: var(--accent-color);
}

.inner-circle {
  width: 10px;
  height: 10px;
  background: var(--accent-color);
  border-radius: 50%;
  animation: popIn 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

@keyframes popIn {
  from { transform: scale(0); }
  to { transform: scale(1); }
}

.no-models {
  text-align: center;
  padding: 30px;
  color: var(--text-secondary);
}
</style>
