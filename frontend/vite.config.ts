import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 3000,
    proxy: {
      // Proxy API requests to backend
      // Use Docker service name, not localhost!
      '/api': {
        target: 'http://api_service:8000',
        changeOrigin: true,
      },
    },
  },
})
