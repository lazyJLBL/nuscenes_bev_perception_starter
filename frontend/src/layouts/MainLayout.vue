<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSystemStore } from '../store/systemStore'
import {
  Activity,
  BarChart3,
  CarFront,
  Menu,
  Server,
  Settings,
  UserCircle
} from 'lucide-vue-next'

const systemStore = useSystemStore()
const route = useRoute()
const router = useRouter()

const navItems = [
  { id: 'sandbox', path: '/', name: '实验沙盒', title: 'nuScenes AD Benchmark Sandbox', icon: Activity },
  { id: 'experiments', path: '/experiments', name: '实验记录', title: '我的仿真试验与结果', icon: BarChart3 },
  { id: 'admin', path: '/admin', name: '管理员', title: '模型与仿真试验管理', icon: Settings },
  { id: 'system', path: '/system', name: '系统状态', title: '系统状态', icon: Server }
]

const currentModuleId = computed(() => {
  if (route.path.startsWith('/experiments')) return 'experiments'
  if (route.path.startsWith('/admin')) return 'admin'
  if (route.path.startsWith('/system')) return 'system'
  return 'sandbox'
})

const currentModule = computed(() => navItems.find(item => item.id === currentModuleId.value) || navItems[0])

const navigateTo = (item) => {
  router.push(item.path)
}
</script>

<template>
  <div class="app-layout">
    <aside class="sidebar glass-panel" :class="{ collapsed: systemStore.isSidebarCollapsed }">
      <div class="brand">
        <div class="brand-icon">
          <CarFront :size="28" color="currentColor" />
        </div>
        <div class="brand-text" v-if="!systemStore.isSidebarCollapsed">AD Sandbox</div>
      </div>

      <nav class="nav-menu">
        <button
          v-for="item in navItems"
          :key="item.id"
          class="nav-item"
          :class="{ active: currentModuleId === item.id }"
          :title="item.name"
          @click="navigateTo(item)"
        >
          <component :is="item.icon" :size="20" class="nav-icon" />
          <span class="nav-text" v-if="!systemStore.isSidebarCollapsed">{{ item.name }}</span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <div class="status-indicator" :class="{ collapsed: systemStore.isSidebarCollapsed }" title="System Online">
          <span class="pulse"></span>
          <span v-if="!systemStore.isSidebarCollapsed">System Online</span>
        </div>
      </div>
    </aside>

    <main class="main-content">
      <header class="top-header">
        <div class="header-left">
          <button class="icon-btn" @click="systemStore.toggleSidebar" title="折叠侧边栏">
            <Menu :size="24" />
          </button>
          <h1>{{ currentModule.title }}</h1>
        </div>
        <div class="avatar" title="当前用户">
          <UserCircle :size="32" color="var(--text-secondary)" />
        </div>
      </header>

      <div class="dashboard-container">
        <router-view :key="$route.fullPath" />
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: 280px;
  margin: 16px;
  display: flex;
  flex-direction: column;
  padding: 24px 0;
  z-index: 10;
  transition: width 0.25s ease;
}

.sidebar.collapsed {
  width: 80px;
}

.brand {
  display: flex;
  align-items: center;
  padding: 0 24px 32px;
  border-bottom: 1px solid var(--glass-border);
  margin-bottom: 24px;
  overflow: hidden;
  white-space: nowrap;
}

.sidebar.collapsed .brand {
  padding: 0 0 32px;
  justify-content: center;
}

.brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  color: var(--accent-color);
}

.sidebar.collapsed .brand-icon {
  margin-right: 0;
}

.brand-text {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.3px;
  color: var(--text-primary);
}

.nav-menu {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 16px;
}

.sidebar.collapsed .nav-menu {
  padding: 0 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 46px;
  padding: 0 16px;
  border: 1px solid transparent;
  border-radius: 8px;
  color: var(--text-secondary);
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  overflow: hidden;
  white-space: nowrap;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 0;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.nav-item.active {
  color: var(--accent-color);
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.3);
}

.nav-icon {
  flex-shrink: 0;
  opacity: 0.9;
}

.nav-text {
  font-weight: 500;
}

.sidebar-footer {
  padding: 0 24px;
}

.sidebar.collapsed .sidebar-footer {
  padding: 0 8px;
}

.status-indicator {
  display: flex;
  align-items: center;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: 8px;
  color: var(--success-color);
  background: rgba(16, 185, 129, 0.1);
  font-size: 0.85rem;
  white-space: nowrap;
  overflow: hidden;
}

.status-indicator.collapsed {
  justify-content: center;
  padding: 0;
}

.pulse {
  width: 8px;
  height: 8px;
  margin-right: 10px;
  border-radius: 50%;
  background: var(--success-color);
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
  animation: pulse 2s infinite;
  flex-shrink: 0;
}

.status-indicator.collapsed .pulse {
  margin-right: 0;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 16px 16px 16px 0;
  overflow: hidden;
}

.top-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 74px;
  padding: 0 32px;
  margin-bottom: 16px;
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  background: var(--panel-bg);
  backdrop-filter: blur(16px);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 8px;
  color: var(--text-secondary);
  background: transparent;
  cursor: pointer;
}

.icon-btn:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.1);
}

.top-header h1 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.5rem;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 1px solid var(--glass-border);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
}

.dashboard-container {
  flex: 1;
  overflow-y: auto;
  border-radius: 8px;
}
</style>
