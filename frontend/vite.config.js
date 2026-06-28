import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8010',
        changeOrigin: true,
      },
      '/static': {
        target: process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8010',
        changeOrigin: true,
      },
    },
  },
})
