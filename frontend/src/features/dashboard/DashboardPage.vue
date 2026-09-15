<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { Inbox, Loader2, Sparkles } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import type { NodeProgressPayload, TaskEvent } from '@/api/events.types'
import EmptyState from '@/components/EmptyState.vue'
import KpiCard from '@/components/KpiCard.vue'
import SseTimeline, { type TimelineNode } from '@/components/SseTimeline.vue'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { useUiStore } from '@/stores/ui'
import { useTaskList } from '@/composables/useTasks'
import { useTaskEvents } from '@/composables/useTaskEvents'

const ui = useUiStore()
const queryClient = useQueryClient()
const { data: taskPage, isLoading: tasksLoading } = useTaskList({ limit: 20 })
const latestTaskId = computed(() => taskPage.value?.items[0]?.task_id ?? null)
const timelineNodes = ref<TimelineNode[]>([])

function upsertTimelineNode(event: TaskEvent<NodeProgressPayload>): void {
  if (event.type !== 'task_item.node_progress') return
  const payload = event.payload
  const id = `${event.task_item_id ?? event.task_id}:${payload.node_id}`
  const node: TimelineNode = {
    id,
    name: payload.node_name,
    status: payload.status,
    durationMs: payload.duration_ms,
    note: payload.error?.message ?? payload.skip_reason ?? null,
  }
  const index = timelineNodes.value.findIndex((item) => item.id === id)
  timelineNodes.value =
    index === -1
      ? [...timelineNodes.value, node]
      : timelineNodes.value.map((item, itemIndex) => (itemIndex === index ? node : item))
}

function onTaskEvent(event: TaskEvent): void {
  if (event.type === 'task_item.node_progress') {
    upsertTimelineNode(event as TaskEvent<NodeProgressPayload>)
    return
  }
  void queryClient.invalidateQueries({ queryKey: ['tasks'] })
}

const { connect } = useTaskEvents(latestTaskId, { onEvent: onTaskEvent })

watch(latestTaskId, (taskId, previousTaskId) => {
  if (taskId === previousTaskId) return
  timelineNodes.value = []
  if (taskId) connect()
}, { immediate: true })
</script>

<template>
  <div class="mx-auto w-full max-w-[1440px] space-y-6 p-4 lg:p-6">
    <div class="flex animate-enter items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">决策大盘</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          聚合监控品类的全局体检状态；指标均为采样口径，时间窗以任务为准。
        </p>
      </div>
      <Button size="sm" @click="ui.newTaskDialogOpen = true">新建诊断任务</Button>
    </div>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiCard label="本批监控竞品" :value="null" note="提交诊断任务后统计" :delay-ms="0" />
      <KpiCard label="实际样本量" :value="null" note="为实际采集样本，非商品总体" :delay-ms="60" />
      <KpiCard label="有证据痛点数" :value="null" note="最多 5 类，不足不补齐" :delay-ms="120" />
      <KpiCard label="财务熔断" not-evaluated note="当前不执行财务否决" :delay-ms="180" />
    </div>

    <div class="grid gap-6 xl:grid-cols-3">
      <Card class="animate-enter xl:col-span-2" :style="{ animationDelay: '180ms' }">
        <CardHeader>
          <CardTitle class="text-base font-semibold">Agent 执行流</CardTitle>
          <CardDescription>
            SSE 展示真实节点与每个 ASIN 状态，区分跳过/失败/取消；断线后按游标回放。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <SseTimeline :nodes="timelineNodes" />
        </CardContent>
      </Card>

      <Card class="animate-enter" :style="{ animationDelay: '240ms' }">
        <CardHeader>
          <CardTitle class="text-base font-semibold">高潜改款项目推荐</CardTitle>
          <CardDescription>仅展示有支撑数据的结果，不足 Top 3 不补齐。</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            :icon="Sparkles"
            title="暂无推荐"
            description="完成诊断任务并获得有证据的报告后，此处展示推荐项目"
          />
        </CardContent>
      </Card>
    </div>

    <Card class="animate-enter" :style="{ animationDelay: '300ms' }">
      <CardHeader>
        <CardTitle class="text-base font-semibold">最近任务</CardTitle>
        <CardDescription>批次任务与单 ASIN 工作单元状态（含部分失败原因）。</CardDescription>
      </CardHeader>
      <CardContent>
        <div v-if="tasksLoading" class="flex items-center justify-center py-8">
          <Loader2 class="size-5 animate-spin text-muted-foreground" />
        </div>
        <EmptyState
          v-else-if="!taskPage?.items.length"
          :icon="Inbox"
          title="暂无任务"
          description="点击右上角「新建诊断任务」提交 1-10 个 Amazon US ASIN"
        />
        <div v-else class="divide-y">
          <div
            v-for="task in taskPage.items"
            :key="task.task_id"
            class="flex items-center justify-between py-3 text-sm"
          >
            <div class="space-y-0.5">
              <p class="font-medium font-mono text-xs">{{ task.task_id }}</p>
              <p class="text-muted-foreground text-xs">
                {{ task.total_items }} 个 ASIN · {{ task.window.preset }} · {{ new Date(task.created_at).toLocaleString() }}
              </p>
            </div>
            <span
              class="rounded-full px-2 py-0.5 text-xs font-medium"
              :class="{
                'bg-yellow-100 text-yellow-800': task.status === 'QUEUED',
                'bg-blue-100 text-blue-800': task.status === 'RUNNING',
                'bg-green-100 text-green-800': task.status === 'COMPLETED',
                'bg-red-100 text-red-800': task.status === 'FAILED',
                'bg-gray-100 text-gray-800': task.status === 'CANCELED',
              }"
            >
              {{ task.status }}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
