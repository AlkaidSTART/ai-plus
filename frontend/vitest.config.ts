import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'

// 独立于 vite.config.ts：避免 vitest 内置 vite 与项目顶层 vite 版本的类型冲突。
// 当前测试均为纯 TS 模块（utils / mock api），暂不需要 vue 插件。
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.{test,spec}.ts'],
  },
})
