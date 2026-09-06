<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getCrossPlatformMapping, getPriceHistory, listProducts } from '@/api'
import type { CrossPlatformMapping, Product } from '@/types'
import type { EChartsOption } from 'echarts'
import EChart from '@/components/charts/EChart.vue'

const products = ref<Product[]>([])
const loading = ref(true)
const keyword = ref('')
const selectedId = ref<string | null>(null)
const mappings = ref<CrossPlatformMapping[]>([])
const historyPoints = ref<{ ts: string; price: number; bsr: number; buy_box_price: number; has_coupon: boolean }[]>([])

onMounted(async () => {
  const [res, mp] = await Promise.all([listProducts({ page_size: 50 }), getCrossPlatformMapping()])
  products.value = res.items
  mappings.value = mp.items
  loading.value = false
  if (res.items.length) select(res.items[0].product_id)
})

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return products.value
  return products.value.filter(
    (p) => p.title.toLowerCase().includes(kw) || p.asin.toLowerCase().includes(kw),
  )
})

async function select(productId: string) {
  selectedId.value = productId
  const res = await getPriceHistory(productId)
  historyPoints.value = res.points
}

const selectedProduct = computed(() => products.value.find((p) => p.product_id === selectedId.value))

const selectedMapping = computed<CrossPlatformMapping | null>(() => {
  if (!selectedId.value) return null
  return mappings.value.find((m) => m.product_id === selectedId.value) ?? null
})

/* ---------- 多币种换算 ---------- */
const FX: Record<string, number> = { USD: 1, EUR: 1.08, GBP: 1.27, JPY: 0.0067, CAD: 0.73, AUD: 0.65, MXN: 0.058 }

const priceUsd = computed(() => {
  const p = selectedProduct.value
  if (!p) return 0
  const rate = FX[p.currency] ?? 1
  return p.current_price * rate
})

/* ---------- 抛重测算 ---------- */
const volumetric = computed(() => {
  const p = selectedProduct.value
  if (!p?.length_cm || !p.width_cm || !p.height_cm || p.weight_kg == null) return null
  const dim = p.length_cm * p.width_cm * p.height_cm
  const v6000 = dim / 6000
  const v5000 = dim / 5000
  const chargeable = Math.max(p.weight_kg, v6000)
  return {
    v6000,
    v5000,
    chargeable,
    oversized: v6000 > p.weight_kg,
    surchargeRate: (chargeable / p.weight_kg - 1) * 100,
  }
})

const priceOption = computed<EChartsOption>(() => {
  const dates = historyPoints.value.map((p) => p.ts.slice(0, 10))
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['售价', 'Buy Box', 'BSR'], top: 0 },
    grid: { left: 40, right: 16, top: 36, bottom: 24 },
    xAxis: { type: 'category', data: dates, axisLabel: { color: '#94a3b8' } },
    yAxis: [
      { type: 'value', name: 'USD', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
      { type: 'value', name: 'BSR', axisLabel: { color: '#94a3b8' }, splitLine: { show: false } },
    ],
    series: [
      { name: '售价', type: 'line', smooth: true, data: historyPoints.value.map((p) => p.price), itemStyle: { color: '#6366f1' }, areaStyle: { opacity: 0.08, color: '#6366f1' } },
      { name: 'Buy Box', type: 'line', smooth: true, data: historyPoints.value.map((p) => p.buy_box_price), itemStyle: { color: '#14b8a6' } },
      { name: 'BSR', type: 'line', smooth: true, yAxisIndex: 1, data: historyPoints.value.map((p) => p.bsr), itemStyle: { color: '#f59e0b' }, showSymbol: false },
    ],
  }
})

const rateColor = (r: number) => (r >= 4.0 ? 'text-emerald-600' : r >= 3.5 ? 'text-amber-600' : 'text-rose-600')
</script>

