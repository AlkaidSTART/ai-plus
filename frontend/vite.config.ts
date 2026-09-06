import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  // 部署形态：
  // - 独立部署 SPA（默认）：base '/'，根路径部署，与 Astro 落地页完全解耦
  // - GitHub Pages：构建时设 VITE_BASE=/ai-plus/（对应 https://alkaidstart.github.io/ai-plus/）
  base: process.env.VITE_BASE ?? '/',
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    // 开发环境将 /api 代理至后端（docs/api.md §1.3）；
    // 生产环境通过 VITE_API_BASE_URL 直连后端（EventSource SSE 同样直连）
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // SSE 长连接需关闭缓冲
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            proxyRes.headers['Cache-Control'] = 'no-cache'
            proxyRes.headers['X-Accel-Buffering'] = 'no'
          })
        },
      },
    },
  },
})
