import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev server port must appear in the backend's CORS allow-list
// (see backend/app/main.py ALLOWED_ORIGINS). 5174 rather than Vite's default
// 5173 because another project already uses 5173 on this machine.
//
// The frontend calls the API directly rather than through a Vite proxy,
// deliberately: that way the real browser CORS path is exercised in
// development instead of being hidden behind a same-origin proxy.
export default defineConfig({
  plugins: [react()],
  server: { port: 5174, strictPort: true },
})
