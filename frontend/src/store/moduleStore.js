import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useModuleStore = defineStore('module', () => {
  const configs = ref({})
  const isLoading = ref(false)
  const error = ref(null)

  const fetchConfigs = async () => {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.get('/modules')
      configs.value = response.data
    } catch (err) {
      console.error('Failed to fetch module configs:', err)
      error.value = '无法连接到后端服务器'
      
      // Fallback for visual testing when backend is down
      configs.value = {
        perception: {
          title: "后端未连接 (Backend Offline)",
          desc: "请运行 python -m backend.main 启动服务",
          available: false,
          subModules: [],
          modelsBySub: {}
        }
      }
    } finally {
      isLoading.value = false
    }
  }

  return {
    configs,
    isLoading,
    error,
    fetchConfigs
  }
})
