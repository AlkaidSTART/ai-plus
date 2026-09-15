<script setup lang="ts">
import {
  ArrowDownRight,
  ArrowUpRight,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Globe,
  Inbox,
  Layers,
  Loader2,
  Plus,
  RefreshCw,
  RotateCw,
  Search,
  TrendingUp,
  Trophy,
} from '@lucide/vue'
import { computed, ref } from 'vue'
import { toast } from 'vue-sonner'
import StatusBadge from '@/components/StatusBadge.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import VChart from '@/components/VChart.vue'
import { useBsrTrends, useCrossPlatform } from '@/composables/useRadar'
import { useRetryTask, useTaskList } from '@/composables/useTasks'
import { CHART_COLORS } from '@/lib/chart'
import { useUiStore } from '@/stores/ui'
import RadarBatchDetails from './RadarBatchDetails.vue'

const ui = useUiStore()

// --- TAB 1: 任务批次状态与明细 ---
const batchStatusFilter = ref<string>('ALL')
const {
  data: taskPage,
  isLoading: tasksLoading,
  refetch: refetchTasks,
} = useTaskList({ limit: 50 })

const expandedTaskIds = ref<Set<string>>(new Set())

function toggleExpand(taskId: string) {
  if (expandedTaskIds.value.has(taskId)) {
    expandedTaskIds.value.delete(taskId)
  } else {
    expandedTaskIds.value.add(taskId)
  }
}

const filteredTasks = computed(() => {
  const items = taskPage.value?.items ?? []
  if (batchStatusFilter.value === 'ALL') return items
  return items.filter((t) => t.status === batchStatusFilter.value)
})

const batchSummary = computed(() => {
  const items = taskPage.value?.items ?? []
  const total = items.length
  const queued = items.filter((t) => t.status === 'QUEUED').length
  const running = items.filter((t) => t.status === 'RUNNING').length
  const completed = items.filter((t) => t.status === 'COMPLETED').length
  const failed = items.filter((t) => t.status === 'FAILED' || t.failed_items > 0).length
  return { total, queued, running, completed, failed }
})

const retryMutation = useRetryTask()

async function handleRetryBatch(taskId: string) {
  try {
    const key = `retry-batch-${taskId}-${Date.now()}`
    await retryMutation.mutateAsync({
      taskId,
      itemIds: [],
      idempotencyKey: key,
    })
    toast.success(`任务批次 ${taskId} 重试已提交`)
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '重试提交失败'
    toast.error(msg)
  }
}

// --- TAB 2: BSR 走势监控 ---
const bsrDays = ref<number>(30)
const selectedBsrAsin = ref<string>('ALL')

const bsrQueryParams = computed(() => ({
  days: bsrDays.value,
  asin: selectedBsrAsin.value === 'ALL' ? undefined : selectedBsrAsin.value,
}))

const {
  data: bsrData,
  isLoading: bsrLoading,
  refetch: refetchBsr,
} = useBsrTrends(bsrQueryParams)

const bsrCompetitors = computed(() => bsrData.value?.items ?? [])

const activeBsrItem = computed(() => {
  if (!bsrCompetitors.value.length) return null
  if (selectedBsrAsin.value !== 'ALL') {
    return bsrCompetitors.value.find((c) => c.asin === selectedBsrAsin.value) ?? bsrCompetitors.value[0]
  }
  return bsrCompetitors.value[0]
})

