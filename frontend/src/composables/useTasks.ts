import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import {
  cancelTask,
  createTask,
  getReport,
  getTask,
  listEvidence,
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

export function useTaskReport(
  taskId: MaybeRefOrGetter<string | null | undefined>,
  itemId: MaybeRefOrGetter<string | null | undefined>,
) {
  const tId = computed(() => toValue(taskId) ?? null)
  const iId = computed(() => toValue(itemId) ?? null)
  return useQuery({
    queryKey: computed(() => [...TASKS_KEY, 'report', tId.value, iId.value]),
    queryFn: ({ signal }) => getReport(tId.value!, iId.value!, signal),
    enabled: computed(() => Boolean(tId.value && iId.value)),
    retry: false,
  })
}

export function useTaskEvidence(
  taskId: MaybeRefOrGetter<string | null | undefined>,
  itemId: MaybeRefOrGetter<string | null | undefined>,
  claimId?: MaybeRefOrGetter<string | null | undefined>,
) {
  const tId = computed(() => toValue(taskId) ?? null)
  const iId = computed(() => toValue(itemId) ?? null)
  const cId = computed(() => toValue(claimId) ?? undefined)
  return useQuery({
    queryKey: computed(() => [...TASKS_KEY, 'evidence', tId.value, iId.value, cId.value]),
    queryFn: ({ signal }) =>
      listEvidence(tId.value!, iId.value!, { claim_id: cId.value }, signal),
    enabled: computed(() => Boolean(tId.value && iId.value)),
    retry: false,
  })
}
