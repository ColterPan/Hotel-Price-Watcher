import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// In development the API runs separately (uvicorn on :8000) and Vite proxies
// /api to it, so the browser only ever talks to one origin and no CORS setup
// is needed. In Docker, nginx does the same job.
export default defineConfig({
  plugins: [react()],
  build: {
    // React + Leaflet + the date picker land around 160 kB gzipped. That is
    // fine for a single-page tool, so don't warn about it.
    chunkSizeWarningLimit: 600,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
