import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Task, TaskStep } from '@/types'
import { listTasks, getTask, createTask as apiCreateTask, type CreateTaskRequest } from '@/api'
import { subscribeTaskEvents } from '@/api/client'
import { STEP_LABEL } from '@/utils/severity'

/** 当前查看的默认任务（mock 主任务） */
export const DEFAULT_TASK_ID = 'tsk_9f2c81a4'

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref<Task[]>([])
  const currentTask = ref<Task | null>(null)
  const loading = ref(false)

  /** 任务流面板：步骤推进记录 */
  const flowSteps = ref<{ step: TaskStep; label: string; progress: number; message: string; time: string }[]>([])
  const flowActive = ref(false)

  async function fetchTasks(params?: { status?: string }) {
    loading.value = true
    try {
      const res = await listTasks(params)
      tasks.value = res.items
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(taskId: string) {
    currentTask.value = await getTask(taskId)
    return currentTask.value
  }

  /**
   * 创建任务并订阅 SSE 事件流。
   * 返回创建出的任务 id（mock 模式下播放完整 7 步流程）。
   */
  async function createAndWatchTask(req: CreateTaskRequest): Promise<string[]> {
    const res = await apiCreateTask(req)
    const ids = res.tasks.map((t) => t.task_id)
    await fetchTasks()
    // 播放第一条任务的流程动画（mock）
    ids.forEach((id, i) => {
      setTimeout(() => startFlow(id), i * 200)
    })
    return ids
  }

  let cancelFlow: (() => void) | null = null

  function startFlow(taskId: string) {
    // 取消上一次订阅，避免并行 SSE / mock 定时器累积
    cancelFlow?.()
    cancelFlow = null

    flowSteps.value = []
    flowActive.value = true
    cancelFlow = subscribeTaskEvents(
      taskId,
      (step, progress, message) => {
        flowSteps.value.push({
          step: step as TaskStep,
          label: STEP_LABEL[step] ?? step,
          progress,
          message,
          time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
        })
      },
      () => {
        cancelFlow = null
        flowActive.value = false
        fetchTasks()
        fetchTask(taskId).catch(() => {})
      },
    )
  }

  return { tasks, currentTask, loading, flowSteps, flowActive, fetchTasks, fetchTask, createAndWatchTask, startFlow }
})
