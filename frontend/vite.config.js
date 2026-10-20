import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import fs from 'fs'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const DEBUG = env.VITE_DEBUG === 'true'

  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: '0.0.0.0',
      port: 5173,
      ...(DEBUG && {
        https: {
          key: fs.readFileSync('../certs/key.pem'),
          cert: fs.readFileSync('../certs/cert.pem'),
        },
      }),
    },
  }
})