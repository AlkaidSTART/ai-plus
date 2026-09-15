import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import {
  evaluateFinancial,
  evaluateTaskItemFinancial,
  getFinancialRules,
  getTaskItemFinancial,
  type FinancialEvaluateRequest,
} from '@/api/client'

const FINANCIAL_KEY = ['financial'] as const

export function useFinancialRules() {
  return useQuery({
    queryKey: [...FINANCIAL_KEY, 'rules'],
    queryFn: ({ signal }) => getFinancialRules(signal),
    staleTime: 60 * 1000,
  })
}

export function useEvaluateFinancial() {
  return useMutation({
    mutationFn: (req: FinancialEvaluateRequest) => evaluateFinancial(req),
  })
}

export function useTaskItemFinancial(
  taskId: MaybeRefOrGetter<string | null | undefined>,
  itemId: MaybeRefOrGetter<string | null | undefined>,
) {
  const tId = computed(() => toValue(taskId) ?? null)
  const iId = computed(() => toValue(itemId) ?? null)
  return useQuery({
    queryKey: computed(() => [...FINANCIAL_KEY, 'item', tId.value, iId.value]),
    queryFn: ({ signal }) => getTaskItemFinancial(tId.value!, iId.value!, signal),
    enabled: computed(() => Boolean(tId.value && iId.value)),
    retry: false,
  })
}

export function useSaveTaskItemFinancial() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: {
      taskId: string
      itemId: string
      body: FinancialEvaluateRequest
    }) => evaluateTaskItemFinancial(vars.taskId, vars.itemId, vars.body),
    onSuccess: (_, vars) => {
      void qc.invalidateQueries({
        queryKey: [...FINANCIAL_KEY, 'item', vars.taskId, vars.itemId],
      })
      void qc.invalidateQueries({
        queryKey: ['tasks', 'report', vars.taskId, vars.itemId],
      })
      void qc.invalidateQueries({
        queryKey: ['tasks'],
      })
    },
  })
}
