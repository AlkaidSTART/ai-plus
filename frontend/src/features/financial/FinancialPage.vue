<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  AlertTriangle,
  Calculator,
  CheckCircle2,
  FileCheck2,
  HelpCircle,
  Percent,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from '@lucide/vue'
import EmptyState from '@/components/EmptyState.vue'
import FinancialStateBadge from '@/components/FinancialStateBadge.vue'
import KpiCard from '@/components/KpiCard.vue'
import VChart from '@/components/VChart.vue'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
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
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { EChartsCoreOption } from 'echarts/core'
import type { FinancialEvaluateRequest, FinancialEvaluateResponse } from '@/api/client'
import {
  useEvaluateFinancial,
  useFinancialRules,
  useSaveTaskItemFinancial,
} from '@/composables/useFinancial'
import { useTaskDetail, useTaskList } from '@/composables/useTasks'

/**
 * 逆向财务风控与熔断（PRD 5.4 & P1-02）。
 * 遵循版本化确定性公式，把控开模与供应链资金链风险。
 * 前端不自行重算裁决逻辑；缺失关键输入时恒为 NOT_EVALUATED。
 */

// 任务关联选择
const { data: taskPage } = useTaskList({ limit: 10 })
const selectedTaskId = ref<string>('sandbox')
const { data: taskDetail } = useTaskDetail(
  computed(() => (selectedTaskId.value !== 'sandbox' ? selectedTaskId.value : null)),
)
const availableItems = computed(() => taskDetail.value?.items ?? [])
const selectedItemId = ref<string | null>(null)

watch(
  availableItems,
  (items) => {
    if (items.length > 0) {
      selectedItemId.value = items[0].item_id
    } else {
      selectedItemId.value = null
    }
  },
  { immediate: true },
)

// 规则元数据与评测服务
const { data: rulesInfo } = useFinancialRules()
const evaluateMutation = useEvaluateFinancial()
const saveMutation = useSaveTaskItemFinancial()

// 表单响应式参数
const form = reactive<{
  mold_cost?: number
  sample_cost?: number
  moq?: number
  unit_product_cost?: number
  expected_sales_price?: number
  shipping_cost_per_unit?: number
  monthly_estimated_sales?: number
  target_payback_months: number
  category_half_life_months: number
  max_cash_budget?: number
}>({
  mold_cost: 6000,
  sample_cost: 600,
  moq: 1000,
  unit_product_cost: 10,
  expected_sales_price: 36,
  shipping_cost_per_unit: 4.5,
  monthly_estimated_sales: 450,
  target_payback_months: 6,
  category_half_life_months: 12,
  max_cash_budget: 30000,
})

const evalResult = ref<FinancialEvaluateResponse | null>(null)
const isSubmitting = computed(
  () => evaluateMutation.isPending.value || saveMutation.isPending.value,
)
const syncSuccess = ref(false)

// 预设模式
function applyHealthyPreset() {
  form.mold_cost = 5000
  form.sample_cost = 500
  form.moq = 1000
  form.unit_product_cost = 8.5
  form.expected_sales_price = 35.0
  form.shipping_cost_per_unit = 4.0
  form.monthly_estimated_sales = 500
  form.target_payback_months = 6
  form.category_half_life_months = 12
  form.max_cash_budget = 25000
  void runEvaluation()
}

function applyVetoMoldPreset() {
  form.mold_cost = 25000
  form.sample_cost = 2000
  form.moq = 800
  form.unit_product_cost = 12.0
  form.expected_sales_price = 38.0
  form.shipping_cost_per_unit = 5.0
  form.monthly_estimated_sales = 150
  form.target_payback_months = 6
  form.category_half_life_months = 12
  form.max_cash_budget = 40000
  void runEvaluation()
}

function applyVetoMarginPreset() {
  form.mold_cost = 4000
  form.sample_cost = 500
  form.moq = 1000
  form.unit_product_cost = 18.0
  form.expected_sales_price = 22.0
  form.shipping_cost_per_unit = 6.0
  form.monthly_estimated_sales = 300
  form.target_payback_months = 6
  form.category_half_life_months = 12
  form.max_cash_budget = 30000
  void runEvaluation()
}

