<script setup lang="ts">
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

/**
 * KPI 指标卡。未评估指标（如 P0 财务熔断数）必须走 notEvaluated，
 * 不得显示为 0 或默认通过（PRD 5.1）。
 */
defineProps<{
  label: string
  value?: string | number | null
  unit?: string
  /** 统计口径/时间窗注脚 */
  note?: string
  notEvaluated?: boolean
  /** 入场动画错峰延迟（ms） */
  delayMs?: number
}>()
</script>

<template>
  <Card
    class="animate-enter transition-shadow hover:shadow-md"
    :style="delayMs ? { animationDelay: `${delayMs}ms` } : undefined"
  >
    <CardHeader class="pb-2">
      <CardTitle class="text-sm font-normal text-muted-foreground">{{ label }}</CardTitle>
    </CardHeader>
    <CardContent>
      <Badge
        v-if="notEvaluated"
        variant="outline"
        class="border-dashed border-slate-300 bg-transparent text-slate-500"
      >
        未评估
      </Badge>
      <div v-else class="text-3xl font-semibold tabular-nums">
        {{ value ?? '—' }}
        <span v-if="unit" class="text-sm font-normal text-muted-foreground">{{ unit }}</span>
      </div>
      <p v-if="note" class="mt-1 text-xs text-muted-foreground">{{ note }}</p>
    </CardContent>
  </Card>
</template>
