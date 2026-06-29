import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'
import ModuleView from '../views/ModuleView.vue'
import SandboxView from '../views/SandboxView.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'SandboxView',
        component: SandboxView
      },
      {
        path: 'sandbox',
        redirect: '/'
      },
      {
        path: 'experiments',
        name: 'ExperimentsView',
        component: () => import('../views/ExperimentsView.vue')
      },
      {
        path: 'system',
        name: 'SystemStatusView',
        component: () => import('../views/SystemStatusView.vue')
      },
      {
        path: 'admin',
        name: 'AdminView',
        component: () => import('../views/AdminView.vue')
      },
      {
        path: 'dev/modules/:moduleId?',
        name: 'ModuleView',
        component: ModuleView,
        props: route => ({ moduleId: route.params.moduleId || 'preprocessing' })
      },
      {
        path: 'preprocessing',
        redirect: '/'
      },
      {
        path: 'perception',
        redirect: '/'
      },
      {
        path: 'decision',
        redirect: '/'
      },
      {
        path: 'planning',
        redirect: '/'
      },
      {
        path: ':pathMatch(.*)*',
        redirect: '/'
      },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