<template>
  <div class="space-y-6">
    <!-- 筛选栏 -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <input
        v-model="keyword"
        type="text"
        placeholder="搜索标题 / ASIN…"
        class="w-64 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
      />
      <span class="text-xs text-slate-400">共 {{ filtered.length }} 个监控商品</span>
    </div>

    <div class="grid gap-6 lg:grid-cols-3">
      <!-- 商品列表 -->
      <div class="card lg:col-span-1">
        <div class="max-h-[640px] divide-y divide-slate-100 overflow-y-auto">
          <div v-if="loading" v-for="i in 5" :key="i" class="flex animate-pulse items-center gap-3 px-4 py-3">
            <div class="size-11 shrink-0 rounded-lg bg-slate-200" />
            <div class="flex-1 space-y-2">
              <div class="h-3 w-3/4 rounded bg-slate-200" />
              <div class="h-2.5 w-1/2 rounded bg-slate-200" />
            </div>
          </div>
          <button
            v-for="p in filtered"
            :key="p.product_id"
            class="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors"
            :class="selectedId === p.product_id ? 'bg-indigo-50/70' : 'hover:bg-slate-50'"
            @click="select(p.product_id)"
          >
            <img :src="p.main_image_url" :alt="p.title" class="size-11 shrink-0 rounded-lg object-cover" loading="lazy" />
            <div class="min-w-0 flex-1">
              <div class="truncate text-sm font-medium text-slate-800">{{ p.title }}</div>
              <div class="mt-0.5 flex items-center gap-2 text-xs text-slate-400">
                <span class="font-mono">{{ p.asin }}</span>
                <span>{{ p.marketplace }}</span>
              </div>
              <div class="mt-1 flex items-center gap-2 text-xs">
                <span class="font-semibold" :class="rateColor(p.avg_rating)">{{ p.avg_rating.toFixed(1) }} ★</span>
                <span class="text-slate-400">{{ p.review_count }} 条评论</span>
              </div>
            </div>
            <span class="shrink-0 text-sm font-semibold text-slate-700">{{ p.currency === 'EUR' ? '€' : '$' }}{{ p.current_price.toFixed(2) }}</span>
          </button>
        </div>
      </div>

      <!-- 详情 -->
      <div class="card lg:col-span-2">
        <template v-if="loading">
          <div class="flex animate-pulse flex-col gap-4 p-5 sm:flex-row sm:items-start sm:gap-4">
            <div class="size-20 shrink-0 rounded-xl bg-slate-200" />
            <div class="min-w-0 flex-1 space-y-3">
              <div class="h-4 w-2/3 rounded bg-slate-200" />
              <div class="h-3 w-1/3 rounded bg-slate-200" />
              <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <div v-for="i in 4" :key="i" class="h-12 rounded-lg bg-slate-100" />
              </div>
            </div>
          </div>
          <div class="m-5 h-64 animate-pulse rounded-xl bg-slate-100" />
        </template>
        <template v-else-if="selectedProduct">
          <div class="flex items-start gap-4 border-b border-slate-100 p-5">
            <img :src="selectedProduct.main_image_url" :alt="selectedProduct.title" class="size-20 rounded-xl object-cover" />
            <div class="min-w-0 flex-1">
              <h3 class="text-base font-semibold text-slate-800">{{ selectedProduct.title }}</h3>
              <p class="mt-1 text-xs text-slate-400">
                {{ selectedProduct.category }} · BSR {{ selectedProduct.bsr }}
                <span v-if="selectedProduct.bsr_category">（{{ selectedProduct.bsr_category }}）</span>
              </p>
              <div class="mt-2 flex flex-wrap items-center gap-2 text-sm">
                <span class="text-lg font-bold text-slate-800">
                  {{ selectedProduct.currency === 'EUR' ? '€' : selectedProduct.currency === 'GBP' ? '£' : selectedProduct.currency === 'JPY' ? '¥' : '$' }}{{ selectedProduct.current_price.toFixed(2) }}
                </span>
                <span class="rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-600">
                  ≈ ${{ priceUsd.toFixed(2) }} USD
                </span>
              </div>
              <div class="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
                <div class="rounded-lg bg-slate-50 p-2.5">
                  <div class="text-slate-400">尺寸 cm</div>
                  <div class="mt-0.5 font-medium text-slate-700">
                    {{ selectedProduct.length_cm }}×{{ selectedProduct.width_cm }}×{{ selectedProduct.height_cm }}
                  </div>
                </div>
                <div class="rounded-lg bg-slate-50 p-2.5">
                  <div class="text-slate-400">重量 kg</div>
                  <div class="mt-0.5 font-medium text-slate-700">{{ selectedProduct.weight_kg }}</div>
                </div>
                <div class="rounded-lg bg-slate-50 p-2.5">
                  <div class="text-slate-400">评分</div>
                  <div class="mt-0.5 font-medium text-slate-700">{{ selectedProduct.avg_rating }} / 5</div>
                </div>
                <div class="rounded-lg bg-slate-50 p-2.5">
                  <div class="text-slate-400">评论数</div>
                  <div class="mt-0.5 font-medium text-slate-700">{{ selectedProduct.review_count }}</div>
                </div>
              </div>

              <!-- 抛重测算 -->
              <div v-if="volumetric" class="mt-3 rounded-lg border p-3" :class="volumetric.oversized ? 'border-amber-200 bg-amber-50/60' : 'border-emerald-200 bg-emerald-50/60'">
                <div class="flex items-center justify-between text-xs">
                  <span class="font-medium" :class="volumetric.oversized ? 'text-amber-700' : 'text-emerald-700'">
                    {{ volumetric.oversized ? '⚠ 已触发抛重（体积重 > 实重）' : '✓ 未抛重（实重计费）' }}
                  </span>
                  <span class="text-slate-400">计费重量 {{ volumetric.chargeable.toFixed(2) }} kg</span>
                </div>
                <div class="mt-1.5 flex flex-wrap gap-1.5 text-[11px]">
                  <span class="rounded bg-white/80 px-1.5 py-0.5 text-slate-600">实重 {{ selectedProduct.weight_kg }} kg</span>
                  <span class="rounded bg-white/80 px-1.5 py-0.5 text-slate-600">体积重 /6000 {{ volumetric.v6000.toFixed(2) }} kg</span>
                  <span class="rounded bg-white/80 px-1.5 py-0.5 text-slate-600">体积重 /5000 {{ volumetric.v5000.toFixed(2) }} kg</span>
                  <span v-if="volumetric.oversized" class="rounded bg-amber-100 px-1.5 py-0.5 font-medium text-amber-700">
                    运费成本 ↑ {{ volumetric.surchargeRate.toFixed(0) }}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div class="p-5">
            <h4 class="mb-3 text-sm font-semibold text-slate-700">近 90 天价格 / BSR 走势</h4>
            <EChart :option="priceOption" :height="'320px'" />

            <!-- 跨平台 SKU 映射 -->
            <template v-if="selectedMapping">
              <h4 class="mb-1 mt-6 text-sm font-semibold text-slate-700">跨平台 SKU 映射与套利空间</h4>
              <p class="mb-3 text-xs text-slate-400">
                Amazon 售价 ${{ selectedMapping.amazon_price_usd.toFixed(2) }} · 跨平台最大价差
                <span class="font-medium text-emerald-600">${{ selectedMapping.max_price_gap_usd.toFixed(2) }}</span>
              </p>
              <div class="overflow-x-auto rounded-xl border border-slate-200">
                <table class="w-full min-w-[560px] text-left text-xs">
                  <thead class="border-b border-slate-100 bg-slate-50 text-slate-400">
                    <tr>
                      <th class="px-3 py-2 font-medium">平台</th>
                      <th class="px-3 py-2 font-medium">外部 SKU</th>
                      <th class="px-3 py-2 font-medium">售价 USD</th>
                      <th class="px-3 py-2 font-medium">匹配度</th>
                      <th class="px-3 py-2 font-medium">佣金 / 履约</th>
                      <th class="px-3 py-2 font-medium">价差</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-50">
                    <tr v-for="m in selectedMapping.matches" :key="`${m.platform}-${m.external_sku}`" class="hover:bg-slate-50/60">
                      <td class="px-3 py-2.5 font-medium text-slate-700">{{ m.platform }}</td>
                      <td class="px-3 py-2.5 font-mono text-slate-500">{{ m.external_sku }}</td>
                      <td class="px-3 py-2.5 text-slate-700">${{ m.price_usd.toFixed(2) }}</td>
                      <td class="px-3 py-2.5">
                        <span class="rounded-md px-1.5 py-0.5 font-medium" :class="m.match_score >= 0.9 ? 'bg-emerald-50 text-emerald-700' : m.match_score >= 0.8 ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-600'">
                          {{ (m.match_score * 100).toFixed(0) }}%
                        </span>
                      </td>
                      <td class="px-3 py-2.5 text-slate-500">
                        <span class="font-medium text-rose-500">-{{ m.commission_usd.toFixed(2) }}</span>
                        <span class="text-slate-300"> / </span>
                        <span class="font-medium text-slate-600">{{ m.fulfillment_usd.toFixed(2) }}</span>
                      </td>
                      <td class="px-3 py-2.5">
                        <span class="font-semibold" :class="selectedMapping.amazon_price_usd - m.price_usd > 0 ? 'text-emerald-600' : 'text-slate-400'">
                          {{ selectedMapping.amazon_price_usd - m.price_usd >= 0 ? '+' : '' }}{{ (selectedMapping.amazon_price_usd - m.price_usd).toFixed(2) }}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </div>
        </template>
        <div v-else class="p-10 text-center text-sm text-slate-400">无匹配商品</div>
      </div>
    </div>
  </div>
</template>
