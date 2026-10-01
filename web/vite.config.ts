import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the API is proxied under /api, so the browser sees one origin and
// certificate links (PUBLIC_BASE_URL) can point at the web client.
const api = process.env.SCRAPLINK_API ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": { target: api, rewrite: (path) => path.replace(/^\/api/, "") },
    },
  },
});
