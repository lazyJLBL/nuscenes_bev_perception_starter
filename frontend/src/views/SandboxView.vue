<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useModuleStore } from '../store/moduleStore'
import api from '../api'
import { 
  Play, 
  Pause, 
  RotateCcw, 
  Cpu, 
  ShieldCheck, 
  TrendingUp, 
  Sparkles, 
  Zap, 
  Gauge
} from 'lucide-vue-next'

const moduleStore = useModuleStore()

onMounted(() => {
  if (Object.keys(moduleStore.configs).length === 0) {
    moduleStore.fetchConfigs()
  }
  fetchBackendHealth()
  fetchCarlaStatus()
  fetchCarlaBootstrap()
})

// Selected pipeline models
const selectedPrep = ref('')
const selectedPer = ref('')
const selectedDec = ref('')
const selectedPlan = ref('')

// Initialize defaults when configurations are loaded
watch(() => moduleStore.configs, (newConfigs) => {
  if (newConfigs && Object.keys(newConfigs).length > 0) {
    if (!selectedPrep.value) selectedPrep.value = 'cam_surround'
    if (!selectedPer.value) selectedPer.value = 'pointpillars'
    if (!selectedDec.value) selectedDec.value = 'fsm_decision'
    if (!selectedPlan.value) selectedPlan.value = 'mpc_smoothing'
  }
}, { immediate: true, deep: true })

// Get models lists from store
const prepModels = computed(() => {
  const sub = moduleStore.configs.preprocessing?.modelsBySub || {}
  const list = []
  for (const mList of Object.values(sub)) {
    list.push(...mList)
  }
  return list
})

const perModels = computed(() => {
  return moduleStore.configs.perception?.modelsBySub?.['3d_detection'] || []
})

const decModels = computed(() => {
  return moduleStore.configs.decision?.modelsBySub?.['behavior_decision'] || []
})

const planModels = computed(() => {
  return moduleStore.configs.planning?.modelsBySub?.['path_planning'] || []
})

// Current model configurations computed
const activePrepConfig = computed(() => prepModels.value.find(m => m.id === selectedPrep.value) || null)
const activePerConfig = computed(() => perModels.value.find(m => m.id === selectedPer.value) || null)
const activeDecConfig = computed(() => decModels.value.find(m => m.id === selectedDec.value) || null)
const activePlanConfig = computed(() => planModels.value.find(m => m.id === selectedPlan.value) || null)

// Simulation Execution States
const timesteps = ref([])
const stats = ref(null)
const simulationImage = ref('')
const obstacles = ref([])
const sandboxWarnings = ref([])
const coordinateFrame = ref(null)
const visualSampleToken = ref('')
const visualSampleSource = ref('')
const visualSceneScore = ref(null)
const backendHealth = ref(null)
const isLoadingSim = ref(false)
const carlaStatus = ref(null)
const carlaScenarios = ref([])
const selectedCarlaScenarioId = ref(null)
const isStartingCarla = ref(false)
const isRunningCarla = ref(false)
const carlaResult = ref(null)
const carlaError = ref('')

const currentStep = ref(0)
const isPlaying = ref(false)
let playInterval = null

const runSimulation = async () => {
  if (!selectedPrep.value || !selectedPer.value || !selectedDec.value || !selectedPlan.value) {
    alert('请选择完整链路的 4 阶段算法模型！')
    return
  }
  
  isLoadingSim.value = true
  isPlaying.value = false
  currentStep.value = 0
  if (playInterval) clearInterval(playInterval)
  
  try {
    const response = await api.post('/run_sandbox', {
      preprocessing: selectedPrep.value,
      perception: selectedPer.value,
      decision: selectedDec.value,
      planning: selectedPlan.value
    })
    
    if (response.data.success) {
      timesteps.value = response.data.timesteps
      stats.value = response.data.stats
      simulationImage.value = response.data.simulation_image
      obstacles.value = response.data.obstacles || []
      sandboxWarnings.value = response.data.warnings || []
      coordinateFrame.value = response.data.coordinate_frame || null
      visualSampleToken.value = response.data.visual_sample_token || ''
      visualSampleSource.value = response.data.visual_sample_source || ''
      visualSceneScore.value = response.data.visual_scene_score ?? null
      
      isPlaying.value = true
      startPlayback()
    }
  } catch (error) {
    console.error('Failed to run sandbox simulation:', error)
    alert('仿真运行失败，请检查后端服务。')
  } finally {
    isLoadingSim.value = false
  }
}

const fetchBackendHealth = async () => {
  try {
    const response = await api.get('/health')
    backendHealth.value = response.data
  } catch (error) {
    backendHealth.value = null
    console.warn('Backend health check failed:', error)
  }
}

const fetchCarlaStatus = async () => {
  try {
    const response = await api.get('/carla/status')
    carlaStatus.value = response.data
  } catch (error) {
    carlaStatus.value = null
    console.warn('CARLA status check failed:', error)
  }
}