function resetToNotEvaluated() {
  form.mold_cost = undefined
  form.sample_cost = undefined
  form.moq = undefined
  form.unit_product_cost = undefined
  form.expected_sales_price = undefined
  form.shipping_cost_per_unit = undefined
  form.monthly_estimated_sales = undefined
  form.target_payback_months = 6
  form.category_half_life_months = 12
  form.max_cash_budget = undefined
  void runEvaluation()
}

function applySuggestion(params: Partial<FinancialEvaluateRequest>) {
  if (params.mold_cost !== undefined) form.mold_cost = params.mold_cost
  if (params.sample_cost !== undefined) form.sample_cost = params.sample_cost
  if (params.moq !== undefined) form.moq = params.moq
  if (params.unit_product_cost !== undefined) form.unit_product_cost = params.unit_product_cost
  if (params.expected_sales_price !== undefined) form.expected_sales_price = params.expected_sales_price
  if (params.shipping_cost_per_unit !== undefined) form.shipping_cost_per_unit = params.shipping_cost_per_unit
  if (params.monthly_estimated_sales !== undefined) form.monthly_estimated_sales = params.monthly_estimated_sales
  if (params.target_payback_months !== undefined) form.target_payback_months = params.target_payback_months
  if (params.category_half_life_months !== undefined) form.category_half_life_months = params.category_half_life_months
  if (params.max_cash_budget !== undefined) form.max_cash_budget = params.max_cash_budget
  void runEvaluation()
}

async function runEvaluation() {
  syncSuccess.value = false
  const req: FinancialEvaluateRequest = {
    mold_cost: form.mold_cost,
    sample_cost: form.sample_cost,
    moq: form.moq,
    unit_product_cost: form.unit_product_cost,
    expected_sales_price: form.expected_sales_price,
    shipping_cost_per_unit: form.shipping_cost_per_unit,
    monthly_estimated_sales: form.monthly_estimated_sales,
    target_payback_months: form.target_payback_months,
    category_half_life_months: form.category_half_life_months,
    max_cash_budget: form.max_cash_budget,
    currency: 'USD',
  }
  const res = await evaluateMutation.mutateAsync(req)
  evalResult.value = res
}

async function saveToCurrentReport() {
  if (selectedTaskId.value === 'sandbox' || !selectedItemId.value) return
  const req: FinancialEvaluateRequest = {
    mold_cost: form.mold_cost,
    sample_cost: form.sample_cost,
    moq: form.moq,
    unit_product_cost: form.unit_product_cost,
    expected_sales_price: form.expected_sales_price,
    shipping_cost_per_unit: form.shipping_cost_per_unit,
    monthly_estimated_sales: form.monthly_estimated_sales,
    target_payback_months: form.target_payback_months,
    category_half_life_months: form.category_half_life_months,
    max_cash_budget: form.max_cash_budget,
    currency: 'USD',
    task_id: selectedTaskId.value,
    item_id: selectedItemId.value,
  }
  const res = await saveMutation.mutateAsync({
    taskId: selectedTaskId.value,
    itemId: selectedItemId.value,
    body: req,
  })
  evalResult.value = res
  syncSuccess.value = true
}

onMounted(() => {
  void runEvaluation()
})

