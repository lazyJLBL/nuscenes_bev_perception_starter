<script setup>
import { ref } from 'vue'

const props = defineProps({
  moduleId: String
})

const emit = defineEmits(['close', 'submit'])

const modelName = ref('')
const modelId = ref('')

const handleSubmit = () => {
  if (!modelName.value || !modelId.value) return
  emit('submit', { id: modelId.value, name: modelName.value })
}
</script>

<template>
  <div class="modal-overlay animate-fade-in" @click.self="emit('close')">
    <div class="modal-content glass-panel">
      <div class="modal-header">
        <h2>添加新模型</h2>
        <button class="close-btn" @click="emit('close')">&times;</button>
      </div>
      
      <div class="modal-body">
        <div class="form-group">
          <label>模型标识 (ID)</label>
          <input 
            type="text" 
            class="form-control" 
            v-model="modelId" 
            placeholder="例如: centerpoint_v1"
          />
        </div>
        <div class="form-group">
          <label>模型显示名称</label>
          <input 
            type="text" 
            class="form-control" 
            v-model="modelName" 
            placeholder="例如: CenterPoint"
          />
        </div>
        
        <div class="info-box">
          <span class="info-icon">ℹ️</span>
          <p>添加后仅登记模型元信息；需要后端真实适配器和实验记录后才会参与对比。</p>
        </div>
      </div>
      
      <div class="modal-footer">
        <button class="btn btn-secondary" @click="emit('close')">取消</button>
        <button 
          class="btn btn-primary" 
          @click="handleSubmit"
          :disabled="!modelName || !modelId"
        >
          确认添加
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-content {
  width: 100%;
  max-width: 450px;
  background: var(--bg-color); /* Overriding glass-panel slightly for opacity */
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h2 {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 1.5rem;
  cursor: pointer;
  transition: color 0.2s;
}

.close-btn:hover {
  color: white;
}

.modal-body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.info-box {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  margin-top: 8px;
}

.info-box p {
  font-size: 0.85rem;
  color: #bfdbfe;
  margin: 0;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