const fetchCarlaBootstrap = async () => {
  try {
    const response = await api.get('/client/bootstrap')
    const scenarios = response.data.scenarios || []
    carlaScenarios.value = scenarios.filter(item => item.dataset_source === 'carla' && item.status === 'active')
    if (!selectedCarlaScenarioId.value && carlaScenarios.value.length > 0) {
      selectedCarlaScenarioId.value = carlaScenarios.value[0].id
    }
  } catch (error) {
    carlaScenarios.value = [
      {
        id: null,
        name: 'Town03 Urban Traffic',
        carla_town: 'Town03',
        default_config_json: {
          duration_seconds: 10,
          weather: 'ClearNoon',
          traffic_vehicles: 10,
          traffic_walkers: 0,
          spawn_point_index: 0,
          synchronous_mode: false
        }
      }
    ]
    selectedCarlaScenarioId.value = null
  }
}

const selectedCarlaScenario = computed(() => {
  return carlaScenarios.value.find(item => item.id === selectedCarlaScenarioId.value) || carlaScenarios.value[0] || null
})

const selectedCarlaConfig = computed(() => selectedCarlaScenario.value?.default_config_json || {})

const startCarla = async () => {
  isStartingCarla.value = true
  carlaError.value = ''
  try {
    const response = await api.post('/carla/start', { windowed: true, res_x: 1280, res_y: 720 })
    if (!response.data.success) {
      carlaError.value = response.data.error || 'CARLA 启动失败'
    }
    await fetchCarlaStatus()
  } catch (error) {
    carlaError.value = 'CARLA 启动请求失败，请检查后端服务。'
  } finally {
    isStartingCarla.value = false
  }
}

const runCarlaSimulation = async () => {
  const scenario = selectedCarlaScenario.value
  const config = selectedCarlaConfig.value
  isRunningCarla.value = true
  carlaError.value = ''
  carlaResult.value = null
  try {
    const response = await api.post('/carla/run', {
      user_id: 2,
      scenario_id: scenario?.id || null,
      town: scenario?.carla_town || config.town || 'Town03',
      duration_seconds: config.duration_seconds || 10,
      weather: config.weather || 'ClearNoon',
      traffic_vehicles: config.traffic_vehicles ?? 10,
      traffic_walkers: config.traffic_walkers ?? 0,
      ego_vehicle: config.ego_vehicle || 'vehicle.tesla.model3',
      spawn_point_index: config.spawn_point_index || 0,
      synchronous_mode: config.synchronous_mode === true
    })
    if (!response.data.success) {
      carlaError.value = response.data.error || 'CARLA 仿真运行失败'
      return
    }
    carlaResult.value = response.data
    timesteps.value = response.data.timesteps || []
    stats.value = {
      ...(response.data.stats || {}),
      total_latency_ms: Number(response.data.metrics?.duration_seconds || 0) * 1000,
      safety_score: response.data.metrics?.collision_count === 0 ? 100 : 60,
      comfort_score: Math.max(0, 100 - (response.data.metrics?.collision_count || 0) * 20),
      efficiency_score: Math.min(100, response.data.metrics?.average_speed_kmh || 0)
    }
    obstacles.value = []
    sandboxWarnings.value = []
    currentStep.value = 0
    isPlaying.value = true
    startPlayback()
    await fetchCarlaStatus()
  } catch (error) {
    console.error('Failed to run CARLA simulation:', error)
    carlaError.value = 'CARLA 仿真请求失败，请确认 CARLA 已启动且 Python API 可用。'
  } finally {
    isRunningCarla.value = false
  }
}

const startPlayback = () => {
  if (playInterval) clearInterval(playInterval)
  playInterval = setInterval(() => {
    if (currentStep.value < timesteps.value.length - 1) {
      currentStep.value++
    } else {
      isPlaying.value = false
      clearInterval(playInterval)
    }
  }, 150) // ~10Hz tick speed in slow motion
}

const togglePlay = () => {
  if (isPlaying.value) {
    isPlaying.value = false
    if (playInterval) clearInterval(playInterval)
  } else {
    if (currentStep.value >= timesteps.value.length - 1) {
      currentStep.value = 0
    }
    isPlaying.value = true
    startPlayback()
  }
}

const stopPlayback = () => {
  isPlaying.value = false
  if (playInterval) clearInterval(playInterval)
}

const replay = () => {
  currentStep.value = 0
  isPlaying.value = true
  startPlayback()
}

// Current frame metrics mapping
const currentFrameData = computed(() => {
  if (timesteps.value.length === 0) return null
  return timesteps.value[currentStep.value]
})

const currentSpeedMps = computed(() => {
  if (!currentFrameData.value) return 0
  return currentFrameData.value.speed_mps ?? currentFrameData.value.speed ?? 0
})

const currentSpeedKmh = computed(() => {
  if (!currentFrameData.value) return 0
  return currentFrameData.value.speed_kmh ?? currentSpeedMps.value * 3.6
})

const visibleSandboxWarnings = computed(() => {
  const warnings = [...sandboxWarnings.value]
  if (stats.value && obstacles.value.length === 0) {
    warnings.push('后端未返回可视障碍物，请检查 /api/health 是否为最新进程。')
  }
  return warnings
})

