<script setup lang="ts">
import { computed } from 'vue'
import type { TaskStatus } from '@/types'

const props = defineProps<{ status: TaskStatus }>()

const CLASS: Record<TaskStatus, string> = {
  PENDING: 'bg-slate-100 text-slate-600 ring-slate-200',
  RUNNING: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
  COMPLETED: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  FAILED: 'bg-rose-50 text-rose-700 ring-rose-200',
  CANCELED: 'bg-slate-100 text-slate-500 ring-slate-200',
}
const LABEL: Record<TaskStatus, string> = {
  PENDING: '待执行',
  RUNNING: '执行中',
  COMPLETED: '已完成',
  FAILED: '失败',
  CANCELED: '已取消',
}

const cls = computed(() => CLASS[props.status])
</script>

<template>
  <span class="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset" :class="cls">
    <span v-if="status === 'RUNNING'" class="size-1.5 animate-pulse rounded-full bg-indigo-500" />
    {{ LABEL[status] }}
  </span>
</template>
