<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import { getAlerts, getClusters, getDashboardOverview, getRecommendations, listTasks } from '@/api'
import type { Alert, Cluster, DashboardOverview, Recommendation, Task } from '@/types'
import { formatPercent, formatRelativeTime, formatUsd } from '@/utils/format'
import TaskStatusBadge from '@/components/common/TaskStatusBadge.vue'
import EChart from '@/components/charts/EChart.vue'
import { useTasksStore } from '@/stores/tasks'
import type { CreateTaskRequest } from '@/types'
import { DEFAULT_TASK_ID } from '@/stores/tasks'

const router = useRouter()
const tasksStore = useTasksStore()

const loading = ref(true)
const overview = ref<DashboardOverview | null>(null)
const recommendations = ref<Recommendation[]>([])
const tasks = ref<Task[]>([])
const alerts = ref<Alert[]>([])
const clusters = ref<Cluster[]>([])

onMounted(async () => {
  const [ov, rec, tk, al, cl] = await Promise.all([
    getDashboardOverview(),
    getRecommendations(),
    listTasks({ page_size: 5 }),
    getAlerts({ page_size: 4 }),
    getClusters(DEFAULT_TASK_ID),
  ])
  overview.value = ov
  recommendations.value = rec.items
  tasks.value = tk.items
  alerts.value = al.items
  clusters.value = cl.items
  loading.value = false
})

/* ---------- KPI 统计卡 ---------- */

const statCards = [
  { key: 'monitored_product_count', label: '监控竞品数', unit: '', icon: 'box', gradient: 'from-indigo-500 to-violet-500', format: 'int' },
  { key: 'running_task_count', label: '运行中诊断任务', unit: '', icon: 'bolt', gradient: 'from-amber-500 to-orange-500', format: 'int' },
  { key: 'pain_point_cluster_count', label: '痛点聚类', unit: '个', icon: 'chart', gradient: 'from-violet-500 to-fuchsia-500', format: 'int' },
  { key: 'fba_saving_pool_usd', label: 'FBA 节省池', unit: 'USD', icon: 'coin', gradient: 'from-emerald-500 to-teal-500', format: 'money' },
  { key: 'veto_triggered_count', label: '风控熔断次数', unit: '', icon: 'shield', gradient: 'from-rose-500 to-red-500', format: 'int' },
  { key: 'avg_rating', label: '平均评分', unit: '/5', icon: 'star', gradient: 'from-sky-500 to-blue-500', format: 'rating' },
  { key: 'negative_review_rate', label: '差评率', unit: '', icon: 'alert', gradient: 'from-slate-500 to-slate-700', format: 'percent' },
] as const

const ICONS: Record<string, string> = {
  box: 'M20.25 7.5l-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z',
  bolt: 'm3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z',
  chart: 'M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z',
  coin: 'M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 5.625c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125',
  shield: 'M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z',
  star: 'M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z',
  alert: 'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z',
}

function statValue(key: string): string {
  if (!overview.value) return '–'
  const v = (overview.value as unknown as Record<string, unknown>)[key]
  if (typeof v !== 'number') return String(v)
  switch (key) {
    case 'fba_saving_pool_usd':
      return formatUsd(v, false)
    case 'avg_rating':
      return v.toFixed(1)
    case 'negative_review_rate':
      return formatPercent(v)
    default:
      return v.toLocaleString('en-US')
  }
}

/* ---------- ECharts：差评痛点分布 ---------- */

const clusterChartOption = computed<EChartsOption>(() => {
  const list = [...clusters.value].sort((a, b) => b.frequency - a.frequency).slice(0, 6)
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: (p: unknown) => {
      const arr = p as { name: string; value: number }[]
      return arr.map((i) => `${i.name}：${i.value} 条`).join('<br/>')
    } },
    grid: { left: 8, right: 16, top: 10, bottom: 4, containLabel: true },
    xAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed', color: '#e2e8f0' } }, axisLabel: { fontSize: 10 } },
    yAxis: {
      type: 'category',
      data: list.map((c) => c.cluster_name).reverse(),
      axisLabel: { fontSize: 11, width: 110, overflow: 'truncate' },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        name: '差评数',
        type: 'bar',
        data: list.map((c) => c.frequency).reverse(),
        barWidth: 14,
        itemStyle: {
          borderRadius: [0, 7, 7, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#6366f1' },
            { offset: 1, color: '#a855f7' },
          ]),
        },
      },
    ],
  }
})

