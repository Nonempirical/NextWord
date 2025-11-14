import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/next_dist': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/step': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})

