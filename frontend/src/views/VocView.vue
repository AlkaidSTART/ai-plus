<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import { getClusters, getTask, getVisualEvidences, listReviews } from '@/api'
import type { Cluster, Review, VisualEvidence } from '@/types'
import { DEFECT_LABEL, ISSUE_TYPE_LABEL, SEVERITY_LABEL } from '@/utils/severity'
import { DEFAULT_TASK_ID } from '@/stores/tasks'
import EChart from '@/components/charts/EChart.vue'

const clusters = ref<Cluster[]>([])
const reviews = ref<Review[]>([])
const evidences = ref<VisualEvidence[]>([])
const loading = ref(true)
const selectedClusterId = ref<string | null>(null)

/* ---------- 筛选条件 ---------- */
const ratingMin = ref<number>(0)
const ratingMax = ref<number>(0)
const language = ref<string>('')
const keyword = ref<string>('')
const verifiedOnly = ref(false)

onMounted(async () => {
  const [c, r, e] = await Promise.all([
    getClusters(DEFAULT_TASK_ID),
    listReviews(DEFAULT_TASK_ID, { page_size: 100 }),
    getVisualEvidences(DEFAULT_TASK_ID),
  ])
  clusters.value = c.items
  reviews.value = r.items
  evidences.value = e.items
  loading.value = false
  if (c.items.length) selectedClusterId.value = c.items[0].cluster_id
})

const selectedCluster = computed<Cluster | null>(() => {
  return clusters.value.find((c) => c.cluster_id === selectedClusterId.value) ?? null
})

/* ---------- 评论筛选 ---------- */

const filteredReviews = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return reviews.value.filter((r) => {
    if (ratingMin.value > 0 && r.rating > ratingMin.value) return false
    if (ratingMax.value > 0 && r.rating < ratingMax.value) return false
    if (language.value && r.language !== language.value) return false
    if (verifiedOnly.value && !r.verified_purchase) return false
    if (kw) {
      const haystack = `${r.title ?? ''} ${r.content} ${r.translated_content ?? ''}`.toLowerCase()
      if (!haystack.includes(kw)) return false
    }
    return true
  })
})

/* ---------- 取证关联：优先展示当前聚类的 sample_image_ids ---------- */

const evidenceByCluster = computed(() => {
  const cluster = selectedCluster.value
  if (!cluster) return evidences.value
  const byId = new Map(evidences.value.map((e) => [e.image_id, e]))
  const linked = cluster.sample_image_ids.map((id) => byId.get(id)).filter(Boolean) as VisualEvidence[]
  const rest = evidences.value.filter((e) => e.cluster_ids.includes(cluster.cluster_id) && !cluster.sample_image_ids.includes(e.image_id))
  const merged = [...linked, ...rest]
  return merged.length ? merged : evidences.value
})

/* ---------- ECharts：严重度分布玫瑰图 ---------- */

const severityRoseOption = computed<EChartsOption>(() => {
  const counts = { critical: 0, moderate: 0, minor: 0 }
  clusters.value.forEach((c) => {
    counts[c.severity_level] = (counts[c.severity_level] ?? 0) + 1
  })
  const total = clusters.value.length || 1
  const colorMap = { critical: '#f43f5e', moderate: '#f59e0b', minor: '#38bdf8' }
  return {
    tooltip: { trigger: 'item', formatter: '{b}：{c} 个（{d}%）' },
    legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 11 } },
    series: [
      {
        name: '严重度',
        type: 'pie',
        roseType: 'radius',
        radius: ['28%', '68%'],
        center: ['50%', '46%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 12, fontWeight: 600 } },
        data: (['critical', 'moderate', 'minor'] as const)
          .filter((k) => counts[k] > 0)
          .map((k) => ({
            name: SEVERITY_LABEL[k],
            value: counts[k],
            itemStyle: { color: colorMap[k] },
          })),
      },
    ],
    graphic: [
      {
        type: 'text',
        left: 'center',
        top: '38%',
        style: { text: String(total), fontSize: 22, fontWeight: 700, fill: '#0f172a', textAlign: 'center' },
      },
      {
        type: 'text',
        left: 'center',
        top: '50%',
        style: { text: '痛点聚类', fontSize: 11, fill: '#94a3b8', textAlign: 'center' },
      },
    ],
  }
})

/* ---------- ECharts：Top 痛点频次横向条图 ---------- */

const frequencyBarOption = computed<EChartsOption>(() => {
  const list = [...clusters.value].sort((a, b) => b.frequency - a.frequency).slice(0, 8)
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 8, right: 20, top: 8, bottom: 4, containLabel: true },
    xAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed', color: '#e2e8f0' } }, axisLabel: { fontSize: 10 } },
    yAxis: {
      type: 'category',
      data: list.map((c) => c.cluster_name).reverse(),
      axisLabel: { fontSize: 11, width: 96, overflow: 'truncate' },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        name: '评论频次',
        type: 'bar',
        data: list.map((c) => c.frequency).reverse(),
        barWidth: 12,
        itemStyle: {
          borderRadius: [0, 6, 6, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#8b5cf6' },
            { offset: 1, color: '#ec4899' },
          ]),
        },
      },
    ],
  }
})

