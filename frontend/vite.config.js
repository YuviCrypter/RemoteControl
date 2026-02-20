import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    include: ["react-grid-layout"],
  },
  server: {
    host: "0.0.0.0", // Set to 0.0.0.0 to listen on all network interfaces
    port: 5173, // Optional: You can specify a port, default is 5173
  },
});
