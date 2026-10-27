import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig(({ mode }) => ({
  define: { __DEMO_ONLY__: JSON.stringify(mode === "demo") },
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
}));