const bsrChartOption = computed(() => {
  const items = bsrCompetitors.value
  if (!items.length) return null

  // If single ASIN selected or single competitor in focus:
  if (selectedBsrAsin.value !== 'ALL' || items.length === 1) {
    const item = activeBsrItem.value
    if (!item || !item.history.length) return null

    const dates = item.history.map((h) => {
      const d = new Date(h.timestamp)
      return `${d.getMonth() + 1}/${d.getDate()}`
    })
    const bsrVals = item.history.map((h) => h.bsr)
    const subBsrVals = item.history.map((h) => h.sub_bsr ?? 0)
    const priceVals = item.history.map((h) => h.price)

    const minBsr = Math.min(...bsrVals)
    const maxBsr = Math.max(...bsrVals)
    const minPrice = Math.min(...priceVals)
    const maxPrice = Math.max(...priceVals)

    return {
      tooltip: {
        trigger: 'axis',
        formatter: (params: any[]) => {
          if (!params || !params.length) return ''
          const idx = params[0].dataIndex
          const point = item.history[idx]
          const dateStr = new Date(point.timestamp).toLocaleDateString()
          return `
            <div style="font-size:12px; line-height:1.5;">
              <div style="font-weight:600; margin-bottom:4px;">${dateStr}</div>
              <div style="color:#2563EB;">主类目 BSR: <b>#${point.bsr}</b></div>
              <div style="color:#059669;">子类目 BSR: <b>#${point.sub_bsr ?? '—'}</b></div>
              <div style="color:#D97706;">标价: <b>$${point.price.toFixed(2)}</b></div>
              <div style="color:#64748B;">Buy Box 状态: <b>${point.buy_box ? '持占中' : '未赢得'}</b></div>
            </div>
          `
        },
      },
      legend: {
        top: 0,
        right: 16,
        data: ['主类目 BSR 排名', '子类目 BSR 排名', '标价 ($)'],
      },
      grid: {
        top: 36,
        left: 48,
        right: 48,
        bottom: 24,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#CBD5E1' } },
        axisLabel: { color: '#64748B', fontSize: 11 },
      },
      yAxis: [
        {
          type: 'value',
          name: 'BSR 排名 (数值越小越优)',
          inverse: true,
          min: Math.max(1, minBsr - 5),
          max: maxBsr + 8,
          axisLabel: {
            formatter: '#{value}',
            color: '#64748B',
            fontSize: 11,
          },
          splitLine: { lineStyle: { color: '#F1F5F9', type: 'dashed' } },
        },
        {
          type: 'value',
          name: '售价 ($)',
          min: Math.max(0, Math.floor(minPrice - 2)),
          max: Math.ceil(maxPrice + 2),
          axisLabel: {
            formatter: '${value}',
            color: '#64748B',
            fontSize: 11,
          },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '主类目 BSR 排名',
          type: 'line',
          yAxisIndex: 0,
          smooth: true,
          data: bsrVals,
          itemStyle: { color: CHART_COLORS[0] },
          areaStyle: { opacity: 0.12, color: CHART_COLORS[0] },
          lineStyle: { width: 2.5 },
        },
        {
          name: '子类目 BSR 排名',
          type: 'line',
          yAxisIndex: 0,
          smooth: true,
          data: subBsrVals,
          itemStyle: { color: CHART_COLORS[1] },
          lineStyle: { width: 2, type: 'dashed' },
        },
        {
          name: '标价 ($)',
          type: 'line',
          yAxisIndex: 1,
          step: 'end',
          data: priceVals,
          itemStyle: { color: CHART_COLORS[2] },
          lineStyle: { width: 1.8 },
        },
      ],
    }
  }

  // Multi-competitor BSR comparison view
  const dates = (items[0]?.history ?? []).map((h) => {
    const d = new Date(h.timestamp)
    return `${d.getMonth() + 1}/${d.getDate()}`
  })

  return {
    tooltip: {
      trigger: 'axis',
    },
    legend: {
      top: 0,
      right: 16,
      data: items.map((c) => c.asin),
    },
    grid: {
      top: 36,
      left: 48,
      right: 24,
      bottom: 24,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLabel: { color: '#64748B', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: 'BSR 排名',
      inverse: true,
      axisLabel: { formatter: '#{value}', color: '#64748B', fontSize: 11 },
      splitLine: { lineStyle: { color: '#F1F5F9', type: 'dashed' } },
    },
    series: items.map((c, i) => ({
      name: c.asin,
      type: 'line',
      smooth: true,
      data: c.history.map((h) => h.bsr),
      itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
      lineStyle: { width: 2 },
    })),
  }
})

// --- TAB 3: 跨平台对齐矩阵 ---
const platformFilter = ref<string>('ALL')
const matchStatusFilter = ref<string>('ALL')
const crossSearchQuery = ref<string>('')

const crossQueryParams = computed(() => ({
  platform: platformFilter.value === 'ALL' ? undefined : platformFilter.value,
  status: matchStatusFilter.value === 'ALL' ? undefined : matchStatusFilter.value,
}))

const {
  data: crossData,
  isLoading: crossLoading,
  refetch: refetchCross,
} = useCrossPlatform(crossQueryParams)

const crossMetrics = computed(() => crossData.value?.metrics ?? {
  total_skus: 0,
  avg_match_score: 0,
  max_spread: 0,
  arbitrage_opportunities: 0,
})

const filteredCrossItems = computed(() => {
  const items = crossData.value?.items ?? []
  if (!crossSearchQuery.value.trim()) return items
  const q = crossSearchQuery.value.trim().toLowerCase()
  return items.filter(
    (x) =>
      x.target_asin.toLowerCase().includes(q) ||
      x.target_title.toLowerCase().includes(q) ||
      x.platform_sku.toLowerCase().includes(q) ||
      x.platform_title.toLowerCase().includes(q),
  )
})
</script>

<template>
  <div class="mx-auto w-full max-w-[1440px] space-y-6 p-4 lg:p-6">
    <!-- Header -->
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div class="animate-enter">
        <h1 class="text-2xl font-semibold tracking-tight">竞品雷达</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          批次任务多 ASIN 独立状态穿透、BSR 时序排名异动追踪与跨平台货源套利矩阵。
        </p>
      </div>

      <div class="flex items-center gap-2">
        <Button size="sm" class="gap-1.5 shadow-sm" @click="ui.newTaskDialogOpen = true">
          <Plus class="h-4 w-4" />
          新建批次任务
        </Button>
      </div>
    </div>

    <!-- Main Navigation Tabs -->
    <Tabs default-value="batches" class="animate-enter space-y-6" :style="{ animationDelay: '60ms' }">
      <TabsList class="grid w-full grid-cols-3 max-w-md">
        <TabsTrigger value="batches" class="gap-1.5">
          <Layers class="h-4 w-4" />
          任务批次
        </TabsTrigger>
        <TabsTrigger value="bsr" class="gap-1.5">
          <TrendingUp class="h-4 w-4" />
          BSR 走势
        </TabsTrigger>
        <TabsTrigger value="cross" class="gap-1.5">
          <Globe class="h-4 w-4" />
          跨平台矩阵
        </TabsTrigger>
      </TabsList>

      <!-- ========================================== -->
      <!-- TAB 1: 任务批次 (Batches)                  -->
      <!-- ========================================== -->
      <TabsContent value="batches" class="space-y-4 animate-in fade-in duration-200">
        <!-- Queue Stats Pill Bar -->
        <div class="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card p-3 shadow-xs">
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-xs font-medium text-muted-foreground">批次状态：</span>
            <Button
              size="sm"
              :variant="batchStatusFilter === 'ALL' ? 'default' : 'outline'"
              class="h-7 text-xs"
              @click="batchStatusFilter = 'ALL'"
            >
              全部 ({{ batchSummary.total }})
            </Button>
            <Button
              size="sm"
              :variant="batchStatusFilter === 'QUEUED' ? 'default' : 'outline'"
              class="h-7 text-xs"
              @click="batchStatusFilter = 'QUEUED'"
            >
              排队中 ({{ batchSummary.queued }})
            </Button>
            <Button
              size="sm"
              :variant="batchStatusFilter === 'RUNNING' ? 'default' : 'outline'"
              class="h-7 text-xs"
              @click="batchStatusFilter = 'RUNNING'"
            >
              执行中 ({{ batchSummary.running }})
            </Button>
            <Button
              size="sm"
              :variant="batchStatusFilter === 'COMPLETED' ? 'default' : 'outline'"
              class="h-7 text-xs"
              @click="batchStatusFilter = 'COMPLETED'"
            >
              已完成 ({{ batchSummary.completed }})
            </Button>
            <Button
              size="sm"
              :variant="batchStatusFilter === 'FAILED' ? 'destructive' : 'outline'"
              class="h-7 text-xs"
              @click="batchStatusFilter = 'FAILED'"
            >
              异常/失败 ({{ batchSummary.failed }})
            </Button>
          </div>

          <Button
            size="sm"
            variant="ghost"
            class="h-7 gap-1 text-xs text-muted-foreground hover:text-foreground"
            :disabled="tasksLoading"
            @click="() => refetchTasks()"
          >
            <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': tasksLoading }" />
            刷新批次
          </Button>
        </div>

        <!-- Batch Task List -->
        <Card>
          <CardHeader class="pb-3">
            <CardTitle class="text-base font-semibold">诊断任务批次列表</CardTitle>
            <CardDescription>
              每批次包含 1-10 个 ASIN；点击展开即可查看批次内单个 ASIN 的独立执行节点与失败阻断原因。
            </CardDescription>
          </CardHeader>
          <CardContent class="p-0">
            <div v-if="tasksLoading" class="flex items-center justify-center py-16 text-sm text-muted-foreground">
              <Loader2 class="mr-2 h-5 w-5 animate-spin" />
              正在同步任务批次状态...
            </div>

            <div v-else-if="!filteredTasks.length" class="p-8">
              <EmptyState
                :icon="Inbox"
                title="暂无匹配的任务批次"
                description="点击上方「新建批次任务」提交目标商品 ASIN 诊断"
              />
            </div>

            <div v-else class="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow class="bg-muted/30">
                    <TableHead class="w-10" />
                    <TableHead class="w-48">任务批次 ID</TableHead>
                    <TableHead class="w-32">市场 · 窗口</TableHead>
                    <TableHead class="w-24">ASIN 规模</TableHead>
                    <TableHead class="w-28">批次主状态</TableHead>
                    <TableHead class="w-44">子项完成进展</TableHead>
                    <TableHead class="w-40">创建时间</TableHead>
                    <TableHead class="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <template v-for="task in filteredTasks" :key="task.task_id">
                    <!-- Main Batch Row -->
                    <TableRow
                      class="cursor-pointer transition-colors hover:bg-muted/40"
                      :class="{ 'bg-muted/20': expandedTaskIds.has(task.task_id) }"
                      @click="toggleExpand(task.task_id)"
                    >
                      <!-- Expand Toggle -->
                      <TableCell class="p-2 text-center" @click.stop="toggleExpand(task.task_id)">
                        <Button variant="ghost" size="icon" class="h-6 w-6">
                          <ChevronDown
                            v-if="expandedTaskIds.has(task.task_id)"
                            class="h-4 w-4 text-muted-foreground transition-transform"
                          />
                          <ChevronRight
                            v-else
                            class="h-4 w-4 text-muted-foreground transition-transform"
                          />
                        </Button>
                      </TableCell>

                      <!-- Task ID -->
                      <TableCell class="font-mono text-xs font-medium">
                        {{ task.task_id }}
                      </TableCell>

                      <!-- Marketplace / Window -->
                      <TableCell class="text-xs text-muted-foreground">
                        <span class="font-medium text-foreground">{{ task.marketplace }}</span>
                        <span class="mx-1">·</span>
                        <span>{{ task.window?.preset ?? '6m' }}</span>
                      </TableCell>

                      <!-- Total items -->
                      <TableCell class="text-xs">
                        <span class="font-semibold">{{ task.total_items }}</span>
                        <span class="text-muted-foreground"> 个</span>
                      </TableCell>

                      <!-- Status -->
                      <TableCell>
                        <StatusBadge :status="task.status as any" />
                      </TableCell>

                      <!-- Completion breakdown -->
                      <TableCell class="text-xs">
                        <div class="flex items-center gap-1.5">
                          <span class="font-medium text-foreground">{{ task.completed_items }} / {{ task.total_items }}</span>
                          <span class="text-muted-foreground">完成</span>
                          <Badge
                            v-if="task.failed_items > 0"
                            variant="destructive"
                            class="ml-1 text-[10px] px-1.5 py-0"
                          >
                            {{ task.failed_items }} 失败
                          </Badge>
                        </div>
                      </TableCell>

                      <!-- Created At -->
                      <TableCell class="text-xs text-muted-foreground">
                        {{ new Date(task.created_at).toLocaleString() }}
                      </TableCell>

                      <!-- Actions -->
                      <TableCell class="text-right" @click.stop>
                        <div class="flex items-center justify-end gap-1.5">
                          <Button
                            v-if="task.failed_items > 0"
                            size="sm"
                            variant="outline"
                            class="h-7 px-2 text-xs"
                            :disabled="retryMutation.isPending.value"
                            @click="handleRetryBatch(task.task_id)"
                          >
                            <RotateCw
                              class="mr-1 h-3 w-3"
                              :class="{ 'animate-spin': retryMutation.isPending.value }"
                            />
                            重试失败项
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            class="h-7 px-2 text-xs text-primary"
                            @click="toggleExpand(task.task_id)"
                          >
                            {{ expandedTaskIds.has(task.task_id) ? '收起明细' : '展开明细' }}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>

                    <!-- Expanded Detail Row: 单 ASIN 状态与失败阻断原因 -->
                    <TableRow v-if="expandedTaskIds.has(task.task_id)" class="bg-muted/10 hover:bg-muted/10">
                      <TableCell colspan="8" class="p-3 pl-8">
                        <RadarBatchDetails :task-id="task.task_id" />
                      </TableCell>
                    </TableRow>
                  </template>
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      <!-- ========================================== -->
      <!-- TAB 2: BSR 走势 (BSR Trends)               -->
      <!-- ========================================== -->
      <TabsContent value="bsr" class="space-y-6 animate-in fade-in duration-200">
        <!-- Control Bar -->
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between rounded-lg border bg-card p-3 shadow-xs">
          <div class="flex flex-wrap items-center gap-3">
            <!-- ASIN Selector -->
            <div class="flex items-center gap-2">
              <span class="text-xs font-medium text-muted-foreground">关注竞品：</span>
              <Select v-model="selectedBsrAsin">
                <SelectTrigger class="h-8 w-56 text-xs">
                  <SelectValue placeholder="选择目标 ASIN" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部竞品多维度对比</SelectItem>
                  <SelectItem
                    v-for="comp in bsrCompetitors"
                    :key="comp.asin"
                    :value="comp.asin"
                  >
                    {{ comp.asin }} ({{ comp.category }})
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <!-- Time Window Selector -->
            <div class="flex items-center gap-1 border-l pl-3">
              <Button
                size="sm"
                :variant="bsrDays === 7 ? 'default' : 'ghost'"
                class="h-7 text-xs px-2.5"
                @click="bsrDays = 7"
              >
                近 7 天
              </Button>
              <Button
                size="sm"
                :variant="bsrDays === 30 ? 'default' : 'ghost'"
                class="h-7 text-xs px-2.5"
                @click="bsrDays = 30"
              >
                近 30 天
              </Button>
              <Button
                size="sm"
                :variant="bsrDays === 90 ? 'default' : 'ghost'"
                class="h-7 text-xs px-2.5"
                @click="bsrDays = 90"
              >
                近 90 天
              </Button>
            </div>
          </div>

          <Button
            size="sm"
            variant="ghost"
            class="h-7 gap-1 text-xs text-muted-foreground hover:text-foreground"
            :disabled="bsrLoading"
            @click="() => refetchBsr()"
          >
            <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': bsrLoading }" />
            刷新走势
          </Button>
        </div>

        <!-- 4 KPI Cards for Active Competitor -->
        <div v-if="activeBsrItem" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <!-- Card 1: BSR Rank & Change -->
          <Card class="shadow-xs">
            <CardHeader class="pb-2">
              <CardTitle class="text-xs font-medium text-muted-foreground flex items-center justify-between">
                <span>当前主类目 BSR 排名</span>
                <Trophy class="h-3.5 w-3.5 text-amber-500" />
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div class="flex items-baseline gap-2">
                <span class="text-2xl font-bold font-mono">#{{ activeBsrItem.current_bsr }}</span>
                <span
                  class="flex items-center text-xs font-medium"
                  :class="activeBsrItem.bsr_change_7d <= 0 ? 'text-emerald-600' : 'text-rose-600'"
                >
                  <ArrowUpRight v-if="activeBsrItem.bsr_change_7d <= 0" class="h-3.5 w-3.5" />
                  <ArrowDownRight v-else class="h-3.5 w-3.5" />
                  {{ activeBsrItem.bsr_change_7d <= 0 ? `升 ${Math.abs(activeBsrItem.bsr_change_7d)}` : `降 ${activeBsrItem.bsr_change_7d}` }} 位 (7d)
                </span>
              </div>
              <p class="mt-1 text-[11px] text-muted-foreground truncate">{{ activeBsrItem.category }}</p>
            </CardContent>
          </Card>

          <!-- Card 2: Subcategory Rank -->
          <Card class="shadow-xs">
            <CardHeader class="pb-2">
              <CardTitle class="text-xs font-medium text-muted-foreground">子类目细分排名</CardTitle>
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold font-mono">
                #{{ activeBsrItem.current_sub_bsr ?? '—' }}
              </div>
              <p class="mt-1 text-[11px] text-muted-foreground truncate">
                {{ activeBsrItem.subcategory ?? '细分类目' }}
              </p>
            </CardContent>
          </Card>

          <!-- Card 3: Current Price -->
          <Card class="shadow-xs">
            <CardHeader class="pb-2">
              <CardTitle class="text-xs font-medium text-muted-foreground">当前在售标价</CardTitle>
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold font-mono">
                ${{ activeBsrItem.current_price.toFixed(2) }}
              </div>
              <p class="mt-1 text-[11px] text-muted-foreground">
                评级 {{ activeBsrItem.rating.toFixed(1) }} ⭐ ({{ activeBsrItem.review_count.toLocaleString() }} 评论)
              </p>
            </CardContent>
          </Card>

          <!-- Card 4: Buy Box Status -->
          <Card class="shadow-xs">
            <CardHeader class="pb-2">
              <CardTitle class="text-xs font-medium text-muted-foreground">Buy Box 占有率</CardTitle>
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold font-mono text-emerald-600">
                {{ (activeBsrItem.buy_box_ratio * 100).toFixed(1) }}%
              </div>
              <p class="mt-1 text-[11px] text-muted-foreground truncate">
                主要持有人：{{ activeBsrItem.buy_box_winner }}
              </p>
            </CardContent>
          </Card>
        </div>

        <!-- BSR & Price Trend Chart -->
        <Card class="shadow-xs">
          <CardHeader class="pb-2">
            <CardTitle class="text-base font-semibold">
              {{ selectedBsrAsin === 'ALL' ? '竞品群 BSR 排名走势对比' : `ASIN ${selectedBsrAsin} 排名与标价异动时序` }}
            </CardTitle>
            <CardDescription>
              左侧 Y 轴采用逆序呈现（#1 位列顶部，符合亚马逊排名直觉）；右侧对应售价波动阶梯。
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div v-if="bsrLoading" class="flex h-80 items-center justify-center text-sm text-muted-foreground">
              <Loader2 class="mr-2 h-5 w-5 animate-spin" />
              正在绘制 BSR 时序趋势图...
            </div>
            <VChart v-else :option="bsrChartOption" height-class="h-80" />
          </CardContent>
        </Card>

        <!-- Competitor Overview Table -->
        <Card class="shadow-xs">
          <CardHeader class="pb-3">
            <CardTitle class="text-base font-semibold">竞品多维核心指标横向矩阵</CardTitle>
            <CardDescription>
              各监控 ASIN 当前排名、价格、Buy Box 持有率与综合评分横向对齐。
            </CardDescription>
          </CardHeader>
          <CardContent class="p-0">
            <div class="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow class="bg-muted/30 text-xs">
                    <TableHead class="w-36">竞品 ASIN</TableHead>
                    <TableHead>商品标题与类目</TableHead>
                    <TableHead class="w-28 text-center">主类目 BSR</TableHead>
                    <TableHead class="w-28 text-center">7 日异动</TableHead>
                    <TableHead class="w-24 text-right">当前标价</TableHead>
                    <TableHead class="w-32 text-center">Buy Box 占有率</TableHead>
                    <TableHead class="w-32 text-center">评分 / 评论数</TableHead>
                    <TableHead class="w-28 text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow
                    v-for="comp in bsrCompetitors"
                    :key="comp.asin"
                    class="text-xs hover:bg-muted/40 cursor-pointer"
                    :class="{ 'bg-muted/20 font-medium': selectedBsrAsin === comp.asin }"
                    @click="selectedBsrAsin = comp.asin"
                  >
                    <!-- ASIN -->
                    <TableCell class="font-mono font-medium">
                      <a
                        :href="`https://www.amazon.com/dp/${comp.asin}`"
                        target="_blank"
                        rel="noreferrer"
                        class="inline-flex items-center gap-1 text-primary hover:underline"
                        @click.stop
                      >
                        {{ comp.asin }}
                        <ExternalLink class="h-3 w-3 text-muted-foreground" />
                      </a>
                    </TableCell>

                    <!-- Title & Category -->
                    <TableCell>
                      <div class="line-clamp-1 font-normal text-foreground">{{ comp.title }}</div>
                      <div class="text-[11px] text-muted-foreground">{{ comp.category }} · {{ comp.subcategory ?? '主品类' }}</div>
                    </TableCell>

                    <!-- Current BSR -->
                    <TableCell class="text-center font-mono font-semibold">
                      #{{ comp.current_bsr }}
                    </TableCell>

                    <!-- 7-day Change -->
                    <TableCell class="text-center font-mono">
                      <span
                        v-if="comp.bsr_change_7d <= 0"
                        class="inline-flex items-center text-emerald-600"
                      >
                        <ArrowUpRight class="h-3.5 w-3.5 mr-0.5" />
                        +{{ Math.abs(comp.bsr_change_7d) }}
                      </span>
                      <span
                        v-else
                        class="inline-flex items-center text-rose-600"
                      >
                        <ArrowDownRight class="h-3.5 w-3.5 mr-0.5" />
                        -{{ comp.bsr_change_7d }}
                      </span>
                    </TableCell>

                    <!-- Current Price -->
                    <TableCell class="text-right font-mono font-medium">
                      ${{ comp.current_price.toFixed(2) }}
                    </TableCell>

                    <!-- Buy Box -->
                    <TableCell class="text-center">
                      <Badge variant="outline" class="border-emerald-200 bg-emerald-50 text-emerald-700">
                        {{ (comp.buy_box_ratio * 100).toFixed(0) }}%
                      </Badge>
                    </TableCell>

                    <!-- Rating & Reviews -->
                    <TableCell class="text-center text-muted-foreground">
                      {{ comp.rating.toFixed(1) }} ⭐ ({{ comp.review_count.toLocaleString() }})
                    </TableCell>

                    <!-- Actions -->
                    <TableCell class="text-right" @click.stop>
                      <Button
                        size="sm"
                        variant="ghost"
                        class="h-7 text-xs text-primary"
                        @click="selectedBsrAsin = comp.asin"
                      >
                        聚焦走势
                      </Button>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      <!-- ========================================== -->
      <!-- TAB 3: 跨平台矩阵 (Cross-Platform Matrix)  -->
      <!-- ========================================== -->
      <TabsContent value="cross" class="space-y-6 animate-in fade-in duration-200">
        <!-- 4 Summary KPI Cards -->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card class="shadow-xs">
            <CardHeader class="pb-2">
              <CardTitle class="text-xs font-medium text-muted-foreground">跨平台对标 SKU 总量</CardTitle>
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold font-mono">
                {{ crossMetrics.total_skus }}
                <span class="text-xs font-normal text-muted-foreground">款</span>
              </div>
              <p class="mt-1 text-[11px] text-muted-foreground">覆盖 TikTok Shop 与 Temu 工厂货源</p>
            </CardContent>
          </Card>

          <Card class="shadow-xs">
            <CardHeader class="pb-2">
              <CardTitle class="text-xs font-medium text-muted-foreground">平均多模态图文对齐度</CardTitle>
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold font-mono text-primary">
                {{ (crossMetrics.avg_match_score * 100).toFixed(1) }}%
              </div>
              <p class="mt-1 text-[11px] text-muted-foreground">基于商品外观特征与规格匹配打分</p>
            </CardContent>
          </Card>

          <Card class="shadow-xs">
            <CardHeader class="pb-2">
              <CardTitle class="text-xs font-medium text-muted-foreground">最大单件套利利润空间</CardTitle>
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold font-mono text-emerald-600">
                +${{ crossMetrics.max_spread.toFixed(2) }}
              </div>
              <p class="mt-1 text-[11px] text-muted-foreground">已扣减估算佣金与跨国履约仓配成本</p>
            </CardContent>
          </Card>

          <Card class="shadow-xs">
            <CardHeader class="pb-2">
              <CardTitle class="text-xs font-medium text-muted-foreground">高置信套利机会款</CardTitle>
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold font-mono text-amber-600">
                {{ crossMetrics.arbitrage_opportunities }}
                <span class="text-xs font-normal text-muted-foreground">款</span>
              </div>
              <p class="mt-1 text-[11px] text-muted-foreground">匹配度 ≥ 85% 且测算价差大于 0</p>
            </CardContent>
          </Card>
        </div>

        <!-- Filter and Search Bar -->
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between rounded-lg border bg-card p-3 shadow-xs">
          <div class="flex flex-wrap items-center gap-3">
            <!-- Channel Filter -->
            <div class="flex items-center gap-1.5">
              <span class="text-xs font-medium text-muted-foreground">渠道平台：</span>
              <Select v-model="platformFilter">
                <SelectTrigger class="h-8 w-36 text-xs">
                  <SelectValue placeholder="渠道平台" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部渠道</SelectItem>
                  <SelectItem value="TIKTOK">TikTok Shop</SelectItem>
                  <SelectItem value="TEMU">Temu</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <!-- Status Filter -->
            <div class="flex items-center gap-1.5">
              <span class="text-xs font-medium text-muted-foreground">匹配状态：</span>
              <Select v-model="matchStatusFilter">
                <SelectTrigger class="h-8 w-36 text-xs">
                  <SelectValue placeholder="匹配状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部状态</SelectItem>
                  <SelectItem value="MATCHED">已对齐 (MATCHED)</SelectItem>
                  <SelectItem value="PENDING">待核验 (PENDING)</SelectItem>
                  <SelectItem value="VARIANT">变体差异 (VARIANT)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <!-- Keyword Search -->
            <div class="relative w-48 sm:w-64">
              <Search class="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
              <Input
                v-model="crossSearchQuery"
                placeholder="搜索 ASIN、对标 SKU 或品名..."
                class="h-8 pl-8 text-xs"
              />
            </div>
          </div>

          <Button
            size="sm"
            variant="ghost"
            class="h-7 gap-1 text-xs text-muted-foreground hover:text-foreground"
            :disabled="crossLoading"
            @click="() => refetchCross()"
          >
            <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': crossLoading }" />
            刷新矩阵
          </Button>
        </div>

        <!-- Cross-Platform SKU Matrix Table -->
        <Card class="shadow-xs">
          <CardHeader class="pb-3">
            <CardTitle class="text-base font-semibold">跨平台货源与竞价套利对齐矩阵</CardTitle>
            <CardDescription>
              对齐亚马逊目标 ASIN 在 TikTok Shop 与 Temu 的货源对标款，实时监控价差与套利可行性。
            </CardDescription>
          </CardHeader>
          <CardContent class="p-0">
            <div v-if="crossLoading" class="flex items-center justify-center py-16 text-sm text-muted-foreground">
              <Loader2 class="mr-2 h-5 w-5 animate-spin" />
              正在同步跨平台货源数据...
            </div>

            <div v-else-if="!filteredCrossItems.length" class="p-8">
              <EmptyState
                :icon="Globe"
                title="未找到匹配的跨平台 SKU"
                description="请尝试调整筛选条件或重置搜索关键词"
              />
            </div>

            <div v-else class="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow class="bg-muted/30 text-xs">
                    <TableHead class="w-44">Amazon 目标款</TableHead>
                    <TableHead class="w-32">对标渠道</TableHead>
                    <TableHead>渠道对标商品 / 货源 SKU</TableHead>
                    <TableHead class="w-36">图文匹配度</TableHead>
                    <TableHead class="w-32 text-right">渠道售价 / 预估费</TableHead>
                    <TableHead class="w-28 text-right">预估套利利差</TableHead>
                    <TableHead class="w-28 text-center">渠道月销量</TableHead>
                    <TableHead class="w-24 text-center">状态</TableHead>
                    <TableHead class="w-24 text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow v-for="item in filteredCrossItems" :key="item.id" class="text-xs hover:bg-muted/40">
                    <!-- Amazon Target -->
                    <TableCell>
                      <div class="font-mono font-medium text-foreground">
                        <a
                          :href="`https://www.amazon.com/dp/${item.target_asin}`"
                          target="_blank"
                          rel="noreferrer"
                          class="inline-flex items-center gap-1 text-primary hover:underline"
                        >
                          {{ item.target_asin }}
                          <ExternalLink class="h-3 w-3 text-muted-foreground" />
                        </a>
                      </div>
                      <div class="text-[11px] text-muted-foreground font-mono mt-0.5">
                        Amazon: ${{ item.target_price.toFixed(2) }}
                      </div>
                    </TableCell>

                    <!-- Platform Badge -->
                    <TableCell>
                      <Badge
                        v-if="item.platform === 'TIKTOK'"
                        variant="outline"
                        class="border-sky-300 bg-sky-50 text-sky-700 font-medium"
                      >
                        TikTok Shop
                      </Badge>
                      <Badge
                        v-else
                        variant="outline"
                        class="border-amber-300 bg-amber-50 text-amber-700 font-medium"
                      >
                        Temu
                      </Badge>
                    </TableCell>

                    <!-- Platform SKU & Title -->
                    <TableCell>
                      <div class="font-mono text-[11px] font-semibold text-foreground">
                        {{ item.platform_sku }}
                      </div>
                      <div class="line-clamp-1 text-muted-foreground text-[11px] mt-0.5">
                        {{ item.platform_title }}
                      </div>
                    </TableCell>

                    <!-- Match Score -->
                    <TableCell>
                      <div class="space-y-1">
                        <div class="flex items-center justify-between text-[11px]">
                          <span class="font-mono font-semibold">{{ (item.match_score * 100).toFixed(0) }}%</span>
                          <span
                            class="text-[10px]"
                            :class="item.match_score >= 0.9 ? 'text-emerald-600' : 'text-amber-600'"
                          >
                            {{ item.match_score >= 0.9 ? '高置信' : '需核对' }}
                          </span>
                        </div>
                        <div class="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                          <div
                            class="h-full rounded-full transition-all"
                            :class="item.match_score >= 0.9 ? 'bg-emerald-500' : 'bg-amber-500'"
                            :style="{ width: `${item.match_score * 100}%` }"
                          />
                        </div>
                      </div>
                    </TableCell>

                    <!-- Channel Price & Fees -->
                    <TableCell class="text-right font-mono">
                      <div class="font-medium text-foreground">${{ item.platform_price.toFixed(2) }}</div>
                      <div class="text-[10px] text-muted-foreground">费: ${{ item.estimated_fees.toFixed(2) }}</div>
                    </TableCell>

                    <!-- Arbitrage Spread -->
                    <TableCell class="text-right font-mono font-bold">
                      <span
                        v-if="item.estimated_spread > 0"
                        class="inline-flex items-center text-emerald-600"
                      >
                        +${{ item.estimated_spread.toFixed(2) }}
                      </span>
                      <span
                        v-else
                        class="inline-flex items-center text-rose-600"
                      >
                        -${{ Math.abs(item.estimated_spread).toFixed(2) }}
                      </span>
                    </TableCell>

                    <!-- Monthly Sales -->
                    <TableCell class="text-center font-mono text-muted-foreground">
                      {{ item.monthly_sales.toLocaleString() }}
                    </TableCell>

                    <!-- Match Status -->
                    <TableCell class="text-center">
                      <Badge
                        v-if="item.match_status === 'MATCHED'"
                        variant="outline"
                        class="border-emerald-200 bg-emerald-50 text-emerald-700"
                      >
                        已对齐
                      </Badge>
                      <Badge
                        v-else-if="item.match_status === 'PENDING'"
                        variant="outline"
                        class="border-amber-200 bg-amber-50 text-amber-700"
                      >
                        待核对
                      </Badge>
                      <Badge
                        v-else
                        variant="outline"
                        class="border-slate-300 bg-slate-50 text-slate-600"
                      >
                        差异款
                      </Badge>
                    </TableCell>

                    <!-- Actions -->
                    <TableCell class="text-right">
                      <a
                        :href="item.platform_url"
                        target="_blank"
                        rel="noreferrer"
                        class="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                      >
                        查看
                        <ExternalLink class="h-3 w-3" />
                      </a>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  </div>
</template>
