<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSystemStore } from '../store/systemStore'
import { 
  CarFront, 
  Menu, 
  UserCircle,
  Activity,
  BarChart3,
  Server
} from 'lucide-vue-next'

const systemStore = useSystemStore()
const route = useRoute()
const router = useRouter()

const navItems = [
  { id: 'sandbox', path: '/', name: '实验沙盒', title: 'nuScenes AD Benchmark Sandbox', icon: Activity },
  { id: 'experiments', path: '/experiments', name: '实验记录', title: '实验记录与对比', icon: BarChart3 },
  { id: 'system', path: '/system', name: '系统状态', title: '系统状态', icon: Server }
]

const currentModuleId = computed(() => {
  if (route.path.startsWith('/experiments')) return 'experiments'
  if (route.path.startsWith('/system')) return 'system'
  return 'sandbox'
})
const currentModule = computed(() => navItems.find(m => m.id === currentModuleId.value) || navItems[0])

const navigateTo = (item) => {
  router.push(item.path)
}
</script>

<template>
  <div class="app-layout">
    <!-- Sidebar -->
    <aside 
      class="sidebar glass-panel"
      :class="{ 'collapsed': systemStore.isSidebarCollapsed }"
    >
      <div class="brand">
        <div class="brand-icon">
          <CarFront :size="28" color="currentColor" />
        </div>
        <div class="brand-text" v-if="!systemStore.isSidebarCollapsed">AD Sandbox</div>
      </div>
      
      <nav class="nav-menu">
        <a 
          v-for="mod in navItems" 
          :key="mod.id"
          class="nav-item"
          :class="{ active: currentModuleId === mod.id }"
          @click="navigateTo(mod)"
          :title="mod.name"
        >
          <component :is="mod.icon" :size="20" class="nav-icon" />
          <span class="nav-text" v-if="!systemStore.isSidebarCollapsed">{{ mod.name }}</span>
        </a>
      </nav>
      
      <div class="sidebar-footer">
        <div class="status-indicator" :class="{ 'collapsed': systemStore.isSidebarCollapsed }" title="System Online">
          <span class="pulse"></span>
          <span v-if="!systemStore.isSidebarCollapsed">System Online</span>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <header class="top-header">
        <div class="header-left">
          <button class="icon-btn" @click="systemStore.toggleSidebar">
            <Menu :size="24" />
          </button>
          <h1>{{ currentModule.title }}</h1>
        </div>
        <div class="user-profile">
          <div class="avatar">
            <UserCircle :size="32" color="var(--text-secondary)" />
          </div>
        </div>
      </header>
      
      <div class="dashboard-container">
        <!-- Dashboard Component changes via Router -->
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

/* Sidebar Styling */
.sidebar {
  width: 280px;
  margin: 16px;
  display: flex;
  flex-direction: column;
  padding: 24px 0;
  z-index: 10;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
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
  padding: 0 0 32px 0;
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
  letter-spacing: 0.5px;
  background: linear-gradient(90deg, #fff, #94a3b8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
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
  padding: 12px 16px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: var(--text-secondary);
  overflow: hidden;
  white-space: nowrap;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 12px 0;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.nav-item.active {
  background: rgba(59, 130, 246, 0.15);
  color: var(--accent-color);
  border: 1px solid rgba(59, 130, 246, 0.3);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.nav-icon {
  margin-right: 12px;
  opacity: 0.8;
  flex-shrink: 0;
}

.sidebar.collapsed .nav-icon {
  margin-right: 0;
}

.nav-item.active .nav-icon {
  opacity: 1;
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
  font-size: 0.85rem;
  color: var(--success-color);
  background: rgba(16, 185, 129, 0.1);
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgba(16, 185, 129, 0.2);
  white-space: nowrap;
  overflow: hidden;
}

.status-indicator.collapsed {
  justify-content: center;
  padding: 8px 0;
}

.pulse {
  width: 8px;
  height: 8px;
  background: var(--success-color);
  border-radius: 50%;
  margin-right: 10px;
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

/* Main Content Styling */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px 16px 16px 0;
  overflow: hidden;
}

.top-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
  background: var(--panel-bg);
  backdrop-filter: blur(16px);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  margin-bottom: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.icon-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  border-radius: 8px;
  transition: all 0.2s;
}

.icon-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.top-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

.avatar {
  width: 40px;
  height: 40px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--glass-border);
  cursor: pointer;
}

.dashboard-container {
  flex: 1;
  overflow-y: auto;
  border-radius: 16px;
}
</style>
