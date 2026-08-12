import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 개발 시 /api 요청을 백엔드(8000)로 프록시.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  build: {
    outDir: "dist",
  },
});
