import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { createPinia } from 'pinia'
import type { App } from 'vue'

/**
 * 全局 provider：TanStack Query（服务端数据）+ Pinia（跨页 UI 状态）。
 * 后端契约就绪前，Query 不发起真实请求（各查询 enabled: false）。
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
})

export function installProviders(app: App): void {
  app.use(createPinia())
  app.use(VueQueryPlugin, { queryClient })
}
