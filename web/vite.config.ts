import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev proxy: /api -> FastAPI backend on :8000. In prod, VITE_API_BASE is set
// (Amplify env var) to the App Runner URL.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