const coordinateFrameLabel = computed(() => {
  if (!coordinateFrame.value) return 'ego: x forward, y left'
  return `ego: x=${coordinateFrame.value.x}, y=${coordinateFrame.value.y}`
})

// Latency breakdown calculations for dynamic waterfall chart
const currentFrameLatencyBreakdown = computed(() => {
  if (!currentFrameData.value) return null
  const bd = currentFrameData.value.latency_breakdown
  if (!bd) return null
  const total = bd.preprocessing + bd.perception + bd.decision + bd.planning
  return {
    total: total.toFixed(1),
    preprocessing: bd.preprocessing,
    perception: bd.perception,
    decision: bd.decision,
    planning: bd.planning,
    w_prep: (bd.preprocessing / total * 100).toFixed(1) + '%',
    w_per: (bd.perception / total * 100).toFixed(1) + '%',
    w_dec: (bd.decision / total * 100).toFixed(1) + '%',
    w_plan: (bd.planning / total * 100).toFixed(1) + '%'
  }
})

// Backend trajectory uses the ego frame: x = forward meters, y = left meters.
// SVG uses horizontal pixels for lateral position and vertical pixels for forward motion.
const roadCenterXPx = 180
const roadBottomYPx = 430
const lateralScalePx = 20
const forwardScalePx = 10

const mapX = (lateralMeters) => {
  return roadCenterXPx - lateralMeters * lateralScalePx
}

const mapY = (forwardMeters) => {
  return roadBottomYPx - forwardMeters * forwardScalePx
}

const obstacleWidthPx = (obs) => {
  return Math.max(14, Math.min(70, (obs.width || 2.0) * lateralScalePx))
}

const obstacleLengthPx = (obs) => {
  return Math.max(18, Math.min(90, (obs.length || 4.0) * forwardScalePx))
}

const obstacleBufferPx = (obs) => {
  return Math.max(10, (obs.safety_buffer || 1.2) * lateralScalePx)
}

const pathPoints = computed(() => {
  return timesteps.value.map(t => `${mapX(t.y)},${mapY(t.x)}`).join(' ')
})
</script>

