<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import ModelSelector from '../components/ModelSelector.vue'
import ImageViewerModal from '../components/ImageViewerModal.vue'
import InferenceVisualizer from '../components/InferenceVisualizer.vue'
import { useModuleStore } from '../store/moduleStore'

const props = defineProps({
  moduleId: {
    type: String,
    required: true
  }
})

const moduleStore = useModuleStore()

onMounted(() => {
  if (Object.keys(moduleStore.configs).length === 0) {
    moduleStore.fetchConfigs()
  }
})

// Sub-modules state
const currentSubModuleId = ref('')

// Image Viewer State
const isViewerOpen = ref(false)
const viewerImageUrl = ref('')
const viewerAltText = ref('')

const openViewer = (url, alt) => {
  viewerImageUrl.value = url
  viewerAltText.value = alt
  isViewerOpen.value = true
}

const currentConfig = computed(() => moduleStore.configs[props.moduleId] || { subModules: [] })

const visualizerRef = ref(null)

// Reset sub-module selection when module changes
watch(() => [props.moduleId, currentConfig.value], () => {
  if (currentConfig.value.subModules && currentConfig.value.subModules.length > 0) {
    // Keep current sub-module if it exists in the new list, else take the first one
    if (!currentConfig.value.subModules.find(s => s.id === currentSubModuleId.value)) {
        currentSubModuleId.value = currentConfig.value.subModules[0].id
    }
  } else {
    currentSubModuleId.value = ''
  }
  
  if (visualizerRef.value) {
    visualizerRef.value.resetUploadState()
  }
}, { immediate: true, deep: true })

const currentModels = computed(() => {
  if (!currentConfig.value.available) return []
  return currentConfig.value.modelsBySub?.[currentSubModuleId.value] || []
})

// Keep track of which model is currently selected in ModelSelector to show corresponding preview
const selectedModelId = ref('')
const handleModelSelected = (id) => {
  selectedModelId.value = id
  if (visualizerRef.value) {
    visualizerRef.value.resetUploadState()
  }
}

const activeModelData = computed(() => {
  return currentModels.value.find(m => m.id === selectedModelId.value) || null
})

</script>

<template>
  <div class="module-dashboard animate-fade-in" :key="moduleId">
    <div class="dashboard-header glass-panel">
      <div>
        <h2>{{ currentConfig.title || '加载中...' }}</h2>
        <p class="desc">{{ currentConfig.desc }}</p>
      </div>
      <div v-if="currentConfig.title && !currentConfig.available" class="coming-soon-badge">
        🚧 开发中 (Coming Soon)
      </div>
    </div>

    <div v-if="moduleStore.isLoading" class="loading-state">
       数据加载中...
    </div>
    
    <div v-else-if="currentConfig.title" class="content-wrapper">
      <!-- Sub-module Navigation -->
      <div class="sub-nav glass-panel">
        <h3>子模块细分</h3>
        <ul class="sub-nav-list">
          <li 
            v-for="sub in currentConfig.subModules" 
            :key="sub.id"
            class="sub-nav-item"
            :class="{ active: currentSubModuleId === sub.id }"
            @click="currentSubModuleId = sub.id"
          >
            {{ sub.name }}
          </li>
        </ul>
      </div>

      <div class="content-grid">
        <!-- Model Selection Area -->
        <div class="grid-col left-col">
          <ModelSelector 
            :module-id="moduleId" 
            :sub-module-id="currentSubModuleId"
            :initial-models="currentModels" 
            :available="currentConfig.available"
            @model-changed="handleModelSelected"
          />
        </div>

        <!-- Preview/Status Area -->
        <div class="grid-col right-col">
          <InferenceVisualizer
            ref="visualizerRef"
            :active-model-data="activeModelData"
            :current-config="currentConfig"
            :module-id="moduleId"
            :sub-module-id="currentSubModuleId"
            @open-viewer="openViewer"
          />
        </div>
      </div>
    </div>
    
    <!-- Image Viewer Modal -->
    <ImageViewerModal 
      v-if="isViewerOpen" 
      :image-url="viewerImageUrl" 
      :alt-text="viewerAltText" 
      @close="isViewerOpen = false" 
    />
  </div>
</template>

<style scoped>
.module-dashboard {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dashboard-header {
  padding: 24px 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dashboard-header h2 {
  font-size: 1.4rem;
  margin-bottom: 8px;
  color: #fff;
}

.desc {
  color: var(--text-secondary);
  font-size: 0.95rem;
  max-width: 600px;
}

.coming-soon-badge {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
  padding: 6px 16px;
  border-radius: 20px;
  font-weight: 500;
  font-size: 0.9rem;
}

.loading-state {
  display: flex;
  justify-content: center;
  align-items: center;
  flex: 1;
  color: var(--text-secondary);
  font-size: 1.2rem;
}

.content-wrapper {
  display: flex;
  gap: 20px;
  flex: 1;
}

.sub-nav {
  width: 220px;
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
}

.sub-nav h3 {
  font-size: 1.05rem;
  margin-bottom: 16px;
  color: #e2e8f0;
  padding-left: 12px;
  border-left: 3px solid var(--accent-color);
}

.sub-nav-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sub-nav-item {
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s ease;
  font-size: 0.95rem;
}

.sub-nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
}

.sub-nav-item.active {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  font-weight: 600;
}

.content-grid {
  display: flex;
  gap: 20px;
  flex: 1;
}

.grid-col {
  display: flex;
  flex-direction: column;
}

.left-col {
  flex: 1;
  min-width: 320px;
}

.right-col {
  flex: 1.8;
}
</style>
