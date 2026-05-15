import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    define: {
      __TARGET_ENDPOINT__: JSON.stringify(env.TARGET_ENDPOINT ?? env.TARGET_URL ?? ""),
    },
    server: {
      proxy: {
        "/api": { target: "http://localhost:8000", changeOrigin: true },
        "/ws": { target: "ws://localhost:8000", changeOrigin: true, ws: true },
      },
    },
  };
});