<template>
  <div class="sandbox-container animate-fade-in">
    <div class="carla-card glass-panel">
      <div class="carla-head">
        <div>
          <p class="carla-eyebrow">CARLA Simulation</p>
          <h2>CARLA 可视化仿真沙盒</h2>
          <p>选择管理员配置的 CARLA 场景，启动本地 CarlaUE4.exe，并运行一次可视窗口仿真。</p>
        </div>
        <div class="carla-status" :class="{ online: carlaStatus?.connected, missing: !carlaStatus?.installed }">
          {{ carlaStatus?.connected ? 'CARLA 已连接' : carlaStatus?.installed ? 'CARLA 未连接' : 'CARLA 未安装' }}
        </div>
      </div>

      <div class="carla-grid">
        <label class="carla-field">
          场景
          <select v-model="selectedCarlaScenarioId">
            <option
              v-for="scenario in carlaScenarios"
              :key="scenario.id ?? scenario.scenario_key"
              :value="scenario.id"
            >
              {{ scenario.name }} / {{ scenario.carla_town || 'Town03' }}
            </option>
          </select>
        </label>

        <div class="carla-metrics">
          <span>Town: {{ selectedCarlaScenario?.carla_town || 'Town03' }}</span>
          <span>天气: {{ selectedCarlaConfig.weather || 'ClearNoon' }}</span>
          <span>车辆: {{ selectedCarlaConfig.traffic_vehicles ?? 10 }}</span>
          <span>行人: {{ selectedCarlaConfig.traffic_walkers ?? 0 }}</span>
          <span>时长: {{ selectedCarlaConfig.duration_seconds || 10 }}s</span>
        </div>

        <div class="carla-actions">
          <button class="btn btn-secondary" :disabled="isStartingCarla" @click="startCarla">
            {{ isStartingCarla ? '正在启动...' : '启动 CARLA' }}
          </button>
          <button class="btn btn-primary" :disabled="isRunningCarla" @click="runCarlaSimulation">
            {{ isRunningCarla ? '正在运行 CARLA...' : '运行 CARLA 仿真' }}
          </button>
          <button class="btn btn-secondary" @click="fetchCarlaStatus">刷新状态</button>
        </div>
      </div>

      <div v-if="carlaError" class="carla-error">{{ carlaError }}</div>

      <div v-if="carlaResult" class="carla-result">
        <img v-if="carlaResult.camera_image_url" :src="carlaResult.camera_image_url" alt="CARLA camera result" />
        <div class="carla-result-stats">
          <div><label>Run</label><strong>{{ carlaResult.run_uid }}</strong></div>
          <div><label>距离</label><strong>{{ carlaResult.metrics?.distance_m }} m</strong></div>
          <div><label>碰撞</label><strong>{{ carlaResult.metrics?.collision_count }}</strong></div>
          <div><label>平均速度</label><strong>{{ carlaResult.metrics?.average_speed_kmh }} km/h</strong></div>
        </div>
      </div>
    </div>

    <!-- Header Configurations -->
    <div class="header-card glass-panel">
      <div class="card-intro">
        <h2>🛠️ nuScenes 离线实验沙盒 (Offline AD Benchmark)</h2>
        <p>在离线实验沙盒中，您可以组合预处理、感知、决策和规划模块，在 nuScenes 场景上生成真实实验记录与多维度指标。</p>
      </div>

      <div class="configurator-grid">
        <!-- Preprocessing -->
        <div class="selector-box">
          <label>1. 数据预处理</label>
          <select v-model="selectedPrep" @change="stopPlayback">
            <option v-for="m in prepModels" :key="m.id" :value="m.id">
              {{ m.name }}
            </option>
          </select>
        </div>

        <!-- Perception -->
        <div class="selector-box">
          <label>2. 感知网络 (3D 检测)</label>
          <select v-model="selectedPer" @change="stopPlayback">
            <option v-for="m in perModels" :key="m.id" :value="m.id">
              {{ m.name }}
            </option>
          </select>
        </div>

        <!-- Decision -->
        <div class="selector-box">
          <label>3. 决策策略</label>
          <select v-model="selectedDec" @change="stopPlayback">
            <option v-for="m in decModels" :key="m.id" :value="m.id">
              {{ m.name }}
            </option>
          </select>
        </div>

        <!-- Planning -->
        <div class="selector-box">
          <label>4. 规控与路径规划</label>
          <select v-model="selectedPlan" @change="stopPlayback">
            <option v-for="m in planModels" :key="m.id" :value="m.id">
              {{ m.name }}
            </option>
          </select>
        </div>
      </div>

      <div class="action-bar">
        <button 
          class="btn btn-primary btn-lg play-sim-btn" 
          :disabled="isLoadingSim"
          @click="runSimulation"
        >
          <span v-if="isLoadingSim" class="spinner-inline"></span>
          <span v-else>🚀</span>
          {{ isLoadingSim ? '正运行离线实验...' : '运行 nuScenes 离线实验' }}
        </button>
      </div>
    </div>

    <!-- Simulation Results & Reports -->
    <div v-if="stats && timesteps.length > 0" class="sandbox-results-grid">
      <!-- Left: Simulation Grid -->
      <div class="sim-panel glass-panel">
        <div class="panel-header">
          <h3>LiDAR BEV 避障仿真监视器</h3>
          <div class="playback-controls">
            <button class="icon-btn-ctrl" @click="togglePlay" :title="isPlaying ? '暂停' : '播放'">
              <Pause v-if="isPlaying" :size="18" />
              <Play v-else :size="18" />
            </button>
            <button class="icon-btn-ctrl" @click="replay" title="重新播放">
              <RotateCcw :size="18" />
            </button>
            <span class="obstacle-counter" :class="{ empty: obstacles.length === 0 }">障碍: {{ obstacles.length }}</span>
            <span class="frame-counter">帧数: {{ currentStep + 1 }}/50</span>
          </div>
        </div>

        <div class="sim-view-viewport">
          <!-- Dynamic SVG Road Map -->
          <svg class="road-svg" viewBox="0 0 360 480" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="roadGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="#1e293b" />
                <stop offset="100%" stop-color="#0f172a" />
              </linearGradient>
            </defs>

            <!-- Background Road -->
            <rect width="360" height="480" fill="url(#roadGrad)" />
            
            <!-- Road Shoulders -->
            <line x1="80" y1="0" x2="80" y2="480" stroke="#475569" stroke-width="4" />
            <line x1="280" y1="0" x2="280" y2="480" stroke="#475569" stroke-width="4" />
            
            <!-- Lane Divider Dashed lines -->
            <line x1="180" y1="0" x2="180" y2="480" stroke="#94a3b8" stroke-width="2" stroke-dasharray="15,20" />

            <!-- Planned Obstacle Avoidance Path -->
            <polyline 
              :points="pathPoints" 
              fill="none" 
              stroke="rgba(59, 130, 246, 0.4)" 
              stroke-width="3" 
              stroke-dasharray="6,6" 
            />

            <!-- Scene Obstacles from the same nuScenes frame used by the planner -->
            <g
              v-for="(obs, index) in obstacles"
              :key="`obstacle-${index}`"
              :class="{ 'obstacle-outside-road': obs.in_road === false }"
              :transform="`translate(${mapX(obs.y)}, ${mapY(obs.x)})`"
            >
              <ellipse
                :rx="obstacleWidthPx(obs) / 2 + obstacleBufferPx(obs)"
                :ry="obstacleLengthPx(obs) / 2 + obstacleBufferPx(obs)"
                fill="rgba(239, 68, 68, 0.08)"
                stroke="rgba(248, 113, 113, 0.35)"
                stroke-width="1.5"
                stroke-dasharray="5,5"
              />
              <rect
                :x="-obstacleWidthPx(obs) / 2"
                :y="-obstacleLengthPx(obs) / 2"
                :width="obstacleWidthPx(obs)"
                :height="obstacleLengthPx(obs)"
                rx="4"
                fill="rgba(239, 68, 68, 0.92)"
                stroke="#f87171"
                stroke-width="2"
              />
              <text x="0" y="5" font-size="14" text-anchor="middle" fill="white" font-weight="bold">
                {{ obs.in_road === false ? '边' : '!' }}
              </text>
            </g>

            <!-- Ego Vehicle -->
            <g v-if="currentFrameData" :transform="`translate(${mapX(currentFrameData.y)}, ${mapY(currentFrameData.x)}) rotate(${-currentFrameData.yaw})`">
              <!-- Shadow -->
              <rect x="-11" y="-21" width="22" height="42" rx="4" fill="black" opacity="0.3" />
              <!-- Car body -->
              <rect x="-10" y="-20" width="20" height="40" rx="4" fill="var(--accent-color)" stroke="#60a5fa" stroke-width="2" />
              <!-- Windshield -->
              <rect x="-8" y="-11" width="16" height="8" rx="1" fill="rgba(255,255,255,0.25)" />
              <!-- Wheels -->
              <rect x="-12" y="-16" width="2" height="8" rx="1" fill="#475569" />
              <rect x="10" y="-16" width="2" height="8" rx="1" fill="#475569" />
              <rect x="-12" y="8" width="2" height="8" rx="1" fill="#475569" />
              <rect x="10" y="8" width="2" height="8" rx="1" fill="#475569" />
              <!-- Headlights -->
              <polygon points="-8,-19 -4,-19 -6,-21" fill="#eab308" />
              <polygon points="8,-19 4,-19 6,-21" fill="#eab308" />
            </g>
          </svg>

          <div v-if="stats && obstacles.length === 0" class="obstacle-empty-warning">
            后端未返回可视障碍物，请检查 /api/health 或重启后端。
          </div>

          <!-- Floating Frame Telemetry Info -->
          <div v-if="currentFrameData" class="telemetry-box">
            <div class="tel-row">
              <span class="label">速度 (Speed):</span>
              <span class="value">
                {{ currentSpeedKmh.toFixed(1) }} km/h
                <small>({{ currentSpeedMps.toFixed(2) }} m/s)</small>
              </span>
            </div>
            <div class="tel-row">
              <span class="label">前轮转角 (Steering):</span>
              <span class="value" :class="{ 'steering-left': currentFrameData.steering > 1, 'steering-right': currentFrameData.steering < -1 }">
                {{ currentFrameData.steering.toFixed(1) }}°
              </span>
            </div>
            <div class="tel-row">
              <span class="label">航向角 (Yaw):</span>
              <span class="value">{{ currentFrameData.yaw.toFixed(1) }}°</span>
            </div>
          </div>
        </div>

        <div class="sandbox-debug-strip">
          <span>样本: {{ visualSampleToken || 'n/a' }}</span>
          <span>来源: {{ visualSampleSource || 'n/a' }}</span>
          <span>坐标: {{ coordinateFrameLabel }}</span>
          <span v-if="visualSceneScore !== null">场景分: {{ Number(visualSceneScore).toFixed(1) }}</span>
          <span v-if="backendHealth">PID: {{ backendHealth.pid }}</span>
        </div>

        <div v-if="visibleSandboxWarnings.length" class="sandbox-warning-list">
          <div v-for="(warning, index) in visibleSandboxWarnings" :key="`sandbox-warning-${index}`">
            {{ warning }}
          </div>
        </div>

        <div class="scrubber-bar">
          <input 
            type="range" 
            min="0" 
            :max="timesteps.length - 1" 
            v-model.number="currentStep" 
            @input="stopPlayback" 
            class="range-slider"
          />
        </div>
      </div>

      <!-- Right: Benchmark Report -->
      <div class="report-panel">
        <!-- Overview Scores -->
        <div class="score-card-grid">
          <div class="glass-panel stat-box">
            <div class="stat-icon-wrapper blue-bg">
              <Zap :size="20" class="stat-icon" />
            </div>
            <div class="stat-info">
              <span class="stat-label">链路平均耗时</span>
              <span class="stat-val">{{ stats.total_latency_ms }} ms</span>
            </div>
          </div>

          <div class="glass-panel stat-box">
            <div class="stat-icon-wrapper purple-bg">
              <Gauge :size="20" class="stat-icon" />
            </div>
            <div class="stat-info">
              <span class="stat-label">帧率吞吐 (FPS)</span>
              <span class="stat-val">{{ stats.average_fps }} FPS</span>
            </div>
          </div>

          <div class="glass-panel stat-box">
            <div class="stat-icon-wrapper gray-bg">
              <Cpu :size="20" class="stat-icon" />
            </div>
            <div class="stat-info">
              <span class="stat-label">峰值显存占用</span>
              <span class="stat-val">{{ stats.total_memory_gb }} GB</span>
            </div>
          </div>
        </div>

        <!-- AD E2E KPI Scores Panel -->
        <div class="glass-panel kpi-panel">
          <h3>🏆 全链路端到端性能评分 (End-to-End Scorecard)</h3>
          
          <div class="kpi-gauges-container">
            <!-- Safety Score -->
            <div class="kpi-gauge">
              <div class="circular-progress" :style="`background: conic-gradient(#ef4444 ${stats.safety_score * 3.6}deg, rgba(255,255,255,0.05) 0deg)`">
                <div class="inner-value">{{ stats.safety_score }}%</div>
              </div>
              <span class="kpi-label">🛡️ 安全通行</span>
              <p class="kpi-desc">受感知算法检出精度与决策层安全冗余规则深度制约。</p>
            </div>

            <!-- Comfort Score -->
            <div class="kpi-gauge">
              <div class="circular-progress" :style="`background: conic-gradient(#10b981 ${stats.comfort_score * 3.6}deg, rgba(255,255,255,0.05) 0deg)`">
                <div class="inner-value">{{ stats.comfort_score }}%</div>
              </div>
              <span class="kpi-label">🛋️ 乘坐舒适</span>
              <p class="kpi-desc">完全受规划算法的几何平滑度与动力学加速度控制。</p>
            </div>

            <!-- Efficiency Score -->
            <div class="kpi-gauge">
              <div class="circular-progress" :style="`background: conic-gradient(#3b82f6 ${stats.efficiency_score * 3.6}deg, rgba(255,255,255,0.05) 0deg)`">
                <div class="inner-value">{{ stats.efficiency_score }}%</div>
              </div>
              <span class="kpi-label">⚡ 通行效率</span>
              <p class="kpi-desc">由决策模块的博弈换道倾向以及路线跟随速率决定。</p>
            </div>
          </div>
        </div>

        <!-- Frame Latency Waterfall Breakdown -->
        <div v-if="currentFrameLatencyBreakdown" class="glass-panel waterfall-panel">
          <div class="waterfall-header">
            <h3>⏳ 链路时延流式瀑布图 (Latency Breakdown)</h3>
            <span class="badge-time">当前帧总时延: {{ currentFrameLatencyBreakdown.total }} ms</span>
          </div>

          <div class="timeline-stack-bar">
            <div class="bar-segment prep" :style="{ width: currentFrameLatencyBreakdown.w_prep }" title="预处理"></div>
            <div class="bar-segment per" :style="{ width: currentFrameLatencyBreakdown.w_per }" title="感知"></div>
            <div class="bar-segment dec" :style="{ width: currentFrameLatencyBreakdown.w_dec }" title="决策"></div>
            <div class="bar-segment plan" :style="{ width: currentFrameLatencyBreakdown.w_plan }" title="规划"></div>
          </div>

          <div class="timeline-legend">
            <div class="legend-item">
              <span class="dot yellow"></span>
              <span class="name">预处理:</span>
              <span class="ms">{{ currentFrameLatencyBreakdown.preprocessing.toFixed(1) }}ms</span>
            </div>
            <div class="legend-item">
              <span class="dot blue"></span>
              <span class="name">感知检测:</span>
              <span class="ms">{{ currentFrameLatencyBreakdown.perception.toFixed(1) }}ms</span>
            </div>
            <div class="legend-item">
              <span class="dot green"></span>
              <span class="name">行为决策:</span>
              <span class="ms">{{ currentFrameLatencyBreakdown.decision.toFixed(1) }}ms</span>
            </div>
            <div class="legend-item">
              <span class="dot purple"></span>
              <span class="name">局部规划:</span>
              <span class="ms">{{ currentFrameLatencyBreakdown.planning.toFixed(1) }}ms</span>
            </div>
          </div>
        </div>

        <!-- Pipeline combination verdict -->
        <div class="glass-panel verdict-panel">
          <div class="verdict-header">
            <Sparkles :size="20" class="verdict-icon" />
            <h4>🧠 智驾链路架构师专家诊断与选型建议</h4>
          </div>
          
          <div class="verdict-content">
            <p v-if="selectedPer === 'pointpillars' && selectedPlan === 'hybrid_astar'">
              🚨 <b>诊断：轻量检测 + 搜索式规划，延迟可控但舒适性需关注</b><br>
              当前系统属于<b>极轻量级</b>链条，平均耗时仅约 {{ stats.total_latency_ms }} ms，对车辆计算硬件要求极低。
              但如果 PointPillars 当前指标偏低，搜索式路径的横向偏移也会放大舒适度问题，适合作为 smoke baseline。
            </p>
            <p v-else-if="selectedPer === 'lidar_cluster' && selectedPlan === 'mpc_smoothing'">
              💎 <b>诊断：确定性 smoke baseline，最适合验证实验管线</b><br>
              <b>LiDAR Cluster</b> 不依赖训练，能快速暴露数据格式、坐标系和可视化问题；<b>MPC-style smoothing</b> 会优先降低轨迹 jerk。
              这组结果不应和深度检测模型精度直接等价比较，但非常适合做端到端管线验收。
            </p>
            <p v-else-if="selectedDec === 'rl_decision'">
              🌟 <b>诊断：强化学习高博弈模型</b><br>
              使用 <b>RL PPO</b> 智能博弈模型，决策换道干脆利落，效率表现高达 95%+。搭配当前的 <b>{{ activePlanConfig?.name }}</b> 规划网络，能在极短时间完成避障博弈。
              建议监控长尾安全误判红线，辅助设置安全启发式备用状态机以作冗余防线。
            </p>
            <p v-else>
              💡 <b>诊断：结构化传统安全方案</b><br>
              <b>有限状态机 (FSM)</b> 在决策阶段充当了可靠的安全红线盾牌，安全冗余高。
              搭配 <b>{{ activePlanConfig?.name }}</b> 可以满足基本的常规安全驾驶要求，决策时延几乎为 0 毫秒，但在紧凑超车等动态交互场景下可能因状态限制表现得过于死板。
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty/Instruction state -->
    <div v-else class="empty-state-intro glass-panel">
      <div class="icon-sphere">⚙️</div>
      <h3>请点击“运行 nuScenes 离线实验”按钮</h3>
      <p>配置好四阶段算法模块后，平台会读取 nuScenes 场景，生成实验记录、链路时延、决策安全率、规划碰撞率、舒适度和轨迹误差等指标。</p>
    </div>
  </div>
