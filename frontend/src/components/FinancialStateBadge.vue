<script setup lang="ts">
import { computed } from 'vue'
import { Badge } from '@/components/ui/badge'
import type { FinancialState } from '@/types/domain'

/**
 * 财务裁决徽章。NOT_EVALUATED（P0/未执行/输入不足）为灰虚线，
 * 不得渲染为 0 收益或默认通过。
 */
const props = defineProps<{ state: FinancialState }>()

const MAP: Record<FinancialState, { label: string; class: string }> = {
  NOT_EVALUATED: {
    label: '未评估',
    class: 'border-dashed border-slate-300 bg-transparent text-slate-500',
  },
  PASSED: { label: '通过', class: 'border-emerald-200 bg-success-soft text-success' },
  VETOED: { label: '熔断', class: 'border-red-200 bg-danger-soft text-destructive font-medium' },
}

const item = computed(() => MAP[props.state])
</script>

<template>
  <Badge variant="outline" :class="item.class">{{ item.label }}</Badge>
</template>
