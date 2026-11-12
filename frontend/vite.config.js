import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api/': {
        target: 'http://backend:8000',
        changeOrigin: false,
      },
      '/login/': {
        target: 'http://backend:8000',
        changeOrigin: false,
      },
      '/logout/': {
        target: 'http://backend:8000',
        changeOrigin: false,
      },
    },
  },
})
