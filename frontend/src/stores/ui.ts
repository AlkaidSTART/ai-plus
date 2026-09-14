import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * 跨页 UI 状态（Pinia 只存 UI 状态；任务/报告/证据等服务端数据归 TanStack Query，
 * 不在此复制）。
 */
export const useUiStore = defineStore('ui', () => {
  /** 全局「新建诊断任务」对话框开关（顶栏触发，App 级渲染） */
  const newTaskDialogOpen = ref(false)

  /** VOC 页跨页保留的过滤条状态（星级为 1-3 的字符串，与 ToggleGroup 值一致） */
  const vocLanguage = ref<string>('all')
  const vocStars = ref<string[]>(['1', '2', '3'])

  return { newTaskDialogOpen, vocLanguage, vocStars }
})
