<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  getAlerts,
  getBacktest,
  getFinancialDecision,
  getProposal,
  runBacktest,
  simulateFinancialApi,
} from '@/api'
import type {
  Alert,
  BacktestResult,
  FinancialDecision,
  FinancialSimulateRequest,
  FinancialSimulateResult,
  Proposal,
} from '@/types'
import type { EChartsOption } from 'echarts'
import EChart from '@/components/charts/EChart.vue'
import { DEFAULT_TASK_ID } from '@/stores/tasks'

const decision = ref<FinancialDecision | null>(null)
const vetoedProposals = ref<Proposal[]>([])
const alerts = ref<Alert[]>([])
const result = ref<FinancialSimulateResult | null>(null)
const running = ref(false)
const backtest = ref<BacktestResult | null>(null)
const backtestRunning = ref(false)

const form = reactive<FinancialSimulateRequest>({
  mold_cost_usd: 8500,
  moq: 2000,
  current_gross_margin: 0.22,
  expected_price_usd: 29.99,
  unit_cost_increase_usd: 0.85,
  expected_payback_months: 8,
  sea_freight_usd_per_cbm: 420,
  package_size_old_cm: [30, 20, 12],
  package_size_new_cm: [26, 18, 9],
  expected_return_rate_reduction: 0.35,
  product_lifecycle_days: 240,
})

onMounted(async () => {
  const [d, a] = await Promise.all([getFinancialDecision(DEFAULT_TASK_ID), getAlerts({ page_size: 10 })])
  decision.value = d
  alerts.value = a.items
  if (d.vetoed_proposal_ids.length) {
    const list = await Promise.all(d.vetoed_proposal_ids.map((id) => getProposal(id).catch(() => null)))
    vetoedProposals.value = list.filter((p): p is Proposal => p !== null)
  }
})

/* ---------- 财务参数调节滑块 ---------- */
type NumberField =
  | 'mold_cost_usd'
  | 'moq'
  | 'current_gross_margin'
  | 'expected_price_usd'
  | 'unit_cost_increase_usd'
  | 'expected_payback_months'
  | 'sea_freight_usd_per_cbm'
  | 'expected_return_rate_reduction'
  | 'product_lifecycle_days'

const sliderFields: { key: NumberField; label: string; min: number; max: number; step: number; fmt: (v: number) => string }[] = [
  { key: 'mold_cost_usd', label: '开模预算 USD', min: 0, max: 30000, step: 500, fmt: (v) => `$${v.toLocaleString('en-US')}` },
  { key: 'moq', label: '首批 MOQ', min: 100, max: 10000, step: 100, fmt: (v) => `${v} 件` },
  { key: 'expected_price_usd', label: '预期售价 USD', min: 5, max: 100, step: 0.5, fmt: (v) => `$${v.toFixed(2)}` },
  { key: 'sea_freight_usd_per_cbm', label: '海运费 USD/CBM', min: 100, max: 1000, step: 10, fmt: (v) => `$${v}` },
  { key: 'expected_payback_months', label: '期望回本月数', min: 1, max: 24, step: 1, fmt: (v) => `${v} 月` },
  { key: 'current_gross_margin', label: '当前毛利率', min: 0.05, max: 0.6, step: 0.01, fmt: (v) => `${(v * 100).toFixed(0)}%` },
  { key: 'unit_cost_increase_usd', label: '单件成本增量 USD', min: 0, max: 5, step: 0.05, fmt: (v) => `$${v.toFixed(2)}` },
  { key: 'expected_return_rate_reduction', label: '预期退货率降幅', min: 0, max: 0.9, step: 0.05, fmt: (v) => `${(v * 100).toFixed(0)}%` },
  { key: 'product_lifecycle_days', label: '品类生命周期（天）', min: 60, max: 540, step: 30, fmt: (v) => `${v} 天` },
]

async function simulate() {
  running.value = true
  try {
    result.value = await simulateFinancialApi({ ...form })
  } finally {
    running.value = false
  }
}

async function triggerBacktest() {
  backtestRunning.value = true
  try {
    const { backtest_id } = await runBacktest(DEFAULT_TASK_ID)
    backtest.value = await getBacktest(backtest_id)
  } finally {
    backtestRunning.value = false
  }
}

