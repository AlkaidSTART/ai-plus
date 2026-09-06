// @ts-check
import { defineConfig } from 'astro/config'
import vue from '@astrojs/vue'

// https://astro.build/config
export default defineConfig({
  integrations: [vue()],
  // 独立部署：落地页与 Vue SPA 完全解耦，不再代理 /app 前缀
  // 「进入控制台」CTA 通过 PUBLIC_SPA_URL 指向 SPA 独立地址（见 src/pages/index.astro）
})
