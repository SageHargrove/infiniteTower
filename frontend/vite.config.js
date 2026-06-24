import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// client.js calls bare paths like /base/, /heroes/, etc. with no /api
// prefix — that's correct for the packaged app (FastAPI serves the built
// frontend itself, same origin, see backend/main.py's catch-all route),
// but the Vite dev server has no such routes of its own. Proxy every
// backend router prefix straight through so `npm run dev` keeps working
// against the same client.js used by the packaged build.
const BACKEND_PREFIXES = [
  'heroes', 'gacha', 'tower', 'base', 'runs', 'equipment',
  'relics', 'profiles', 'chat', 'static', 'portrait-cache', 'arena',
]

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(
      BACKEND_PREFIXES.map((p) => [`/${p}`, { target: 'http://localhost:8000', changeOrigin: true }])
    )
  }
})
