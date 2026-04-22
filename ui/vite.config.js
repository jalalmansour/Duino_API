import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    port: 3000,
    host: '0.0.0.0',
    // ── CRITICAL: allow ALL hosts including Colab/Kaggle internal proxy ──────
    // Vite 5.x: must be `true` (boolean), NOT the string 'all'
    allowedHosts: true,
    strictPort: false,
    cors: true,
    headers: {
      'X-Frame-Options': 'ALLOWALL',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
      'Access-Control-Allow-Headers': '*',
    },
    hmr: false,   // disable HMR — notebooks don't support websockets reliably
  },
  build: {
    outDir: 'dist',
    assetsInlineLimit: 10240,
  },
});
