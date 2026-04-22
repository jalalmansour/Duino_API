import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    port: 3000,
    host: '0.0.0.0',
    // ── CRITICAL: allow Colab proxy hosts (*.colab.dev, *.codatalab-user-runtimes.internal)
    // Without this, Vite blocks all requests from the Colab proxy with "Blocked request"
    allowedHosts: 'all',
    cors: true,
    headers: {
      'X-Frame-Options': 'ALLOWALL',
      'Access-Control-Allow-Origin': '*',
    },
    hmr: {
      // Disable HMR websocket in notebook environments (no ws support)
      protocol: 'ws',
      clientPort: 443,
    },
  },
  build: {
    outDir: 'dist',
    assetsInlineLimit: 10240,
  },
});