</template>

<style scoped>
.sandbox-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 8px 16px 24px;
}

.carla-card {
  padding: 24px;
  border-radius: 8px;
}

.carla-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.carla-head h2 {
  margin: 0 0 8px;
  font-size: 1.5rem;
}

.carla-head p {
  margin: 0;
  color: var(--text-secondary);
}

.carla-eyebrow {
  margin: 0 0 6px;
  color: var(--accent-color);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.carla-status {
  flex: 0 0 auto;
  padding: 8px 12px;
  border: 1px solid rgba(250, 204, 21, 0.35);
  border-radius: 999px;
  color: #fef3c7;
  background: rgba(113, 63, 18, 0.22);
  font-size: 0.84rem;
}

.carla-status.online {
  color: #bbf7d0;
  border-color: rgba(34, 197, 94, 0.35);
  background: rgba(20, 83, 45, 0.22);
}

.carla-status.missing {
  color: #fecaca;
  border-color: rgba(248, 113, 113, 0.35);
  background: rgba(127, 29, 29, 0.2);
}

.carla-grid {
  display: grid;
  grid-template-columns: minmax(260px, 0.7fr) minmax(320px, 1fr) auto;
  gap: 16px;
  align-items: end;
}

.carla-field {
  display: grid;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 0.86rem;
}

.carla-field select {
  min-height: 42px;
  padding: 0 12px;
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  color: var(--text-primary);
  background: rgba(0, 0, 0, 0.28);
}

.carla-metrics {
  display: grid;
  grid-template-columns: repeat(5, minmax(80px, 1fr));
  gap: 8px;
}

.carla-metrics span {
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 8px;
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.04);
  font-size: 0.82rem;
  text-align: center;
}