function markRead(alert: Alert) {
  alert.is_read = true
}

const curveOption = computed<EChartsOption>(() => {
  const pts = result.value?.payback_curve ?? []
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 44, right: 16, top: 20, bottom: 28 },
    xAxis: {
      type: 'value',
      name: '退货率降幅',
      axisLabel: { color: '#94a3b8', formatter: (v: number) => `${(v * 100).toFixed(0)}%` },
    },
    yAxis: { type: 'value', name: '回本月数', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
    series: [
      {
        type: 'line',
        smooth: true,
        data: pts.map((p) => [p.return_rate_reduction, p.payback_months]),
        itemStyle: { color: '#6366f1' },
        lineStyle: { width: 2 },
      },
    ],
  }
})

const alertColor: Record<string, string> = {
  high: 'bg-rose-500',
  medium: 'bg-amber-500',
  low: 'bg-slate-400',
}

function fmtUsd(v: number): string {
  return `$${v.toLocaleString('en-US', { maximumFractionDigits: 2 })}`
}
</script>

<template>
  <div class="space-y-6">
    <!-- 模拟器 -->
    <section class="card">
      <header class="border-b border-slate-100 px-5 py-4">
        <h2 class="text-sm font-semibold">逆向财务模拟器</h2>
        <p class="mt-0.5 text-xs text-slate-400">输入成本与箱规参数，沙盒复算 FBA 节省、回本周期与风控结论</p>
      </header>
      <div class="grid gap-6 p-5 lg:grid-cols-2">
        <form class="grid gap-4" @submit.prevent="simulate">
          <label v-for="f in sliderFields" :key="f.key" class="block">
            <span class="flex items-center justify-between text-xs text-slate-500">
              {{ f.label }}
              <span class="rounded bg-indigo-50 px-1.5 py-0.5 font-mono font-medium text-indigo-600">{{ f.fmt(form[f.key]) }}</span>
            </span>
            <input
              v-model.number="form[f.key]"
              type="range"
              :min="f.min"
              :max="f.max"
              :step="f.step"
              class="mt-1.5 w-full accent-indigo-600"
            />
          </label>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <span class="text-xs text-slate-500">改造前箱规 cm（L×W×H）</span>
              <div class="mt-1 flex items-center gap-1.5">
                <input v-model.number="form.package_size_old_cm[0]" type="number" class="w-full rounded-lg border border-slate-200 px-2 py-2 text-sm outline-none focus:border-indigo-400" />
                <span class="text-slate-400">×</span>
                <input v-model.number="form.package_size_old_cm[1]" type="number" class="w-full rounded-lg border border-slate-200 px-2 py-2 text-sm outline-none focus:border-indigo-400" />
                <span class="text-slate-400">×</span>
                <input v-model.number="form.package_size_old_cm[2]" type="number" class="w-full rounded-lg border border-slate-200 px-2 py-2 text-sm outline-none focus:border-indigo-400" />
              </div>
            </div>
            <div>
              <span class="text-xs text-slate-500">改造后箱规 cm（L×W×H）</span>
              <div class="mt-1 flex items-center gap-1.5">
                <input v-model.number="form.package_size_new_cm[0]" type="number" class="w-full rounded-lg border border-slate-200 px-2 py-2 text-sm outline-none focus:border-indigo-400" />
                <span class="text-slate-400">×</span>
                <input v-model.number="form.package_size_new_cm[1]" type="number" class="w-full rounded-lg border border-slate-200 px-2 py-2 text-sm outline-none focus:border-indigo-400" />
                <span class="text-slate-400">×</span>
                <input v-model.number="form.package_size_new_cm[2]" type="number" class="w-full rounded-lg border border-slate-200 px-2 py-2 text-sm outline-none focus:border-indigo-400" />
              </div>
            </div>
          </div>

          <button
            type="submit"
            class="rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:opacity-60"
            :disabled="running"
          >
            {{ running ? '计算中…' : '运行财务模拟' }}
          </button>
        </form>

        <!-- 结果 -->
        <div class="space-y-3">
          <template v-if="result">
            <div class="flex flex-wrap items-center gap-2">
              <span class="rounded-md px-2.5 py-1 text-sm font-semibold" :class="result.veto_status === 'PASSED' ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'">
                {{ result.veto_status === 'PASSED' ? 'PASSED 通过' : 'VETOED 熔断' }}
              </span>
              <span class="text-xs text-slate-400">ROI {{ result.roi }}x · 回本 {{ result.payback_months }} 个月</span>
            </div>

            <div class="grid grid-cols-2 gap-3 text-xs">
              <div class="rounded-lg bg-slate-50 p-3">
                <div class="text-slate-400">体积重 旧→新</div>
                <div class="mt-1 font-medium text-slate-700">{{ result.volumetric_weight_old_kg }}kg → {{ result.volumetric_weight_new_kg }}kg</div>
              </div>
              <div class="rounded-lg bg-slate-50 p-3">
                <div class="text-slate-400">FBA 档位 旧→新</div>
                <div class="mt-1 font-medium text-slate-700">{{ result.fba_tier_old }} → {{ result.fba_tier_new }}</div>
              </div>
              <div class="rounded-lg bg-slate-50 p-3">
                <div class="text-slate-400">单件履约节省</div>
                <div class="mt-1 font-medium text-emerald-600">{{ fmtUsd(result.fulfillment_saving_usd_per_unit) }}</div>
              </div>
              <div class="rounded-lg bg-slate-50 p-3">
                <div class="text-slate-400">月利润增量</div>
                <div class="mt-1 font-medium text-emerald-600">{{ fmtUsd(result.monthly_profit_delta_usd) }}</div>
              </div>
            </div>

            <div v-if="result.veto_reasons.length" class="rounded-lg border border-rose-200 bg-rose-50 p-3">
              <div class="text-xs font-semibold text-rose-700">否决原因</div>
              <ul class="mt-1 list-disc space-y-1 pl-4 text-xs text-rose-600">
                <li v-for="(r, i) in result.veto_reasons" :key="i">{{ r }}</li>
              </ul>
            </div>
            <div v-if="result.fallback_suggestions.length" class="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <div class="text-xs font-semibold text-amber-700">免开模替代建议</div>
              <ul class="mt-1 list-disc space-y-1 pl-4 text-xs text-amber-600">
                <li v-for="(r, i) in result.fallback_suggestions" :key="i">{{ r }}</li>
              </ul>
            </div>

            <EChart :option="curveOption" :height="'180px'" />
          </template>
          <div v-else class="grid h-full place-items-center rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-400">
            填写左侧参数后运行模拟，查看回本曲线与风控结论
          </div>
        </div>
      </div>
    </section>

    <!-- 决策摘要 + 回测 -->
    <div class="grid gap-6 lg:grid-cols-2">
      <section class="card">
        <header class="border-b border-slate-100 px-5 py-4">
          <h2 class="text-sm font-semibold">任务级财务决策</h2>
        </header>
        <div class="p-5">
          <template v-if="decision">
            <div
              class="mb-4 flex items-center gap-2 rounded-lg border px-3 py-2.5 text-xs font-medium"
              :class="decision.veto_status === 'PASSED' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-rose-200 bg-rose-50 text-rose-700'"
            >
              <span class="size-2 shrink-0 rounded-full" :class="decision.veto_status === 'PASSED' ? 'bg-emerald-500' : 'bg-rose-500'" />
              {{ decision.veto_status === 'PASSED' ? '熔断决议 PASSED：财务指标健康，可进入开模流程' : '熔断决议 VETOED：已触发财务熔断，建议执行免开模替代方案' }}
            </div>

            <div class="grid grid-cols-2 gap-3 text-xs sm:grid-cols-3">
              <div class="rounded-lg bg-slate-50 p-3">
                <div class="text-slate-400">审核提案</div>
                <div class="mt-1 text-sm font-semibold text-slate-800">{{ decision.checked_proposals }} 条</div>
              </div>
              <div class="rounded-lg bg-slate-50 p-3">
                <div class="text-slate-400">否决提案</div>
                <div class="mt-1 text-sm font-semibold text-rose-600">{{ decision.vetoed_proposal_ids.length }} 条</div>
              </div>
              <div class="rounded-lg bg-slate-50 p-3">
                <div class="text-slate-400">重试次数</div>
                <div class="mt-1 text-sm font-semibold text-slate-800">{{ decision.retry_count }}</div>
              </div>
            </div>

            <div v-if="decision.veto_reasons.length" class="mt-3 rounded-lg border border-rose-200 bg-rose-50 p-3">
              <div class="text-xs font-semibold text-rose-700">熔断原因</div>
              <ul class="mt-1 list-disc space-y-1 pl-4 text-xs text-rose-600">
                <li v-for="(r, i) in decision.veto_reasons" :key="i">{{ r }}</li>
              </ul>
            </div>

            <ul v-if="vetoedProposals.length" class="mt-3 space-y-2">
              <li v-for="p in vetoedProposals" :key="p.proposal_id" class="rounded-lg border border-rose-100 bg-rose-50/50 p-3">
                <div class="flex items-center justify-between gap-2">
                  <span class="text-xs font-medium text-slate-700">{{ p.title }}</span>
                  <span class="shrink-0 rounded bg-rose-100 px-1.5 py-0.5 text-[11px] font-medium text-rose-600">VETOED</span>
                </div>
                <div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-slate-500">
                  <span>开模 ${{ p.cost_estimation_usd.toLocaleString('en-US') }}</span>
                  <span>ROI {{ p.estimated_roi }}x</span>
                  <span>{{ p.track_type }}</span>
                </div>
                <p v-if="p.veto_reason" class="mt-1 text-[11px] leading-relaxed text-rose-600">{{ p.veto_reason }}</p>
              </li>
            </ul>

            <p class="mt-3 text-xs text-slate-400">
              约束：MOQ {{ decision.financial_constraint.moq }} · 期望回本 {{ decision.financial_constraint.expected_payback_months }} 个月 · 当前毛利 {{ (decision.financial_constraint.current_gross_margin * 100).toFixed(0) }}%
            </p>
          </template>
        </div>
      </section>

      <section class="card">
        <header class="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 class="text-sm font-semibold">历史回测</h2>
          <button
            class="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            :disabled="backtestRunning"
            @click="triggerBacktest"
          >
            {{ backtestRunning ? '运行中…' : backtest ? '重新运行' : '运行回测' }}
          </button>
        </header>
        <div class="p-5">
          <template v-if="backtest">
            <div class="flex items-center gap-3">
              <span class="text-3xl font-bold text-indigo-600">{{ (backtest.accuracy_score * 100).toFixed(0) }}%</span>
              <div class="text-xs text-slate-400">
                <div>回测切片 {{ backtest.slice_date }}</div>
                <div>聚类命中准确率</div>
              </div>
            </div>
            <div class="mt-4 space-y-2">
              <div v-for="v in backtest.cluster_verdicts" :key="v.cluster_id" class="flex items-start gap-2 rounded-lg bg-slate-50 p-3 text-xs">
                <span class="mt-0.5 rounded px-1.5 py-0.5 font-medium" :class="v.hit ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'">
                  {{ v.hit ? '命中' : '未中' }}
                </span>
                <div>
                  <div class="font-medium text-slate-700">{{ v.cluster_name }}</div>
                  <div class="mt-0.5 text-slate-500">{{ v.actual_trend }}</div>
                </div>
              </div>
            </div>
          </template>
          <div v-else class="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-400">
            对已完成任务的聚类结论做历史切片验证，量化误报率
          </div>
        </div>
      </section>
    </div>

    <!-- 告警中心 -->
    <section class="card">
      <header class="border-b border-slate-100 px-5 py-4">
        <h2 class="text-sm font-semibold">告警中心（{{ alerts.length }}）</h2>
      </header>
      <div class="divide-y divide-slate-100">
        <div v-for="a in alerts" :key="a.alert_id" class="flex items-start gap-3 px-5 py-3.5">
          <span class="mt-1.5 size-2 shrink-0 rounded-full" :class="alertColor[a.severity]" />
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-sm font-medium text-slate-700" :class="{ 'opacity-60': a.is_read }">{{ a.title }}</span>
              <span v-if="!a.is_read" class="rounded bg-rose-50 px-1.5 py-0.5 text-[11px] font-medium text-rose-600">未读</span>
            </div>
            <p class="mt-0.5 text-xs text-slate-500">{{ a.message }}</p>
          </div>
          <button v-if="!a.is_read" class="shrink-0 text-xs text-indigo-600 hover:underline" @click="markRead(a)">标为已读</button>
        </div>
      </div>
    </section>
  </div>
</template>
