import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    allowedHosts: true,
    proxy: {
      // Forward /api/* → FastAPI backend on port 8004
      '/api': {
        target: 'https://their-marion-sunny-complement.trycloudflare.com',
        changeOrigin: true,
      },
    },
  },
})