// ECharts 动态盈亏平衡折线图
const chartOption = computed<EChartsCoreOption | null>(() => {
  if (!evalResult.value || !evalResult.value.break_even_timeline.length) return null
  const timeline = evalResult.value.break_even_timeline
  const months = timeline.map((d) => `第${d.month}月`)
  const revenue = timeline.map((d) => d.cumulative_revenue)
  const cost = timeline.map((d) => d.cumulative_cost)
  const netCash = timeline.map((d) => d.net_cashflow)

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        if (!Array.isArray(params) || params.length === 0) return ''
        const m = params[0].axisValue
        let html = `<div class="font-medium mb-1">${m}</div>`
        params.forEach((item: any) => {
          html += `<div class="flex items-center justify-between gap-4 text-xs">
            <span style="color:${item.color}">● ${item.seriesName}</span>
            <span class="font-mono font-medium">$${Number(item.value).toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
          </div>`
        })
        return html
      },
    },
    legend: {
      data: ['累计收入', '累计发生总成本', '累计净现金流'],
      top: 0,
      textStyle: { fontSize: 12 },
    },
    grid: {
      top: 40,
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: months,
      axisLine: { lineStyle: { color: '#94a3b8' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: (val: number) => `$${val >= 1000 ? `${(val / 1000).toFixed(0)}k` : val}`,
      },
      splitLine: { lineStyle: { strokeDasharray: '3 3', color: '#e2e8f0' } },
    },
    series: [
      {
        name: '累计收入',
        type: 'line',
        smooth: true,
        data: revenue,
        itemStyle: { color: '#059669' },
        lineStyle: { width: 2 },
      },
      {
        name: '累计发生总成本',
        type: 'line',
        smooth: true,
        data: cost,
        itemStyle: { color: '#DC2626' },
        lineStyle: { width: 2, type: 'dashed' },
      },
      {
        name: '累计净现金流',
        type: 'line',
        smooth: true,
        data: netCash,
        itemStyle: { color: '#2563EB' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(37,99,235,0.25)' },
              { offset: 1, color: 'rgba(37,99,235,0.02)' },
            ],
          },
        },
        lineStyle: { width: 2.5 },
      },
    ],
  }
})
</script>

