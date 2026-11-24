import path from 'node:path'
import { fileURLToPath } from 'node:url'

import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

const sourceDirectory = fileURLToPath(new URL('./src', import.meta.url))

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(sourceDirectory),
      },
    },
    server: {
      proxy: {
        '^/(auth|me|profile|profiles|verification-requests|directory|follows|artists|songs|analyzer|releases|canary|advisor|events|admin|api)(/|$)': {
          target: backendTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
