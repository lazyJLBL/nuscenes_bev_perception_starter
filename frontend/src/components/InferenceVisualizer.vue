<script setup>
import { ref, computed } from 'vue'
import api from '../api'

const props = defineProps({
  activeModelData: {
    type: Object,
    default: null
  },
  currentConfig: {
    type: Object,
    required: true
  },
  moduleId: {
    type: String,
    default: ''
  },
  subModuleId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['open-viewer'])

const isUploading = ref(false)
const isInferencing = ref(false)
const uploadedImage = ref(null)
const inferenceResult = ref(null)
const fileInput = ref(null)
const errorMessage = ref(null)
const uploadedFileInfo = ref(null)

// Compare mode states
const isCompareMode = ref(false)
const compareResults = ref({
})

const comparisonModels = computed(() => {
  const models = props.currentConfig?.modelsBySub?.[props.subModuleId] || []
  return models.filter(model => model.status === 'active' && ['pointpillars', 'lidar_cluster'].includes(model.id))
})

// Computed property to determine if the active submodule expects LiDAR point clouds
const isLidarInput = computed(() => {
  return props.subModuleId === 'lidar_data' || props.subModuleId === '3d_detection'
})

const triggerUpload = () => {
  fileInput.value.click()
}

const resetCompareResults = () => {
  compareResults.value = Object.fromEntries(comparisonModels.value.map(model => [model.id, null]))
}

const metricText = (model) => {
  if (!model.metrics) return model.accuracy || '待评测'
  if (typeof model.metrics.nd_score === 'number') {
    return `NDS ${model.metrics.nd_score.toFixed(3)} / mAP ${(model.metrics.mean_ap || 0).toFixed(3)}`
  }
  if (model.metrics.metric_source) return model.metrics.metric_source
  return model.accuracy || '待评测'
}

const latencyText = (model) => {
  if (model.latency === null || model.latency === undefined) return '未配置'
  return `${Number(model.latency).toFixed(1)} ms`
}

const memoryText = (model) => {
  if (model.memory === null || model.memory === undefined) return '未配置'
  return `${Number(model.memory).toFixed(1)} GB`
}

const fpsText = (model) => {
  if (model.fps === null || model.fps === undefined) return '未配置'
  return `${Number(model.fps).toFixed(0)} FPS`
}

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  errorMessage.value = null
  
  if (isCompareMode.value && isLidarInput.value) {
    uploadedImage.value = null
    uploadedFileInfo.value = {
      name: file.name,
      size: (file.size / 1024).toFixed(1) + ' KB'
    }
    inferenceResult.value = null
    resetCompareResults()
    
    isUploading.value = false
    isInferencing.value = true
    
    try {
      const modelIds = comparisonModels.value.map(model => model.id)
      if (modelIds.length === 0) {
        throw new Error('当前没有可运行的真实感知模型适配器。')
      }
      await Promise.all(modelIds.map(async (mId) => {
        const formData = new FormData()
        formData.append('file', file)
        const response = await api.post(`/inference/${mId}`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
        if (response.data.success) {
          compareResults.value[mId] = response.data.inference_result_url
          if (!uploadedFileInfo.value.points && response.data.num_points) {
            uploadedFileInfo.value = {
              ...uploadedFileInfo.value,
              points: response.data.num_points.toLocaleString(),
              channels: response.data.num_channels
            }
          }
        } else {
          throw new Error(response.data.error || `模型 ${mId} 推理失败。`)
        }
      }))
    } catch (error) {
      console.error('Compare inference error:', error)
      if (error.response && error.response.data && error.response.data.error) {
        errorMessage.value = error.response.data.error
      } else {
        errorMessage.value = error.message || '推理失败，请检查文件格式。'
      }
      uploadedFileInfo.value = null
    } finally {
      isInferencing.value = false
    }
  } else {
    uploadedImage.value = URL.createObjectURL(file)
    uploadedFileInfo.value = {
      name: file.name,
      size: (file.size / 1024).toFixed(1) + ' KB'
    }
    
    inferenceResult.value = null
    isUploading.value = true
    
    const formData = new FormData()
    formData.append('file', file)

    try {
      isUploading.value = false
      isInferencing.value = true
      
      const modelId = props.activeModelData?.id || 'unknown'
      const response = await api.post(`/inference/${modelId}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      
      if (response.data.success) {
        inferenceResult.value = response.data.inference_result_url
        
        if (isLidarInput.value) {
          uploadedFileInfo.value = {
            name: response.data.filename,
            size: (response.data.file_size / 1024).toFixed(1) + ' KB',
            points: response.data.num_points.toLocaleString(),
            channels: response.data.num_channels
          }
        } else {
          uploadedFileInfo.value = {
            name: response.data.filename,
            size: (response.data.file_size / 1024).toFixed(1) + ' KB'
          }
        }
      } else {
        errorMessage.value = response.data.error || '推理失败，请检查数据格式。'
        uploadedFileInfo.value = null
        uploadedImage.value = null
      }
    } catch (error) {
      console.error('Inference error:', error)
      if (error.response && error.response.data && error.response.data.error) {
        errorMessage.value = error.response.data.error
      } else {
        errorMessage.value = '推理失败，请检查后端服务是否开启以及文件格式是否正确。'
      }
      uploadedFileInfo.value = null
      uploadedImage.value = null
    } finally {
      isInferencing.value = false
    }
  }
}

const downloadAll = () => {
  const link = document.createElement('a')
  const payload = {
    activeModel: props.activeModelData,
    uploadedFile: uploadedFileInfo.value,
    inferenceResult: inferenceResult.value,
    compareResults: compareResults.value
  }
  link.href = 'data:application/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(payload, null, 2))
  link.download = 'perception_outputs_manifest.json'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  alert('已下载当前模型输出清单')
}

const openViewer = (url, alt) => {
  emit('open-viewer', url, alt)
}

// Need to expose a way to reset uploaded image when model changes
const resetUploadState = () => {
  uploadedImage.value = null
  inferenceResult.value = null
  errorMessage.value = null
  uploadedFileInfo.value = null
  resetCompareResults()
}

defineExpose({ resetUploadState })
</script>

<template>
  <div class="preview-panel glass-panel">
    <div class="preview-header">
      <h3>实时状态预览 / 识别测试</h3>
      <div class="preview-actions" v-if="activeModelData && activeModelData.outputImage">
        <label v-if="moduleId === 'perception' && subModuleId === '3d_detection'" class="compare-toggle">
          <input type="checkbox" v-model="isCompareMode" @change="resetUploadState" />
          <span>⚖️ 同屏对比模式</span>
        </label>
        <input type="file" ref="fileInput" @change="handleFileUpload" :accept="isLidarInput ? '.bin' : 'image/*'" style="display: none" />
        <button class="btn btn-secondary btn-sm" @click="triggerUpload">
          {{ isLidarInput ? (isCompareMode ? '📤 上传点云并发对比' : '📤 上传雷达点云 (.bin)') : '📤 上传测试图片' }}
        </button>
        <button class="btn btn-primary btn-sm" @click="downloadAll">📦 下载全部输出</button>
      </div>
    </div>
    
    <!-- LiDAR Upload Instructions Card -->
    <div v-if="!uploadedFileInfo && !errorMessage && activeModelData && isLidarInput" class="upload-instructions-card">
      <div class="inst-header">
        <span class="inst-icon">💡</span>
        <h4>如何上传与测试您的 3D 点云？</h4>
      </div>
      <p class="inst-desc">
        请在右上方上传您的激光雷达点云二进制文件 (<b>.bin</b>)。系统将自动校验点云文件的格式，并使用您选择的 3D 检测算法进行 BEV 推理。
      </p>
      <div class="format-spec-grid">
        <div class="spec-column">
          <h5>📁 文件格式要求</h5>
          <ul>
            <li>后缀名必须为 <code>.bin</code></li>
            <li>大小需大于 0 且为 4 字节的倍数</li>
            <li>解析后点数不得少于 100</li>
          </ul>
        </div>
        <div class="spec-column">
          <h5>📊 数据结构与通道</h5>
          <ul>
            <li><b>5 通道 (nuScenes 格式)</b>: <code>[x, y, z, intensity, ring]</code></li>
            <li><b>4 通道 (标准格式)</b>: <code>[x, y, z, intensity]</code></li>
            <li>系统将自动截取前 4 列输入 PointPillars 模型</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Camera Upload Instructions Card -->
    <div v-if="!uploadedFileInfo && !errorMessage && activeModelData && !isLidarInput" class="upload-instructions-card">
      <div class="inst-header">
        <span class="inst-icon">📷</span>
        <h4>如何上传与测试您的相机图像？</h4>
      </div>
      <p class="inst-desc">
        请在右上方上传您的相机图像文件 (<b>.jpg / .png</b>)。系统将自动对该图像进行视角对齐与多传感器数据预处理。
      </p>
      <div class="format-spec-grid">
        <div class="spec-column">
          <h5>📁 文件格式要求</h5>
          <ul>
            <li>文件后缀名支持 <code>.jpg</code>, <code>.jpeg</code>, <code>.png</code></li>
            <li>大小需大于 0 且图像未损坏</li>
          </ul>
        </div>
        <div class="spec-column">
          <h5>📊 图像预处理输出</h5>
          <ul>
            <li>校验并输出确定性图像预处理预览</li>
            <li>不会用模拟检测结果冒充真实感知模型</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Error Alert Box -->
    <div v-if="errorMessage" class="error-alert-box">
      <div class="error-icon">⚠️</div>
      <div class="error-content">
        <h4>数据校验失败 (Validation Error)</h4>
        <p>{{ errorMessage }}</p>
      </div>
    </div>

    <!-- Compare Mode Inference Workflow -->
    <div v-if="uploadedFileInfo && isCompareMode && isLidarInput && !errorMessage" class="compare-workflow">
      <div class="compare-meta-header">
        <h4>📡 正在对比评估点云文件: <span class="highlight-text">{{ uploadedFileInfo.name }}</span> ({{ uploadedFileInfo.size }})</h4>
        <p v-if="uploadedFileInfo.points">解析点数: {{ uploadedFileInfo.points }} | 格式: {{ uploadedFileInfo.channels }}通道</p>
      </div>

      <div class="compare-grid">
        <div v-for="model in comparisonModels" :key="model.id" class="compare-column">
          <div class="column-header">
            <h5>{{ model.name }}</h5>
            <span class="column-badge badge-blue">真实适配器</span>
          </div>
          <div v-if="compareResults[model.id]" class="img-container clickable" @click="openViewer(compareResults[model.id], `${model.name} Result`)">
            <img :src="compareResults[model.id]" :alt="model.name" />
            <div class="zoom-hint">🔍 点击放大</div>
          </div>
          <div v-else class="placeholder-box">
            <div class="loading-spinner"></div>
            <span>{{ model.name }} 推理中...</span>
          </div>
        </div>
      </div>

      <!-- Quantitative Comparison Table -->
      <div class="compare-table-wrapper glass-panel">
        <h4>📊 多维度量化指标评估 (Quantitative Benchmarking)</h4>
        <table class="compare-table">
          <thead>
            <tr>
              <th>模型名称 (Model)</th>
              <th>检测精度 (NDS)</th>
              <th>推理耗时 (Latency)</th>
              <th>显存占用 (Memory)</th>
              <th>帧率吞吐 (FPS)</th>
              <th>核心架构特征</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="model in comparisonModels" :key="model.id" :class="{ 'active-row': activeModelData && activeModelData.id === model.id }">
              <td class="model-name">{{ model.name }}</td>
              <td class="metric-val highlight-blue">{{ metricText(model) }}</td>
              <td>{{ latencyText(model) }}</td>
              <td>{{ memoryText(model) }}</td>
              <td>{{ fpsText(model) }}</td>
              <td>{{ model.desc }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Single Mode Upload & Inference Workflow -->
    <div v-else-if="uploadedFileInfo && !errorMessage" class="inference-workflow">
      <div class="inference-box">
        <h4>{{ isLidarInput ? '已加载点云数据' : '原始输入图片' }}</h4>
        <div v-if="isLidarInput" class="point-cloud-meta-box">
          <div class="meta-icon">📡</div>
          <div class="meta-item">
            <span class="meta-label">文件名称:</span>
            <span class="meta-val truncate" :title="uploadedFileInfo.name">{{ uploadedFileInfo.name }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">文件大小:</span>
            <span class="meta-val">{{ uploadedFileInfo.size }}</span>
          </div>
          <div v-if="uploadedFileInfo.points" class="meta-item">
            <span class="meta-label">解析点数:</span>
            <span class="meta-val highlight">{{ uploadedFileInfo.points }} 个点</span>
          </div>
          <div v-if="uploadedFileInfo.channels" class="meta-item">
            <span class="meta-label">通道格式:</span>
            <span class="meta-val">{{ uploadedFileInfo.channels }} 通道 (Float32)</span>
          </div>
        </div>
        <div v-else class="img-container clickable" @click="openViewer(uploadedImage, 'Uploaded Image')">
          <img :src="uploadedImage" alt="Uploaded" />
          <div class="zoom-hint">🔍 点击放大</div>
        </div>
      </div>
      
      <div class="inference-arrow">
        <div v-if="isInferencing" class="loading-spinner"></div>
        <span v-else>➡️</span>
        <p v-if="isInferencing">模型推理中...</p>
      </div>
      
      <div class="inference-box">
        <h4>{{ isLidarInput ? '3D 物体检测结果 (BEV)' : '预处理输出结果' }}</h4>
        <div v-if="inferenceResult" class="img-container clickable" @click="openViewer(inferenceResult, 'Inference Result')">
          <img :src="inferenceResult" alt="Result" />
          <div class="zoom-hint">🔍 点击放大</div>
        </div>
        <div v-else class="placeholder-box">
          <div class="loading-spinner" style="margin-bottom: 12px;"></div>
          正在运行模型...
        </div>
      </div>
    </div>

    <!-- Default Typical Output Visualization (when no upload active) -->
    <div v-else-if="activeModelData && activeModelData.outputImage && !errorMessage" class="real-output">
      <div class="output-row" v-if="activeModelData.camImage">
        <div class="img-container clickable" @click="openViewer(activeModelData.camImage, 'Camera/Input Output')">
          <span class="img-label">输入视角 (Input)</span>
          <img :src="activeModelData.camImage" alt="Input Output" />
          <div class="zoom-hint">🔍 点击放大</div>
        </div>
      </div>
      <div class="output-row">
        <div class="img-container clickable" @click="openViewer(activeModelData.outputImage, 'Processed Output')">
          <span class="img-label">数据处理结果 (Output)</span>
          <img :src="activeModelData.outputImage" alt="Output" />
          <div class="zoom-hint">🔍 点击放大</div>
        </div>
      </div>
    </div>
    
    <!-- Empty state -->
    <div v-else-if="!errorMessage" class="empty-state">
      <span class="empty-icon">⚙️</span>
      <p v-if="currentConfig.available">当前子模块未选择已就绪的模型</p>
      <p v-else>该模块尚未就绪，请先配置感知模块</p>
    </div>
  </div>
</template>

<style scoped>
.preview-panel {
  flex: 1;
  padding: 24px;
  display: flex;
  flex-direction: column;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.preview-header h3 {
  font-size: 1.1rem;
  color: #e2e8f0;
  margin: 0;
}

.preview-actions {
  display: flex;
  gap: 12px;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 0.85rem;
}

.real-output {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  overflow-y: auto;
}

.output-row {
  flex: 1;
  display: flex;
  min-height: 200px;
}

.img-container {
  position: relative;
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--glass-border);
  background: rgba(0,0,0,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}

.img-container img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.img-label {
  position: absolute;
  top: 10px;
  left: 10px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  z-index: 2;
}

/* Upload Instructions Card */
.upload-instructions-card {
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  backdrop-filter: blur(10px);
}

.inst-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.inst-header h4 {
  color: var(--accent-color);
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
}

.inst-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin: 0 0 16px 0;
  line-height: 1.5;
}

.format-spec-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 16px;
}

.spec-column h5 {
  color: #e2e8f0;
  margin: 0 0 8px 0;
  font-size: 0.85rem;
  font-weight: 500;
}

.spec-column ul {
  margin: 0;
  padding-left: 16px;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.spec-column li {
  margin-bottom: 6px;
  line-height: 1.4;
}

.spec-column code {
  background: rgba(0, 0, 0, 0.3);
  padding: 2px 4px;
  border-radius: 4px;
  color: #f87171;
  font-family: monospace;
}

/* Error Alert Box */
.error-alert-box {
  width: 100%;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 10px;
  padding: 12px 16px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}

.error-icon {
  font-size: 1.2rem;
}

.error-content h4 {
  color: #f87171;
  margin: 0 0 4px 0;
  font-size: 0.9rem;
  font-weight: 600;
}

.error-content p {
  color: #fca5a5;
  margin: 0;
  font-size: 0.8rem;
  line-height: 1.4;
}

/* Point Cloud Meta Box */
.point-cloud-meta-box {
  width: 100%;
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  padding: 20px;
  height: 300px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 14px;
}

.meta-icon {
  font-size: 2.5rem;
  text-align: center;
  margin-bottom: 8px;
}

.meta-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.05);
  padding-bottom: 8px;
}

.meta-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.meta-label {
  color: var(--text-secondary);
}

.meta-val {
  color: #e2e8f0;
  font-weight: 500;
  max-width: 180px;
  text-align: right;
}

.meta-val.highlight {
  color: var(--accent-color);
  font-weight: bold;
}

.truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Upload Workflow Styles */
.inference-workflow {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  flex: 1;
}

.inference-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  height: 100%;
}

.inference-box h4 {
  color: var(--text-secondary);
  font-weight: 500;
}

.inference-box .img-container {
  height: 300px;
}

.placeholder-box {
  width: 100%;
  height: 300px;
  border-radius: 12px;
  border: 1px dashed rgba(255, 255, 255, 0.2);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  background: rgba(0, 0, 0, 0.2);
}

.inference-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--accent-color);
  font-size: 1.5rem;
  gap: 10px;
}

.inference-arrow p {
  font-size: 0.8rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

.loading-spinner {
  width: 30px;
  height: 30px;
  border: 3px solid rgba(59, 130, 246, 0.3);
  border-radius: 50%;
  border-top-color: var(--accent-color);
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Clickable Images */
.clickable {
  cursor: pointer;
  transition: all 0.2s;
}

.clickable:hover {
  border-color: var(--accent-color);
  box-shadow: 0 0 15px rgba(59, 130, 246, 0.3);
}

.zoom-hint {
  position: absolute;
  bottom: 10px;
  right: 10px;
  background: rgba(0,0,0,0.7);
  color: white;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 0.75rem;
  opacity: 0;
  transition: opacity 0.2s;
  pointer-events: none;
}

.clickable:hover .zoom-hint {
  opacity: 1;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0.6;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 16px;
  filter: grayscale(1);
}

/* Compare Mode Styles */
.compare-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  color: var(--text-secondary);
  cursor: pointer;
  margin-right: 16px;
  user-select: none;
}

.compare-toggle input {
  cursor: pointer;
  accent-color: var(--accent-color);
}

.compare-workflow {
  display: flex;
  flex-direction: column;
  gap: 24px;
  width: 100%;
}

.compare-meta-header {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  padding-bottom: 12px;
}

.compare-meta-header h4 {
  margin: 0 0 4px 0;
  color: #f1f5f9;
}

.compare-meta-header p {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.highlight-text {
  color: var(--accent-color);
  font-weight: 600;
}

.compare-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  width: 100%;
}

.compare-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 4px;
}

.column-header h5 {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: #e2e8f0;
}

.column-badge {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 500;
}

.badge-blue {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.badge-green {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.badge-purple {
  background: rgba(168, 85, 247, 0.15);
  color: #c084fc;
  border: 1px solid rgba(168, 85, 247, 0.3);
}

.compare-column .img-container {
  height: 220px;
}

.compare-column .placeholder-box {
  height: 220px;
}

.compare-table-wrapper {
  padding: 20px;
  background: rgba(15, 23, 42, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.compare-table-wrapper h4 {
  margin: 0 0 16px 0;
  font-size: 0.95rem;
  color: #f1f5f9;
}

.compare-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.85rem;
}

.compare-table th, .compare-table td {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.compare-table th {
  font-weight: 600;
  color: var(--text-secondary);
  background: rgba(0, 0, 0, 0.2);
}

.compare-table tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

.compare-table tr.active-row {
  background: rgba(59, 130, 246, 0.08);
  border-left: 3px solid var(--accent-color);
}

.compare-table tr.active-row td {
  color: #f8fafc;
}

.model-name {
  font-weight: 500;
  color: #e2e8f0;
}

.metric-val {
  font-weight: 600;
}

.highlight-blue {
  color: #60a5fa;
}

.highlight-green {
  color: #34d399;
}

.highlight-purple {
  color: #c084fc;
}
</style>