.carla-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.carla-error {
  margin-top: 14px;
  padding: 12px 14px;
  border: 1px solid rgba(248, 113, 113, 0.35);
  border-radius: 8px;
  color: #fecaca;
  background: rgba(127, 29, 29, 0.2);
}

.carla-result {
  display: grid;
  grid-template-columns: minmax(280px, 420px) 1fr;
  gap: 16px;
  margin-top: 16px;
}

.carla-result img {
  width: 100%;
  border-radius: 8px;
  border: 1px solid var(--glass-border);
}

.carla-result-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.carla-result-stats div {
  padding: 12px;
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
}

.carla-result-stats label {
  display: block;
  margin-bottom: 6px;
  color: var(--text-secondary);
  font-size: 0.78rem;
}

.carla-result-stats strong {
  overflow-wrap: anywhere;
}

/* Header Card Configurations */
.header-card {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.card-intro h2 {
  font-size: 1.35rem;
  color: #fff;
  margin: 0 0 8px 0;
  font-weight: 600;
}

.card-intro p {
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.5;
  margin: 0;
}

.configurator-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.selector-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.selector-box label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.selector-box select {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #e2e8f0;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
  outline: none;
}

.selector-box select:focus {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.action-bar {
  display: flex;
  justify-content: flex-end;
}

.play-sim-btn {
  padding: 12px 28px;
  font-size: 0.95rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.spinner-inline {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Results Section styling */
.sandbox-results-grid {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 20px;
  align-items: start;
}

/* Simulation view panel styling */
.sim-panel {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  padding-bottom: 12px;
}

.panel-header h3 {
  font-size: 0.95rem;
  margin: 0;
  color: #e2e8f0;
  font-weight: 600;
}

.playback-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon-btn-ctrl {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #94a3b8;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.icon-btn-ctrl:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border-color: rgba(255, 255, 255, 0.2);
}

.frame-counter {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-family: monospace;
  margin-left: 4px;
}

.obstacle-counter {
  font-size: 0.75rem;
  color: #fca5a5;
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(248, 113, 113, 0.24);
  border-radius: 6px;
  padding: 4px 7px;
  white-space: nowrap;
}

.obstacle-counter.empty {
  color: #fbbf24;
  background: rgba(234, 179, 8, 0.12);
  border-color: rgba(234, 179, 8, 0.32);
}

.sim-view-viewport {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--glass-border);
  background: #0b0f19;
  display: flex;
  justify-content: center;
}

.road-svg {
  width: 100%;
  max-width: 340px;
  height: auto;
  display: block;
}

.obstacle-outside-road rect {
  fill: rgba(249, 115, 22, 0.72);
  stroke: #fb923c;
}

.obstacle-outside-road ellipse {
  fill: rgba(249, 115, 22, 0.07);
  stroke: rgba(251, 146, 60, 0.4);
}

.obstacle-empty-warning {
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: 16px;
  background: rgba(120, 53, 15, 0.82);
  border: 1px solid rgba(251, 191, 36, 0.32);
  border-radius: 8px;
  color: #fde68a;
  font-size: 0.75rem;
  line-height: 1.4;
  padding: 10px 12px;
}

.sandbox-debug-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 0.72rem;
  font-family: monospace;
}

.sandbox-debug-strip span {
  background: rgba(15, 23, 42, 0.66);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 6px;
  padding: 4px 7px;
}

.sandbox-warning-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #fde68a;
  font-size: 0.75rem;
}

.sandbox-warning-list div {
  background: rgba(120, 53, 15, 0.35);
  border: 1px solid rgba(251, 191, 36, 0.22);
  border-radius: 7px;
  padding: 8px 10px;
}

.telemetry-box {
  position: absolute;
  top: 12px;
  right: 12px;
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tel-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  font-size: 0.75rem;
  font-family: monospace;
}

.tel-row .label {
  color: var(--text-secondary);
}

.tel-row .value {
  color: #f1f5f9;
  font-weight: bold;
}

.tel-row .value small {
  color: var(--text-secondary);
  font-size: 0.68rem;
  margin-left: 4px;
}

.tel-row .value.steering-left {
  color: #34d399;
}

.tel-row .value.steering-right {
  color: #fb7185;
}

.scrubber-bar {
  padding: 4px 0 0 0;
}

.range-slider {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  outline: none;
  border-radius: 4px;
  cursor: pointer;
  accent-color: var(--accent-color);
}

/* Report Panel side styling */
.report-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.score-card-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.stat-box {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon-wrapper {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon-wrapper.blue-bg {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.stat-icon-wrapper.purple-bg {
  background: rgba(168, 85, 247, 0.15);
  color: #c084fc;
  border: 1px solid rgba(168, 85, 247, 0.2);
}

.stat-icon-wrapper.gray-bg {
  background: rgba(148, 163, 184, 0.15);
  color: #cbd5e1;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.stat-val {
  font-size: 1.25rem;
  font-weight: 700;
  color: #f8fafc;
  font-family: monospace;
}

/* KPI Scorecard layout */
.kpi-panel {
  padding: 20px;
}

.kpi-panel h3 {
  font-size: 0.95rem;
  margin: 0 0 20px 0;
  color: #e2e8f0;
  font-weight: 600;
}

.kpi-gauges-container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.kpi-gauge {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.circular-progress {
  width: 90px;
  height: 90px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.2);
}

.inner-value {
  width: 78px;
  height: 78px;
  background: #111827;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  font-weight: 700;
  color: #fff;
  font-family: monospace;
}

.kpi-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 6px;
}

.kpi-desc {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.4;
  padding: 0 8px;
}

/* Latency waterfall breakdown styling */
.waterfall-panel {
  padding: 20px;
}

.waterfall-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.waterfall-header h3 {
  font-size: 0.95rem;
  margin: 0;
  color: #e2e8f0;
  font-weight: 600;
}

.badge-time {
  font-size: 0.75rem;
  background: rgba(234, 179, 8, 0.15);
  color: #facc15;
  border: 1px solid rgba(234, 179, 8, 0.25);
  padding: 2px 8px;
  border-radius: 6px;
  font-family: monospace;
}

.timeline-stack-bar {
  display: flex;
  height: 12px;
  background: rgba(255,255,255,0.05);
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 16px;
  border: 1px solid rgba(255, 255, 255, 0.03);
}

.bar-segment {
  height: 100%;
  transition: width 0.1s ease-out;
}

.bar-segment.prep { background: #eab308; }
.bar-segment.per { background: #3b82f6; }
.bar-segment.dec { background: #10b981; }
.bar-segment.plan { background: #a855f7; }

.timeline-legend {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  font-size: 0.75rem;
  gap: 6px;
}

.legend-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-item .dot.yellow { background: #eab308; }
.legend-item .dot.blue { background: #3b82f6; }
.legend-item .dot.green { background: #10b981; }
.legend-item .dot.purple { background: #a855f7; }

.legend-item .name {
  color: var(--text-secondary);
}

.legend-item .ms {
  color: #fff;
  font-weight: 600;
  font-family: monospace;
}

/* Verdict and experts opinions panel */
.verdict-panel {
  padding: 20px;
}

.verdict-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.verdict-icon {
  color: #eab308;
}

.verdict-header h4 {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: #f1f5f9;
}

.verdict-content {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

.verdict-content p {
  margin: 0;
}

/* Empty states */
.empty-state-intro {
  padding: 60px 40px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.icon-sphere {
  width: 70px;
  height: 70px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.2rem;
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.empty-state-intro h3 {
  font-size: 1.1rem;
  color: #fff;
  margin: 0;
  font-weight: 500;
}

.empty-state-intro p {
  max-width: 580px;
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0;
}
</style>
