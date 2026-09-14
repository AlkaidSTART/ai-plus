import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { createTask, listTasks, type TaskCreateRequest } from '@/api/client'

const TASKS_KEY = ['tasks'] as const

export function useTaskList(params?: { limit?: number }) {
  return useQuery({
    queryKey: [...TASKS_KEY, params],
    queryFn: () => listTasks({ limit: params?.limit ?? 20 }),
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
