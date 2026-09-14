<script setup lang="ts">
import { computed } from 'vue'
import { Badge } from '@/components/ui/badge'
import type { TaskLifecycleStatus } from '@/types/domain'

/** 任务/工作单元生命周期徽章。颜色映射=计划第 1 节，禁止自创颜色。 */
const props = defineProps<{ status: TaskLifecycleStatus }>()

const MAP: Record<TaskLifecycleStatus, { label: string; class: string }> = {
  QUEUED: { label: '排队中', class: 'border-slate-200 bg-neutral-soft text-slate-500' },
  RUNNING: { label: '运行中', class: 'border-blue-200 bg-info-soft text-info' },
  COMPLETED: { label: '已完成', class: 'border-emerald-200 bg-success-soft text-success' },
  FAILED: { label: '失败', class: 'border-red-200 bg-danger-soft text-destructive' },
  CANCELED: { label: '已取消', class: 'border-dashed border-slate-300 bg-transparent text-slate-400' },
}

const item = computed(() => MAP[props.status])
</script>

<template>
  <Badge variant="outline" :class="item.class">{{ item.label }}</Badge>
</template>