const langLabel: Record<string, string> = { en: 'EN', de: 'DE', ja: 'JA', es: 'ES' }

function severityColor(level: string): string {
  return level === 'critical' ? 'bg-rose-500' : level === 'moderate' ? 'bg-amber-500' : 'bg-sky-500'
}
</script>

<template>
  <div class="space-y-6">
    <div v-if="loading" class="grid gap-4 sm:grid-cols-2">
      <div v-for="i in 2" :key="i" class="card h-64 animate-pulse rounded-xl bg-slate-100" />
    </div>

    <template v-else>
      <!-- 洞察概览图 -->
      <div class="grid gap-6 xl:grid-cols-3">
        <section class="card xl:col-span-1">
          <header class="border-b border-slate-100 px-5 py-4">
            <h2 class="text-sm font-semibold">严重度分布</h2>
          </header>
          <div class="p-3">
            <EChart :option="severityRoseOption" height="220px" />
          </div>
        </section>
        <section class="card xl:col-span-2">
          <header class="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <h2 class="text-sm font-semibold">痛点频次排行</h2>
            <span class="text-xs text-slate-400">Top 8 · 点击聚类卡联动下方取证</span>
          </header>
          <div class="p-4">
            <EChart :option="frequencyBarOption" height="220px" />
          </div>
        </section>
      </div>

      <!-- 痛点聚类 -->
      <section class="card">
        <header class="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 class="text-sm font-semibold">痛点聚类（{{ clusters.length }}）</h2>
          <span class="text-xs text-slate-400">任务 {{ DEFAULT_TASK_ID }} · bge-m3 多语言聚类</span>
        </header>
        <div class="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">
          <div
            v-for="c in clusters"
            :key="c.cluster_id"
            class="cursor-pointer rounded-xl border p-4 transition-all"
            :class="selectedClusterId === c.cluster_id
              ? 'border-indigo-400 bg-indigo-50/50 shadow-sm ring-2 ring-indigo-100'
              : 'border-slate-200 hover:border-slate-300 hover:shadow-sm'"
            @click="selectedClusterId = c.cluster_id"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <div class="truncate text-sm font-semibold text-slate-800">{{ c.cluster_name }}</div>
                <div class="mt-0.5 text-xs text-slate-400">{{ ISSUE_TYPE_LABEL[c.issue_type] }} · {{ SEVERITY_LABEL[c.severity_level] }}</div>
              </div>
              <span class="shrink-0 rounded-md px-2 py-0.5 text-xs font-bold" :class="{
                'bg-rose-100 text-rose-700': c.severity_level === 'critical',
                'bg-amber-100 text-amber-700': c.severity_level === 'moderate',
                'bg-sky-100 text-sky-700': c.severity_level === 'minor',
              }">
                {{ c.severity_score.toFixed(1) }}
              </span>
            </div>
            <div class="mt-3 flex items-center gap-2 text-xs text-slate-500">
              <div class="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
                <div class="h-full rounded-full" :class="severityColor(c.severity_level)" :style="{ width: `${Math.min(100, c.frequency_ratio * 100)}%` }" />
              </div>
              <span>{{ c.frequency }} 条（{{ (c.frequency_ratio * 100).toFixed(0) }}%）</span>
            </div>
            <div class="mt-3 flex flex-wrap gap-1">
              <span v-for="k in c.keywords.slice(0, 4)" :key="k" class="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600">{{ k }}</span>
            </div>

            <!-- 展开：代表性引用 sample_quotes -->
            <div v-if="selectedClusterId === c.cluster_id && c.sample_quotes.length" class="mt-3 space-y-2 border-t border-indigo-100 pt-3">
              <div class="text-[11px] font-medium text-indigo-500">代表性差评引用</div>
              <blockquote v-for="q in c.sample_quotes.slice(0, 2)" :key="q.review_id" class="rounded-lg bg-white/70 px-3 py-2 text-xs text-slate-600">
                <div class="flex items-center gap-1.5 text-[10px] text-slate-400">
                  <span class="font-medium text-amber-500">{{ '★'.repeat(Math.round(q.rating)) }}</span>
                  <span class="rounded bg-slate-100 px-1 py-px">{{ langLabel[q.language] ?? q.language }}</span>
                </div>
                <p class="mt-1 leading-relaxed line-clamp-2">“{{ q.translated_content }}”</p>
              </blockquote>
              <div class="flex flex-wrap gap-1.5">
                <span v-for="id in c.sample_image_ids" :key="id" class="rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-medium text-indigo-600">📷 {{ id }} 已取证</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 取证 + 评论 -->
      <div class="grid gap-6 xl:grid-cols-2">
        <!-- VLM 取证画廊 -->
        <section class="card">
          <header class="border-b border-slate-100 px-5 py-4">
            <h2 class="text-sm font-semibold">VLM 视觉取证（{{ evidenceByCluster.length }}）</h2>
            <p class="mt-0.5 text-xs text-slate-400">
              Claude Vision 质检买家实拍图 · 当前聚类取证样本优先展示
            </p>
          </header>
          <div class="grid max-h-[640px] grid-cols-2 gap-3 overflow-y-auto p-4">
            <figure v-for="e in evidenceByCluster" :key="e.image_id" class="overflow-hidden rounded-xl border border-slate-200">
              <div class="relative">
                <img :src="e.storage_url" :alt="e.description" class="aspect-[4/3] w-full object-cover" loading="lazy" />
                <span class="absolute left-2 top-2 rounded-md bg-black/60 px-2 py-0.5 text-[11px] font-medium text-white">
                  {{ DEFECT_LABEL[e.defect_category] }} · {{ (e.confidence * 100).toFixed(0) }}%
                </span>
              </div>
              <figcaption class="p-2.5 text-xs text-slate-500">{{ e.description }}</figcaption>
            </figure>
            <div v-if="!evidenceByCluster.length" class="col-span-2 p-8 text-center text-sm text-slate-400">该聚类暂无视觉取证样本</div>
          </div>
        </section>

        <!-- 评论列表 -->
        <section class="card">
          <header class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
            <h2 class="text-sm font-semibold">差评样本（{{ filteredReviews.length }}）</h2>
            <div class="flex flex-wrap items-center gap-2 text-xs">
              <input
                v-model="keyword"
                type="search"
                placeholder="关键词检索…"
                class="w-32 rounded-lg border border-slate-200 px-2 py-1.5 outline-none transition-colors focus:border-indigo-400"
              />
              <select v-model="ratingMin" class="rounded-lg border border-slate-200 px-2 py-1.5 outline-none focus:border-indigo-400">
                <option :value="0">最低星级不限</option>
                <option :value="1">≤1 星</option>
                <option :value="2">≤2 星</option>
                <option :value="3">≤3 星</option>
              </select>
              <select v-model="ratingMax" class="rounded-lg border border-slate-200 px-2 py-1.5 outline-none focus:border-indigo-400">
                <option :value="0">最高星级不限</option>
                <option :value="3">≥3 星</option>
                <option :value="4">≥4 星</option>
              </select>
              <select v-model="language" class="rounded-lg border border-slate-200 px-2 py-1.5 outline-none focus:border-indigo-400">
                <option value="">全部语种</option>
                <option value="en">英文</option>
                <option value="de">德语</option>
                <option value="ja">日语</option>
                <option value="es">西语</option>
              </select>
              <label class="flex cursor-pointer items-center gap-1.5 rounded-lg border border-slate-200 px-2 py-1.5">
                <input v-model="verifiedOnly" type="checkbox" class="accent-indigo-600" />
                <span class="text-slate-600">仅已购</span>
              </label>
            </div>
          </header>
          <div class="max-h-[560px] divide-y divide-slate-100 overflow-y-auto">
            <div v-for="r in filteredReviews" :key="r.review_id" class="px-5 py-4">
              <div class="flex items-center justify-between gap-2">
                <div class="flex items-center gap-2 text-xs">
                  <span class="font-medium text-amber-500">{{ '★'.repeat(Math.round(r.rating)) }}<span class="text-slate-300">{{ '★'.repeat(5 - Math.round(r.rating)) }}</span></span>
                  <span class="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-500">{{ langLabel[r.language] ?? r.language }}</span>
                  <span class="text-slate-400">{{ r.review_date }}</span>
                  <span v-if="r.verified_purchase" class="rounded bg-emerald-50 px-1.5 py-0.5 text-[11px] font-medium text-emerald-600">已购</span>
                </div>
                <span class="text-[11px] text-slate-400">{{ r.helpful_votes }} 人觉得有用</span>
              </div>
              <p class="mt-1.5 text-sm text-slate-700">{{ r.translated_content }}</p>
              <p class="mt-1 text-xs italic text-slate-400" :title="r.content">{{ r.content }}</p>
              <div v-if="r.image_urls.length" class="mt-2 flex gap-1.5">
                <img v-for="u in r.image_urls.slice(0, 3)" :key="u" :src="u" class="size-10 rounded-md object-cover" loading="lazy" />
              </div>
            </div>
            <div v-if="!filteredReviews.length" class="p-8 text-center text-sm text-slate-400">无匹配评论</div>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>
