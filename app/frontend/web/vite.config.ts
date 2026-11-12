import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies /api to the FastAPI app (uvicorn app.backend.api.app:app --port 8000).
export default defineConfig(({ mode }) => {
  const apiTarget = loadEnv(mode, ".", "AUTOAUTH_").AUTOAUTH_API_URL || "http://localhost:8000";
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": { target: apiTarget, changeOrigin: true },
        "/healthz": { target: apiTarget, changeOrigin: true },
      },
    },
    build: { outDir: "dist", chunkSizeWarningLimit: 1500 },
  };
});
