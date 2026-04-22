import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    port: 3000,
    host: '0.0.0.0',
    cors: true,
    headers: {
      'X-Frame-Options': 'ALLOWALL',
    },
  },
  build: {
    outDir: 'dist',
    assetsInlineLimit: 10240,
  },
});