/* ---------- ECharts：评分健康度仪表盘 ---------- */

const ratingGaugeOption = computed<EChartsOption>(() => {
  const value = overview.value?.avg_rating ?? 0
  return {
    series: [
      {
        type: 'gauge',
        startAngle: 220,
        endAngle: -40,
        min: 0,
        max: 5,
        radius: '92%',
        center: ['50%', '58%'],
        progress: { show: true, width: 12, itemStyle: { color: value >= 4 ? '#10b981' : value >= 3.5 ? '#f59e0b' : '#ef4444' } },
        axisLine: { lineStyle: { width: 12, color: [[1, '#e2e8f0']] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { show: false },
        anchor: { show: false },
        detail: {
          valueAnimation: true,
          fontSize: 30,
          fontWeight: 700,
          offsetCenter: [0, 0],
          color: '#0f172a',
          formatter: (v: number) => v.toFixed(1),
        },
        data: [{ value, name: '平均评分' }],
        title: { offsetCenter: [0, 34], fontSize: 11, color: '#64748b' },
      },
    ],
  }
})

/* ---------- 快速触发 ---------- */

const quickForm = ref({ asins: 'B0D2XYZ8KQ, B0C5JXM1Z2', marketplace: 'US', moldBudget: 8500, moq: 2000 })
const triggering = ref(false)

async function triggerQuickTask() {
  const asins = quickForm.value.asins
    .split(/[,，\s]+/)
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean)
    .slice(0, 10)
  if (!asins.length) return
  triggering.value = true
  try {
    const req: CreateTaskRequest = {
      asins,
      marketplace: quickForm.value.marketplace,
      review_window_months: 6,
      financial_constraint: {
        mold_cost_usd: quickForm.value.moldBudget,
        moq: quickForm.value.moq,
        current_gross_margin: 0.25,
        expected_price_usd: 29.99,
        unit_cost_increase_usd: 1.2,
        expected_payback_months: 6,
        sea_freight_usd_per_cbm: 180,
      },
      options: { enable_vision_audit: true, enable_backtest: true },
    }
    const ids = await tasksStore.createAndWatchTask(req)
    if (ids.length) router.push('/voc')
  } finally {
    triggering.value = false
  }
}

/* ---------- 工具 ---------- */

const alertColor: Record<string, string> = {
  high: 'bg-rose-500',
  medium: 'bg-amber-500',
  low: 'bg-slate-400',
}

function openTask(task: Task) {
  router.push(`/reformulation?task_id=${task.task_id}`)
}
</script>

<template>
  <div class="space-y-6">
    <!-- 顶部 KPI 指标 -->
    <div v-if="loading" class="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
      <div v-for="i in 7" :key="i" class="card card-pad animate-pulse">
        <div class="h-3 w-16 rounded bg-slate-200" />
        <div class="mt-3 h-7 w-20 rounded bg-slate-200" />
      </div>
    </div>
    <div v-else class="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
      <div
        v-for="s in statCards"
        :key="s.key"
        class="card card-pad group transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
      >
        <div class="flex items-center justify-between">
          <div class="text-xs text-slate-500">{{ s.label }}</div>
          <div class="grid size-7 place-items-center rounded-lg bg-gradient-to-br text-white shadow-sm" :class="s.gradient">
            <svg class="size-4" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" :d="ICONS[s.icon]" />
            </svg>
          </div>
        </div>
        <div class="mt-2 flex items-baseline gap-1">
          <span class="text-2xl font-bold tracking-tight text-slate-900">{{ statValue(s.key) }}</span>
          <span v-if="s.unit" class="text-xs text-slate-400">{{ s.unit }}</span>
        </div>
      </div>
    </div>

    <div class="grid gap-6 xl:grid-cols-3">
      <!-- 差评痛点分布 + 评分健康度 -->
      <section class="card xl:col-span-2">
        <header class="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 class="text-sm font-semibold">差评痛点分布</h2>
          <span class="text-xs text-slate-400">按评论频次 Top 6 聚类</span>
        </header>
        <div class="p-4">
          <EChart v-if="!loading" :option="clusterChartOption" height="280px" />
          <div v-else class="h-[280px] animate-pulse rounded-lg bg-slate-100" />
          <div v-if="!loading && !clusters.length" class="py-12 text-center text-sm text-slate-400">暂无聚类数据</div>
        </div>
      </section>

      <div class="space-y-6">
        <!-- 评分健康度 -->
        <section class="card">
          <header class="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <h2 class="text-sm font-semibold">评分健康度</h2>
          </header>
          <div class="p-4">
            <EChart v-if="!loading" :option="ratingGaugeOption" height="170px" />
            <div class="mt-1 flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-xs">
              <span class="text-slate-500">差评率</span>
              <span class="font-semibold text-rose-600">{{ overview ? formatPercent(overview.negative_review_rate) : '–' }}</span>
            </div>
          </div>
        </section>

        <!-- 告警速览 -->
        <section class="card">
          <header class="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <h2 class="text-sm font-semibold">风控告警速览</h2>
            <button class="text-xs text-indigo-600 hover:underline" @click="router.push('/financial')">全部 →</button>
          </header>
          <div class="divide-y divide-slate-100">
            <div v-for="a in alerts" :key="a.alert_id" class="px-5 py-3.5">
              <div class="flex items-center gap-2">
                <span class="size-2 shrink-0 rounded-full" :class="alertColor[a.severity]" />
                <span class="min-w-0 truncate text-sm font-medium text-slate-700">{{ a.title }}</span>
              </div>
              <p class="mt-1 line-clamp-2 text-xs text-slate-500">{{ a.message }}</p>
            </div>
            <div v-if="!alerts.length" class="px-5 py-8 text-center text-sm text-slate-400">暂无告警</div>
          </div>
        </section>
      </div>
    </div>

    <div class="grid gap-6 xl:grid-cols-3">
      <!-- 高价值改款推荐 -->
      <section class="card xl:col-span-2">
        <header class="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 class="text-sm font-semibold">高价值改款推荐</h2>
          <span class="text-xs text-slate-400">按预估 ROI 排序</span>
        </header>
        <div class="divide-y divide-slate-100">
          <div v-for="r in recommendations" :key="r.product_id" class="group flex items-center gap-4 px-5 py-4 transition-colors hover:bg-slate-50/70">
            <img :src="r.main_image_url" :alt="r.title" class="size-14 shrink-0 rounded-lg object-cover" loading="lazy" />
            <div class="min-w-0 flex-1">
              <div class="truncate text-sm font-medium text-slate-800">{{ r.title }}</div>
              <div class="mt-0.5 text-xs text-slate-400">
                ASIN {{ r.asin }} · 完成于 {{ formatRelativeTime(r.finished_at) }}
              </div>
              <div class="mt-1.5 flex flex-wrap gap-1.5 text-xs">
                <span class="rounded-md bg-emerald-50 px-2 py-0.5 font-medium text-emerald-700">ROI {{ r.estimated_roi }}x</span>
                <span class="rounded-md bg-sky-50 px-2 py-0.5 font-medium text-sky-700">退货率 ↓{{ (r.return_rate_reduction * 100).toFixed(0) }}%</span>
                <span
                  class="rounded-md px-2 py-0.5 font-medium"
                  :class="r.veto_status === 'PASSED' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'"
                >
                  {{ r.veto_status === 'PASSED' ? '已通过风控' : '被否决' }}
                </span>
              </div>
            </div>
            <button
              class="shrink-0 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-600"
              @click="router.push('/reformulation')"
            >
              查看报告 →
            </button>
          </div>
          <div v-if="!recommendations.length" class="px-5 py-10 text-center text-sm text-slate-400">暂无推荐项目</div>
        </div>
      </section>

      <!-- 快速触发诊断任务 -->
      <section class="card overflow-hidden">
        <div class="bg-gradient-to-br from-indigo-600 to-violet-600 px-5 py-4 text-white">
          <h2 class="text-sm font-semibold">快速触发诊断任务</h2>
          <p class="mt-0.5 text-xs text-indigo-100">输入 ASIN / 链接，一键跑通 LangGraph 洞察流水线</p>
        </div>
        <form class="space-y-3 p-5" @submit.prevent="triggerQuickTask">
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-500">ASIN / 链接（逗号分隔，最多 10 个）</label>
            <textarea
              v-model="quickForm.asins"
              rows="2"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none transition-colors focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
              placeholder="B0D2XYZ8KQ, B0C5JXM1Z2"
            />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="mb-1 block text-xs font-medium text-slate-500">目标站点</label>
              <select
                v-model="quickForm.marketplace"
                class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-400"
              >
                <option value="US">美国 US</option>
                <option value="DE">德国 DE</option>
                <option value="JP">日本 JP</option>
              </select>
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-slate-500">开模预算 ($)</label>
              <input
                v-model.number="quickForm.moldBudget"
                type="number"
                min="0"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400"
              />
            </div>
          </div>
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-500">MOQ（件）</label>
            <input
              v-model.number="quickForm.moq"
              type="number"
              min="0"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400"
            />
          </div>
          <button
            type="submit"
            class="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-60"
            :disabled="triggering || tasksStore.flowActive || !quickForm.asins.trim()"
          >
            <svg v-if="triggering || tasksStore.flowActive" class="size-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4Z" />
            </svg>
            <span>{{ tasksStore.flowActive ? '任务执行中…' : '一键发起诊断' }}</span>
          </button>
        </form>
      </section>
    </div>

    <!-- 最近诊断任务 -->
    <section class="card">
      <header class="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <h2 class="text-sm font-semibold">最近诊断任务</h2>
        <button class="text-xs text-indigo-600 hover:underline" @click="router.push('/voc')">全部 →</button>
      </header>
      <div class="overflow-x-auto">
        <table class="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr class="border-b border-slate-100 text-xs text-slate-400">
              <th class="px-5 py-3 font-medium">任务 ID</th>
              <th class="px-5 py-3 font-medium">ASIN</th>
              <th class="px-5 py-3 font-medium">状态</th>
              <th class="px-5 py-3 font-medium">进度</th>
              <th class="px-5 py-3 font-medium">创建时间</th>
              <th class="px-5 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr v-for="t in tasks" :key="t.task_id" class="transition-colors hover:bg-slate-50/60">
              <td class="px-5 py-3 font-mono text-xs text-slate-600">{{ t.task_id }}</td>
              <td class="px-5 py-3 text-xs">{{ t.asin }}</td>
              <td class="px-5 py-3"><TaskStatusBadge :status="t.status" /></td>
              <td class="px-5 py-3">
                <div class="flex items-center gap-2">
                  <div class="h-1.5 w-24 overflow-hidden rounded-full bg-slate-100">
                    <div
                      class="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-500"
                      :style="{ width: `${t.progress}%` }"
                    />
                  </div>
                  <span class="text-xs text-slate-500">{{ t.progress }}%</span>
                </div>
              </td>
              <td class="px-5 py-3 text-xs text-slate-500">{{ formatRelativeTime(t.created_at) }}</td>
              <td class="px-5 py-3">
                <button
                  v-if="t.status === 'COMPLETED'"
                  class="rounded-md border border-slate-200 px-2 py-1 text-xs font-medium text-slate-600 hover:border-indigo-300 hover:text-indigo-600"
                  @click="openTask(t)"
                >
                  查看
                </button>
                <span v-else class="text-xs text-slate-300">—</span>
              </td>
            </tr>
            <tr v-if="!tasks.length">
              <td colspan="6" class="px-5 py-10 text-center text-sm text-slate-400">暂无诊断任务</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
