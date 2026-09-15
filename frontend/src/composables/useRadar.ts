import { useQuery } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import {
  getBsrTrends,
  getCrossPlatform,
  type ListBsrTrendsParams,
  type ListCrossPlatformParams,
} from '@/api/client'

const RADAR_KEY = ['radar'] as const

export function useBsrTrends(params?: MaybeRefOrGetter<ListBsrTrendsParams | undefined>) {
  const resolvedParams = computed(() => toValue(params) ?? {})
  return useQuery({
    queryKey: computed(() => [...RADAR_KEY, 'bsr-trends', resolvedParams.value]),
    queryFn: ({ signal }) => getBsrTrends(resolvedParams.value, signal),
    staleTime: 30_000,
  })
}

export function useCrossPlatform(params?: MaybeRefOrGetter<ListCrossPlatformParams | undefined>) {
  const resolvedParams = computed(() => toValue(params) ?? {})
  return useQuery({
    queryKey: computed(() => [...RADAR_KEY, 'cross-platform', resolvedParams.value]),
    queryFn: ({ signal }) => getCrossPlatform(resolvedParams.value, signal),
    staleTime: 30_000,
  })
}
