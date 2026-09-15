import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import {
  cancelTask,
  createTask,
  getTask,
  listTasks,
  retryTask,
  type TaskCreateRequest,
} from '@/api/client'

const TASKS_KEY = ['tasks'] as const

export function useTaskList(params?: { limit?: number }) {
  return useQuery({
    queryKey: [...TASKS_KEY, params],
    queryFn: () => listTasks({ limit: params?.limit ?? 20 }),
  })
}

export function useTaskDetail(taskId: MaybeRefOrGetter<string | null | undefined>) {
  const id = computed(() => toValue(taskId) ?? null)
  return useQuery({
    queryKey: computed(() => [...TASKS_KEY, 'detail', id.value]),
    queryFn: ({ signal }) => getTask(id.value!, signal),
    enabled: computed(() => Boolean(id.value)),
  })
}

export function useCreateTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { body: TaskCreateRequest; idempotencyKey: string }) =>
      createTask(vars.body, vars.idempotencyKey),
    onSuccess: () => qc.invalidateQueries({ queryKey: [...TASKS_KEY] }),
  })
}

export function useCancelTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => cancelTask(taskId),
    onSuccess: (task) => {
      qc.setQueryData([...TASKS_KEY, 'detail', task.task_id], task)
      void qc.invalidateQueries({ queryKey: [...TASKS_KEY] })
    },
  })
}

export function useRetryTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { taskId: string; itemIds: string[]; idempotencyKey: string }) =>
      retryTask(vars.taskId, vars.itemIds, vars.idempotencyKey),
    onSuccess: (result) => {
      void qc.invalidateQueries({ queryKey: [...TASKS_KEY] })
      void qc.invalidateQueries({ queryKey: [...TASKS_KEY, 'detail', result.task_id] })
    },
  })
}
