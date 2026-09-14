<script setup lang="ts">
import { Workflow } from '@lucide/vue'
import EmptyState from '@/components/EmptyState.vue'
import type { NodeStatus } from '@/types/domain'

/**
 * SSE 节点时间线：展示后端推送的真实节点状态（含跳过/无数据/失败/取消），
 * 不伪造固定步骤动画（PRD P0-04）。
 */
export interface TimelineNode {
  id: string
  name: string
  status: NodeStatus
  durationMs?: number | null
  note?: string | null
}

defineProps<{ nodes: TimelineNode[] }>()

const DOT: Record<NodeStatus, string> = {
  PENDING: 'bg-slate-300',
  RUNNING: 'bg-info animate-pulse',
  SUCCESS: 'bg-success',
  SKIPPED: 'bg-slate-300',
  FAILED: 'bg-destructive',
  CANCELED: 'bg-slate-400',
  NO_DATA: 'bg-warning',
}

const LABEL: Record<NodeStatus, string> = {
  PENDING: '等待',
  RUNNING: '运行中',
  SUCCESS: '完成',
  SKIPPED: '跳过',
  FAILED: '失败',
  CANCELED: '已取消',
  NO_DATA: '无数据',
}

function formatDuration(ms: number | null | undefined): string | null {
  if (ms == null) return null
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
}
</script>

<template>
  <EmptyState
    v-if="nodes.length === 0"
    :icon="Workflow"
    title="暂无执行节点"
    description="任务运行后，此处按后端推送的真实节点事件展示进度"
  />
  <ol v-else class="relative space-y-4 border-l pl-6">
    <li v-for="node in nodes" :key="node.id" class="relative">
      <span
        class="absolute -left-[31px] top-1 size-2.5 rounded-full ring-4 ring-background"
        :class="DOT[node.status]"
      />
      <div class="flex items-center gap-2">
        <span class="text-sm font-medium">{{ node.name }}</span>
        <span class="text-xs text-muted-foreground">{{ LABEL[node.status] }}</span>
        <span v-if="formatDuration(node.durationMs)" class="text-xs tabular-nums text-muted-foreground">
          {{ formatDuration(node.durationMs) }}
        </span>
      </div>
      <p v-if="node.note" class="mt-0.5 text-xs text-muted-foreground">{{ node.note }}</p>
    </li>
  </ol>
</template>
