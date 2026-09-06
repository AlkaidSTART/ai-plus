// @ts-check
import { defineConfig } from 'astro/config'
import vue from '@astrojs/vue'

// https://astro.build/config
export default defineConfig({
  integrations: [vue()],
  // 开发环境将 /app 前缀代理到 Vue SPA（5173），实现「落地页 → 控制台」同源联合
  // 部署时在 Nginx 加一条 location /app { proxy_pass http://<spa>:<port>; } 即可复用
  vite: {
    server: {
      proxy: {
        '/app': {
          target: 'http://localhost:5173',
          changeOrigin: true,
        },
      },
    },
  },
})
