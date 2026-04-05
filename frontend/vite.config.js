import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  publicDir: 'static',
  server: {
    host: true,
    allowedHosts: ['.onrender.com']
  }
});