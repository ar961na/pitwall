/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In dev, the browser talks to Vite (5173) and Vite forwards /api/* to FastAPI.
// Inside docker-compose the backend is reachable as http://api:8000 instead of localhost.
export default defineConfig({
  // GitHub Pages serves the project under /<repo>/, set by CI via VITE_BASE.
  base: process.env.VITE_BASE ?? '/',
  plugins: [react()],
  server: {
    host: true,
    proxy: {
      '/api': process.env.API_TARGET ?? 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
  },
})
