<script setup>
import { ref } from 'vue'

const props = defineProps({
  imageUrl: {
    type: String,
    required: true
  },
  altText: {
    type: String,
    default: 'Image Viewer'
  }
})

const emit = defineEmits(['close'])

const scale = ref(1)
const isDragging = ref(false)
const position = ref({ x: 0, y: 0 })
const startPos = ref({ x: 0, y: 0 })

const handleZoomIn = () => { scale.value += 0.25 }
const handleZoomOut = () => { scale.value = Math.max(0.25, scale.value - 0.25) }
const handleReset = () => {
  scale.value = 1
  position.value = { x: 0, y: 0 }
}

const handleDownload = () => {
  const link = document.createElement('a')
  link.href = props.imageUrl
  link.download = props.imageUrl.split('/').pop() || 'download.jpg'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// Drag logic
const startDrag = (e) => {
  isDragging.value = true
  startPos.value = { x: e.clientX - position.value.x, y: e.clientY - position.value.y }
}

const doDrag = (e) => {
  if (!isDragging.value) return
  position.value = {
    x: e.clientX - startPos.value.x,
    y: e.clientY - startPos.value.y
  }
}

const stopDrag = () => {
  isDragging.value = false
}
</script>

<template>
  <div class="image-viewer-overlay" @click.self="emit('close')" @mousemove="doDrag" @mouseup="stopDrag" @mouseleave="stopDrag">
    <div class="toolbar glass-panel">
      <button class="tool-btn" @click="handleZoomIn" title="放大">🔍+</button>
      <button class="tool-btn" @click="handleZoomOut" title="缩小">🔍-</button>
      <button class="tool-btn" @click="handleReset" title="重置视角">🔄</button>
      <button class="tool-btn download-btn" @click="handleDownload" title="下载图片">📥 下载</button>
      <button class="tool-btn close-btn" @click="emit('close')" title="关闭">&times;</button>
    </div>

    <div class="image-container">
      <img 
        :src="imageUrl" 
        :alt="altText"
        class="viewer-img"
        :style="{ 
          transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
          cursor: isDragging ? 'grabbing' : 'grab'
        }"
        @mousedown.prevent="startDrag"
        draggable="false"
      />
    </div>
  </div>
</template>

<style scoped>
.image-viewer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(8px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.toolbar {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 12px;
  padding: 12px 20px;
  z-index: 10000;
  border-radius: 30px;
  background: rgba(20, 25, 40, 0.8);
}

.tool-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 1.1rem;
}

.tool-btn:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: scale(1.05);
}

.download-btn {
  width: auto;
  padding: 0 16px;
  border-radius: 20px;
  background: rgba(59, 130, 246, 0.6);
  border-color: rgba(59, 130, 246, 0.8);
  font-size: 0.95rem;
}

.download-btn:hover {
  background: rgba(59, 130, 246, 0.8);
}

.close-btn {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.4);
  font-size: 1.5rem;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.5);
}

.image-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.viewer-img {
  max-width: 90%;
  max-height: 90vh;
  object-fit: contain;
  transition: transform 0.1s ease-out;
  box-shadow: 0 10px 40px rgba(0,0,0,0.5);
  border-radius: 8px;
}
</style>
