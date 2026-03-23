import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  ssr: {
    // Leaflet is browser-only — never try to SSR it
    noExternal: ['leaflet'],
  },
});
