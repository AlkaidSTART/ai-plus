import { useQueries, useQuery } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import {
  getReport,
  listEvidence,
  type EvidenceResponse,
  type ListEvidenceParams,
  type Page,
} from '@/api/client'

export interface ReadyReportTarget {
  task_id: string
  item_id: string
  report_available: boolean
}

export function reportQueryKey(taskId: string, itemId: string) {
  return ['tasks', taskId, 'items', itemId, 'report'] as const
}

function evidenceQueryKey(
  taskId: string,
  itemId: string,
  params: ListEvidenceParams,
) {
  return [
    'tasks',
    taskId,
    'items',
    itemId,
    'evidence',
    params.claim_id ?? null,
    params.source_type ?? null,
    params.cursor ?? null,
    params.limit ?? null,
  ] as const
}

/**
 * 单 ASIN 报告。调用方必须把 enabled 与 item.report_available 绑定；
 * 未就绪返回 409 时不构造本地空报告。
 */
export function useReport(
  taskId: MaybeRefOrGetter<string | null | undefined>,
  itemId: MaybeRefOrGetter<string | null | undefined>,
  enabled: MaybeRefOrGetter<boolean> = true,
) {
  const task = computed(() => toValue(taskId) ?? null)
  const item = computed(() => toValue(itemId) ?? null)
  const isEnabled = computed(() => Boolean(task.value && item.value && toValue(enabled)))

  return useQuery({
    queryKey: computed(() => reportQueryKey(task.value ?? '', item.value ?? '')),
    queryFn: ({ signal }) => getReport(task.value!, item.value!, signal),
    enabled: isEnabled,
    retry: false,
  })
}

/** 聚合当前任务下所有已就绪报告，不替未就绪 item 发请求。 */
export function useReadyItemReports(
  targets: MaybeRefOrGetter<ReadyReportTarget[]>,
) {
  const readyTargets = computed(() => toValue(targets).filter((item) => item.report_available))
  return useQueries({
    queries: computed(() =>
      readyTargets.value.map((target) => ({
        queryKey: reportQueryKey(target.task_id, target.item_id),
        queryFn: ({ signal }: { signal: AbortSignal }) =>
          getReport(target.task_id, target.item_id, signal),
        retry: false,
      })),
    ),
  })
}

/** 报告引用证据；claim_id 可传 pain_point_id 或 proposal_id。 */
export function useEvidence(
  taskId: MaybeRefOrGetter<string | null | undefined>,
  itemId: MaybeRefOrGetter<string | null | undefined>,
  params: MaybeRefOrGetter<ListEvidenceParams> = {},
  enabled: MaybeRefOrGetter<boolean> = true,
) {
  const task = computed(() => toValue(taskId) ?? null)
  const item = computed(() => toValue(itemId) ?? null)
  const queryParams = computed(() => toValue(params))
  const isEnabled = computed(() => Boolean(task.value && item.value && toValue(enabled)))

  return useQuery<Page<EvidenceResponse>, Error>({
    queryKey: computed(() =>
      evidenceQueryKey(task.value ?? '', item.value ?? '', queryParams.value),
    ),
    queryFn: ({ signal }) =>
      listEvidence(task.value!, item.value!, queryParams.value, signal),
    enabled: isEnabled,
  })
}
