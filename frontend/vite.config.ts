/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/judgments': {
        target: 'http://127.0.0.1:8000/api/v1',
        changeOrigin: true,
      },
      '/categories': {
        target: 'http://127.0.0.1:8000/api/v1',
        changeOrigin: true,
      },
      '/courts': {
        target: 'http://127.0.0.1:8000/api/v1',
        changeOrigin: true,
      },
      '/search': {
        target: 'http://127.0.0.1:8000/api/v1',
        changeOrigin: true,
      },
    },
  },
  build: {
    minify: 'esbuild',
    cssCodeSplit: true,
    sourcemap: false,
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'lucide-icons': ['lucide-react'],
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: false,
  },
});