<template>
  <div class="mx-auto w-full max-w-[1440px] space-y-6 p-4 lg:p-6">
    <!-- 顶栏标题与上下文联动 -->
    <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between animate-enter">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">财务风控与逆向熔断</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          工业级逆向财务否决引擎（PRD P1）：遵循版本化确定性公式，把控开模与现金流安全。
        </p>
      </div>

      <!-- 快捷预设与任务绑定 -->
      <div class="flex flex-wrap items-center gap-2">
        <div class="flex items-center gap-2 text-xs text-muted-foreground">
          <span>测算上下文:</span>
          <Select v-model="selectedTaskId">
            <SelectTrigger class="h-8 w-44 text-xs">
              <SelectValue placeholder="选择任务上下文" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="sandbox">独立仿真沙盘</SelectItem>
              <SelectItem
                v-for="t in taskPage?.items ?? []"
                :key="t.task_id"
                :value="t.task_id"
              >
                任务 {{ t.task_id.slice(0, 8) }} ({{ t.status }})
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Button
          v-if="selectedTaskId !== 'sandbox' && selectedItemId"
          variant="outline"
          size="sm"
          class="h-8 text-xs gap-1"
          :disabled="isSubmitting"
          @click="saveToCurrentReport"
        >
          <FileCheck2 class="size-3.5 text-primary" />
          同步决策至报告
        </Button>
      </div>
    </div>

    <!-- 预设快速切换栏 -->
    <div class="flex flex-wrap items-center gap-2 text-xs animate-enter" :style="{ animationDelay: '40ms' }">
      <span class="text-muted-foreground">快速案例预设:</span>
      <Button variant="secondary" size="sm" class="h-7 text-xs" @click="applyHealthyPreset">
        稳健通过用例
      </Button>
      <Button variant="secondary" size="sm" class="h-7 text-xs text-destructive hover:bg-destructive/10" @click="applyVetoMoldPreset">
        开模分摊超标熔断
      </Button>
      <Button variant="secondary" size="sm" class="h-7 text-xs text-destructive hover:bg-destructive/10" @click="applyVetoMarginPreset">
        负毛利倒挂熔断
      </Button>
      <Button variant="ghost" size="sm" class="h-7 text-xs text-muted-foreground" @click="resetToNotEvaluated">
        <RotateCcw class="size-3 mr-1" />
        恢复未评估态
      </Button>
    </div>

    <!-- 状态同步成功提示 -->
    <Alert v-if="syncSuccess" class="border-emerald-200 bg-emerald-50 text-emerald-900 animate-enter">
      <CheckCircle2 class="size-4 text-emerald-600" />
      <AlertTitle>决策同步完成</AlertTitle>
      <AlertDescription>
        已将当前财务裁决（{{ evalResult?.financial_state }}）与指标持久化至任务报告中。
      </AlertDescription>
    </Alert>

    <!-- 熔断决议状态区 (Veto Banner) -->
    <div class="animate-enter" :style="{ animationDelay: '80ms' }">
      <!-- 1. NOT_EVALUATED 状态 -->
      <Alert
        v-if="!evalResult || evalResult.financial_state === 'NOT_EVALUATED'"
        class="border-dashed border-slate-300 bg-slate-50/50"
      >
        <HelpCircle class="size-5 text-slate-500" />
        <AlertTitle class="flex items-center gap-2 text-slate-800 font-semibold">
          财务裁决状态
          <FinancialStateBadge state="NOT_EVALUATED" />
        </AlertTitle>
        <AlertDescription class="mt-2 space-y-1 text-slate-600 text-xs sm:text-sm">
          <p>
            当前处于「未评估」状态：由于缺少开模预算、MOQ、单位采购成本或售价等必要输入参数，
            系统未执行确定性财务否决。
          </p>
          <p class="text-xs text-slate-500">
            * 遵循 PRD 规范：未执行财务评估不等于通过，亦不代表 0 收益或免于风险审查。请填入参数进行测算。
          </p>
        </AlertDescription>
      </Alert>

      <!-- 2. PASSED 状态 -->
      <Alert
        v-else-if="evalResult.financial_state === 'PASSED'"
        class="border-emerald-200 bg-emerald-50/70 text-emerald-950"
      >
        <ShieldCheck class="size-5 text-emerald-600" />
        <AlertTitle class="flex items-center gap-2 text-emerald-900 font-semibold">
          财务准入审查结论
          <FinancialStateBadge state="PASSED" />
        </AlertTitle>
        <AlertDescription class="mt-2 space-y-2 text-emerald-900 text-xs sm:text-sm">
          <p v-for="(reason, idx) in evalResult.reasons" :key="idx">
            {{ reason }}
          </p>
          <div class="flex flex-wrap gap-2 pt-1 text-xs text-emerald-700">
            <span class="rounded bg-emerald-100/80 px-2 py-0.5">规则版本: {{ evalResult.rule_version }}</span>
            <span class="rounded bg-emerald-100/80 px-2 py-0.5">计价币种: {{ evalResult.currency }}</span>
            <span class="rounded bg-emerald-100/80 px-2 py-0.5">静态回本: {{ evalResult.metrics?.payback_months }} 个月</span>
          </div>
        </AlertDescription>
      </Alert>

      <!-- 3. VETOED 熔断状态 -->
      <Alert
        v-else-if="evalResult.financial_state === 'VETOED'"
        variant="destructive"
        class="border-red-300 bg-red-50/80 text-red-950"
      >
        <ShieldAlert class="size-5 text-red-600" />
        <AlertTitle class="flex items-center gap-2 text-red-900 font-bold">
          触发逆向财务熔断告警
          <FinancialStateBadge state="VETOED" />
        </AlertTitle>
        <AlertDescription class="mt-2 space-y-3 text-xs sm:text-sm">
          <div class="rounded-md border border-red-200 bg-white/80 p-3 space-y-1.5 text-red-900">
            <div class="font-medium flex items-center gap-1.5 text-red-700">
              <AlertTriangle class="size-4" />
              熔断否决理由（公式确定性可复算）：
            </div>
            <ul class="list-disc list-inside space-y-1 pl-1 text-xs sm:text-sm text-red-800">
              <li v-for="(reason, idx) in evalResult.reasons" :key="idx">
                {{ reason }}
              </li>
            </ul>
          </div>

          <!-- 替代建议卡片 (PRD 要求: 提供免开模小改、仅优化包装等替代建议，重新评估仍遵守规则与任务预算) -->
          <div v-if="evalResult.alternative_suggestions.length > 0" class="pt-2">
            <div class="text-xs font-semibold text-red-900 uppercase tracking-wide mb-2 flex items-center gap-1.5">
              <Sparkles class="size-3.5 text-amber-600" />
              工程与供应链替代整改方案（点击一键应用测试）：
            </div>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div
                v-for="alt in evalResult.alternative_suggestions"
                :key="alt.suggestion_id"
                class="rounded-lg border border-red-200 bg-white p-3 shadow-xs space-y-2 flex flex-col justify-between"
              >
                <div>
                  <div class="font-medium text-xs sm:text-sm text-foreground">{{ alt.title }}</div>
                  <p class="text-xs text-muted-foreground mt-1">{{ alt.description }}</p>
                  <div class="text-xs text-emerald-700 font-medium mt-2 bg-emerald-50 rounded p-1.5 border border-emerald-100">
                    {{ alt.estimated_impact }}
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  class="w-full text-xs h-7 mt-2"
                  @click="applySuggestion(alt.suggested_params)"
                >
                  应用此方案重算
                </Button>
              </div>
            </div>
          </div>
        </AlertDescription>
      </Alert>
    </div>

    <!-- 顶栏 KPI 统计行 -->
    <div
      v-if="evalResult?.metrics"
      class="grid grid-cols-2 gap-4 lg:grid-cols-5 animate-enter"
      :style="{ animationDelay: '120ms' }"
    >
      <KpiCard
        label="预估静态回本周期"
        :value="`${evalResult.metrics.payback_months} 个月`"
        :note="`期望上限 ≤ ${form.target_payback_months} 个月`"
      />
      <KpiCard
        label="单件边际贡献 / 毛利"
        :value="`$${evalResult.metrics.unit_contribution_margin.toFixed(2)}`"
        :note="`毛利率 ${evalResult.metrics.gross_margin_rate}%`"
      />
      <KpiCard
        label="首批启动资金需求"
        :value="`$${evalResult.metrics.initial_batch_cash.toLocaleString('en-US')}`"
        :note="`固定投入 $${evalResult.metrics.fixed_costs.toLocaleString('en-US')}`"
      />
      <KpiCard
        label="单件模具分摊比率"
        :value="`${evalResult.metrics.mold_cost_ratio}%`"
        :note="`单件分摊 $${evalResult.metrics.amortized_mold_cost_per_unit.toFixed(2)} (红线 35%)`"
      />
      <KpiCard
        label="12个月预估 ROI"
        :value="`${evalResult.metrics.estimated_12m_roi}%`"
        :note="`月度净贡献 $${evalResult.metrics.monthly_contribution.toLocaleString('en-US')}`"
      />
    </div>

    <!-- 主体两栏布局 -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-enter" :style="{ animationDelay: '160ms' }">
      <!-- 左栏：财务参数调节滑块与输入表单 -->
      <Card class="lg:col-span-5 h-fit">
        <CardHeader>
          <div class="flex items-center justify-between">
            <CardTitle class="text-base font-semibold flex items-center gap-2">
              <Calculator class="size-4 text-primary" />
              财务参数调节与门槛约束
            </CardTitle>
            <Badge variant="outline" class="text-xs">
              {{ evalResult?.currency ?? 'USD' }}
            </Badge>
          </div>
          <CardDescription>
            支持滑动调节或精确输入；保留单位与依据，后端统一按确定性公式重算。
          </CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <!-- 开模预算 -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between text-xs">
              <Label for="mold_cost" class="font-medium">开模预算 (USD)</Label>
              <span class="text-muted-foreground font-mono">
                ${{ form.mold_cost !== undefined ? form.mold_cost.toLocaleString('en-US') : '未设置' }}
              </span>
            </div>
            <div class="flex items-center gap-3">
              <input
                id="mold_cost_range"
                type="range"
                min="0"
                max="50000"
                step="500"
                :value="form.mold_cost ?? 0"
                class="w-full accent-primary h-2 bg-secondary rounded-lg cursor-pointer"
                @input="form.mold_cost = Number(($event.target as HTMLInputElement).value)"
              />
              <Input
                id="mold_cost"
                type="number"
                v-model.number="form.mold_cost"
                class="h-8 w-24 text-xs font-mono"
                placeholder="USD"
              />
            </div>
          </div>

          <!-- 打样成本 -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between text-xs">
              <Label for="sample_cost" class="font-medium">打样及手板成本 (USD)</Label>
              <span class="text-muted-foreground font-mono">
                ${{ form.sample_cost !== undefined ? form.sample_cost.toLocaleString('en-US') : '未设置' }}
              </span>
            </div>
            <div class="flex items-center gap-3">
              <input
                id="sample_cost_range"
                type="range"
                min="0"
                max="5000"
                step="100"
                :value="form.sample_cost ?? 0"
                class="w-full accent-primary h-2 bg-secondary rounded-lg cursor-pointer"
                @input="form.sample_cost = Number(($event.target as HTMLInputElement).value)"
              />
              <Input
                id="sample_cost"
                type="number"
                v-model.number="form.sample_cost"
                class="h-8 w-24 text-xs font-mono"
              />
            </div>
          </div>

          <!-- 首批 MOQ -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between text-xs">
              <Label for="moq" class="font-medium">首批最小起订量 (MOQ, 件)</Label>
              <span class="text-muted-foreground font-mono">
                {{ form.moq !== undefined ? form.moq.toLocaleString('en-US') : '未设置' }} 件
              </span>
            </div>
            <div class="flex items-center gap-3">
              <input
                id="moq_range"
                type="range"
                min="100"
                max="10000"
                step="100"
                :value="form.moq ?? 100"
                class="w-full accent-primary h-2 bg-secondary rounded-lg cursor-pointer"
                @input="form.moq = Number(($event.target as HTMLInputElement).value)"
              />
              <Input
                id="moq"
                type="number"
                v-model.number="form.moq"
                class="h-8 w-24 text-xs font-mono"
              />
            </div>
          </div>

          <!-- 单件生产采购成本 -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between text-xs">
              <Label for="unit_product_cost" class="font-medium">单件生产/采购成本 (USD)</Label>
              <span class="text-muted-foreground font-mono">
                ${{ form.unit_product_cost !== undefined ? form.unit_product_cost.toFixed(2) : '未设置' }}
              </span>
            </div>
            <div class="flex items-center gap-3">
              <input
                id="unit_cost_range"
                type="range"
                min="1"
                max="150"
                step="0.5"
                :value="form.unit_product_cost ?? 1"
                class="w-full accent-primary h-2 bg-secondary rounded-lg cursor-pointer"
                @input="form.unit_product_cost = Number(($event.target as HTMLInputElement).value)"
              />
              <Input
                id="unit_product_cost"
                type="number"
                step="0.5"
                v-model.number="form.unit_product_cost"
                class="h-8 w-24 text-xs font-mono"
              />
            </div>
          </div>

          <!-- 预期售价 -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between text-xs">
              <Label for="expected_sales_price" class="font-medium">预期零售价格 (USD)</Label>
              <span class="text-muted-foreground font-mono">
                ${{ form.expected_sales_price !== undefined ? form.expected_sales_price.toFixed(2) : '未设置' }}
              </span>
            </div>
            <div class="flex items-center gap-3">
              <input
                id="price_range"
                type="range"
                min="5"
                max="300"
                step="1"
                :value="form.expected_sales_price ?? 5"
                class="w-full accent-primary h-2 bg-secondary rounded-lg cursor-pointer"
                @input="form.expected_sales_price = Number(($event.target as HTMLInputElement).value)"
              />
              <Input
                id="expected_sales_price"
                type="number"
                step="1"
                v-model.number="form.expected_sales_price"
                class="h-8 w-24 text-xs font-mono"
              />
            </div>
          </div>

          <!-- 单件海运及履约运费 -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between text-xs">
              <Label for="shipping_cost" class="font-medium">单件海运与履约运费 (USD)</Label>
              <span class="text-muted-foreground font-mono">
                ${{ form.shipping_cost_per_unit !== undefined ? form.shipping_cost_per_unit.toFixed(2) : '未设置' }}
              </span>
            </div>
            <div class="flex items-center gap-3">
              <input
                id="shipping_range"
                type="range"
                min="0"
                max="40"
                step="0.5"
                :value="form.shipping_cost_per_unit ?? 0"
                class="w-full accent-primary h-2 bg-secondary rounded-lg cursor-pointer"
                @input="form.shipping_cost_per_unit = Number(($event.target as HTMLInputElement).value)"
              />
              <Input
                id="shipping_cost"
                type="number"
                step="0.5"
                v-model.number="form.shipping_cost_per_unit"
                class="h-8 w-24 text-xs font-mono"
              />
            </div>
          </div>

          <!-- 月预估销量 -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between text-xs">
              <Label for="monthly_sales" class="font-medium">月度预估销量 (件/月)</Label>
              <span class="text-muted-foreground font-mono">
                {{ form.monthly_estimated_sales !== undefined ? form.monthly_estimated_sales : '未设置' }} 件
              </span>
            </div>
            <div class="flex items-center gap-3">
              <input
                id="sales_range"
                type="range"
                min="10"
                max="2000"
                step="10"
                :value="form.monthly_estimated_sales ?? 10"
                class="w-full accent-primary h-2 bg-secondary rounded-lg cursor-pointer"
                @input="form.monthly_estimated_sales = Number(($event.target as HTMLInputElement).value)"
              />
              <Input
                id="monthly_sales"
                type="number"
                v-model.number="form.monthly_estimated_sales"
                class="h-8 w-24 text-xs font-mono"
              />
            </div>
          </div>

          <!-- 约束门槛设置 -->
          <div class="pt-2 border-t space-y-3">
            <div class="text-xs font-medium text-muted-foreground">风控门槛约束</div>
            <div class="grid grid-cols-2 gap-3">
              <div class="space-y-1">
                <Label for="target_payback" class="text-xs">期望回本月数上限</Label>
                <Input
                  id="target_payback"
                  type="number"
                  v-model.number="form.target_payback_months"
                  class="h-8 text-xs font-mono"
                />
              </div>
              <div class="space-y-1">
                <Label for="half_life" class="text-xs">品类生命半衰期 (月)</Label>
                <Input
                  id="half_life"
                  type="number"
                  v-model.number="form.category_half_life_months"
                  class="h-8 text-xs font-mono"
                />
              </div>
            </div>
            <div class="space-y-1">
              <Label for="max_budget" class="text-xs">最大启动资金预算 (USD, 可选)</Label>
              <Input
                id="max_budget"
                type="number"
                v-model.number="form.max_cash_budget"
                placeholder="例如 30000"
                class="h-8 text-xs font-mono"
              />
            </div>
          </div>

          <!-- 操作按钮 -->
          <Button
            class="w-full gap-1.5"
            :disabled="isSubmitting"
            @click="runEvaluation"
          >
            <RefreshCw class="size-3.5" :class="{ 'animate-spin': isSubmitting }" />
            重新执行财务测算与风控校验
          </Button>
        </CardContent>
      </Card>

      <!-- 右栏：盈亏平衡曲线与敏感度分析 -->
      <div class="lg:col-span-7 space-y-6">
        <!-- 动态盈亏平衡与现金流走势折线图 -->
        <Card>
          <CardHeader>
            <div class="flex items-center justify-between">
              <CardTitle class="text-base font-semibold flex items-center gap-2">
                <TrendingUp class="size-4 text-primary" />
                动态盈亏平衡与现金流回收曲线
              </CardTitle>
              <Badge variant="outline" class="text-xs font-mono">ECharts</Badge>
            </div>
            <CardDescription>
              展示 0-18 个月累计收入、总成本与现金流回收走势。前端不自行重算业务逻辑。
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div v-if="!evalResult || evalResult.financial_state === 'NOT_EVALUATED'">
              <EmptyState
                :icon="Calculator"
                title="暂无测算走势曲线"
                description="输入有效财务参数后将生成动态回本敏感度与现金流走势"
              />
            </div>
            <div v-else>
              <VChart :option="chartOption" height-class="h-72" />
              <div class="mt-2 text-xs text-muted-foreground flex items-center justify-between border-t pt-2">
                <span>* 初始固定开模打样成本: ${{ evalResult.metrics?.fixed_costs.toLocaleString('en-US') }}</span>
                <span>* 理论保本销量: {{ evalResult.metrics?.break_even_units !== null ? `${evalResult.metrics?.break_even_units} 件` : '无法回本' }}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- 销量与定价敏感度矩阵 -->
        <Card>
          <CardHeader>
            <CardTitle class="text-base font-semibold flex items-center gap-2">
              <Percent class="size-4 text-primary" />
              销量与售价敏感度矩阵
            </CardTitle>
            <CardDescription>
              基于确定性公式模拟销量波动（-30% ~ +30%）与售价浮动下的静态回本月数。红色单元格表示命中熔断。
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div v-if="!evalResult || evalResult.financial_state === 'NOT_EVALUATED'">
              <EmptyState
                :icon="Percent"
                title="敏感度数据未就绪"
                description="请先输入完整财务数据执行测算"
              />
            </div>
            <div v-else class="overflow-x-auto">
              <table class="w-full text-xs text-center border-collapse">
                <thead>
                  <tr class="border-b bg-muted/40">
                    <th class="p-2 text-left text-muted-foreground font-medium">售价 \ 销量变动</th>
                    <th class="p-2 font-medium">-30% 销量</th>
                    <th class="p-2 font-medium">-15% 销量</th>
                    <th class="p-2 font-medium font-semibold text-foreground">基准销量</th>
                    <th class="p-2 font-medium">+15% 销量</th>
                    <th class="p-2 font-medium">+30% 销量</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="pDelta in [-15, -10, 0, 10, 15]"
                    :key="pDelta"
                    class="border-b hover:bg-muted/30 transition-colors"
                  >
                    <td class="p-2 text-left font-medium text-muted-foreground">
                      {{ pDelta === 0 ? '基准售价' : `${pDelta > 0 ? '+' : ''}${pDelta}% 售价` }}
                    </td>
                    <td
                      v-for="sDelta in [-30, -15, 0, 15, 30]"
                      :key="sDelta"
                      class="p-2 font-mono"
                    >
                      <template
                        v-for="pt in evalResult.sensitivity_matrix.filter(
                          (m) => m.price_change_percent === pDelta && m.sales_change_percent === sDelta
                        )"
                        :key="`${pt.sales_change_percent}_${pt.price_change_percent}`"
                      >
                        <span
                          class="inline-block px-2 py-0.5 rounded text-xs"
                          :class="
                            pt.is_vetoed
                              ? 'bg-red-100 text-red-700 font-medium'
                              : 'bg-emerald-100 text-emerald-800'
                          "
                        >
                          {{ pt.payback_months >= 999 ? '熔断' : `${pt.payback_months}月` }}
                        </span>
                      </template>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <!-- 规则版本与说明 -->
        <Card>
          <CardHeader class="pb-3">
            <CardTitle class="text-sm font-semibold flex items-center justify-between">
              <span>生效风控规则清单 (PRD P1-02)</span>
              <Badge variant="secondary" class="text-xs">
                {{ rulesInfo?.rule_version ?? 'financial_rules_v1.0' }}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent class="space-y-2 text-xs">
            <div
              v-for="r in rulesInfo?.rules ?? []"
              :key="r.code"
              class="rounded border p-2.5 bg-card/60 flex items-start justify-between gap-4"
            >
              <div>
                <div class="font-medium text-foreground flex items-center gap-1.5">
                  <span class="size-1.5 rounded-full bg-primary" />
                  {{ r.name }}
                </div>
                <div class="text-muted-foreground mt-0.5">{{ r.description }}</div>
              </div>
              <div class="text-right shrink-0">
                <span class="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
                  {{ r.threshold }}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>
