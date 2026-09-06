<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { exportRfc, getFinancialDecision, getInsightReport, getProposals, getProposalEvidence } from '@/api'
import type { FinancialDecision, InsightReport, Proposal, ProposalEvidence } from '@/types'
import { DEFAULT_TASK_ID } from '@/stores/tasks'

const track = ref<'BODY_OPTIMIZATION' | 'PACKAGING_FULFILLMENT'>('BODY_OPTIMIZATION')
const proposals = ref<Proposal[]>([])
const decision = ref<FinancialDecision | null>(null)
const evidenceOpen = ref(false)
const activeEvidence = ref<ProposalEvidence | null>(null)
const activeProposal = ref<Proposal | null>(null)

/* ---------- 导出 RFC / 聚合报告 ---------- */
const exporting = ref(false)
const reportOpen = ref(false)
const report = ref<InsightReport | null>(null)

onMounted(async () => {
  const [p, d] = await Promise.all([getProposals(DEFAULT_TASK_ID), getFinancialDecision(DEFAULT_TASK_ID)])
  proposals.value = p.items
  decision.value = d
})

async function handleExportRfc() {
  exporting.value = true
  try {
    const r = await exportRfc(DEFAULT_TASK_ID)
    const blob = new Blob([r.content], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = r.filename
    a.click()
    URL.revokeObjectURL(url)
  } finally {
    exporting.value = false
  }
}

async function openReport() {
  report.value = null
  reportOpen.value = true
  report.value = await getInsightReport(DEFAULT_TASK_ID)
}

const reportTopClusters = computed(() => {
  const items = report.value?.clusters.items ?? []
  return [...items].sort((a, b) => b.severity_score - a.severity_score).slice(0, 3)
})

const trackProposals = computed(() => proposals.value.filter((x) => x.track_type === track.value))
const bodyProposals = computed(() => proposals.value.filter((x) => x.track_type === 'BODY_OPTIMIZATION'))
const packagingProposals = computed(() => proposals.value.filter((x) => x.track_type === 'PACKAGING_FULFILLMENT'))

async function openEvidence(proposal: Proposal) {
  activeProposal.value = proposal
  activeEvidence.value = null
  evidenceOpen.value = true
  activeEvidence.value = await getProposalEvidence(proposal.proposal_id)
}

const trackMeta = {
  BODY_OPTIMIZATION: { label: '本体结构改款', desc: '开模 / 结构件 / 电子方案' },
  PACKAGING_FULFILLMENT: { label: '包装履约轨', desc: '免开模 · 箱规降阶 · FBA 费用优化' },
} as const

const vetoRate = computed(() => {
  if (!proposals.value.length) return 0
  return proposals.value.filter((p) => p.status === 'VETOED').length / proposals.value.length
})

function fmtUsd(v: number): string {
  return `$${v.toLocaleString('en-US')}`
}
</script>

<template>
  <div class="space-y-6">
    <!-- 决策概览 -->
    <section class="card card-pad">
      <div class="flex flex-wrap items-center gap-x-8 gap-y-3">
        <div>
          <div class="text-xs text-slate-400">本次诊断任务</div>
          <div class="mt-1 font-mono text-sm text-slate-700">{{ DEFAULT_TASK_ID }}</div>
        </div>
        <div>
          <div class="text-xs text-slate-400">生成提案</div>
          <div class="mt-1 text-lg font-bold text-slate-800">{{ proposals.length }} 条</div>
        </div>
        <div>
          <div class="text-xs text-slate-400">风控否决率</div>
          <div class="mt-1 text-lg font-bold text-rose-600">{{ (vetoRate * 100).toFixed(0) }}%</div>
        </div>
        <div>
          <div class="text-xs text-slate-400">财务结论</div>
          <div class="mt-1">
            <span
              class="rounded-md px-2 py-1 text-xs font-semibold"
              :class="decision?.veto_status === 'PASSED' ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'"
            >
              {{ decision?.veto_status === 'PASSED' ? '整体通过' : '触发熔断' }}
            </span>
            <span v-if="decision?.fallback_applied" class="ml-2 text-xs text-amber-600">已生成免开模替代方案</span>
          </div>
        </div>
        <div class="ml-auto flex items-center gap-2">
          <button
            class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-600"
            @click="openReport"
          >
            <svg class="size-4" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0V12a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 12V5.25" />
            </svg>
            聚合报告
          </button>
          <button
            class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-60"
            :disabled="exporting"
            @click="handleExportRfc"
          >
            <svg v-if="exporting" class="size-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4Z" />
            </svg>
            <svg v-else class="size-4" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            导出工程改款 RFC
          </button>
        </div>
      </div>
    </section>

    <!-- 双栏切换 -->
    <div class="grid gap-3 sm:grid-cols-2">
      <button
        v-for="(m, key) in trackMeta"
        :key="key"
        class="card card-pad text-left transition-colors"
        :class="track === key ? 'border-indigo-400 ring-2 ring-indigo-100' : 'hover:border-slate-300'"
        @click="track = key as typeof track"
      >
        <div class="flex items-center justify-between">
          <span class="text-sm font-semibold" :class="track === key ? 'text-indigo-600' : 'text-slate-700'">{{ m.label }}</span>
          <span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{{ (key === 'BODY_OPTIMIZATION' ? bodyProposals : packagingProposals).length }} 条</span>
        </div>
        <p class="mt-1 text-xs text-slate-400">{{ m.desc }}</p>
      </button>
    </div>

    <!-- 提案列表 -->
    <div class="space-y-4">
      <section v-for="p in trackProposals" :key="p.proposal_id" class="card">
        <div class="flex flex-wrap items-start justify-between gap-3 p-5">
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="text-sm font-semibold text-slate-800">{{ p.title }}</h3>
              <span
                class="rounded-md px-2 py-0.5 text-xs font-semibold"
                :class="p.status === 'PASSED' ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'"
              >
                {{ p.status === 'PASSED' ? '通过' : '否决' }}
              </span>
            </div>
            <p class="mt-2 text-sm leading-relaxed text-slate-600">{{ p.description }}</p>
          </div>
          <button
            class="shrink-0 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:border-indigo-300 hover:text-indigo-600"
            @click="openEvidence(p)"
          >
            证据链（{{ p.evidence_review_count }} 评论 · {{ p.evidence_image_count }} 图）
          </button>
        </div>

        <!-- 指标 -->
        <div class="grid grid-cols-2 gap-px border-t border-slate-100 bg-slate-100 sm:grid-cols-4">
          <div class="bg-white p-4">
            <div class="text-xs text-slate-400">预估改造成本</div>
            <div class="mt-1 text-sm font-semibold text-slate-800">{{ fmtUsd(p.cost_estimation_usd) }}</div>
            <div class="mt-0.5 text-[11px] text-slate-400">{{ p.mold_opening_required ? `开模 ${p.mold_cycle_days} 天` : '免开模' }}</div>
          </div>
          <div class="bg-white p-4">
            <div class="text-xs text-slate-400">预估 ROI</div>
            <div class="mt-1 text-sm font-semibold text-indigo-600">{{ p.estimated_roi.toFixed(1) }}x</div>
          </div>
          <div class="bg-white p-4">
            <div class="text-xs text-slate-400">缺陷率降幅</div>
            <div class="mt-1 text-sm font-semibold text-emerald-600">↓{{ (p.defect_rate_reduction * 100).toFixed(0) }}%</div>
          </div>
          <div class="bg-white p-4">
            <div class="text-xs text-slate-400">支撑聚类</div>
            <div class="mt-1 font-mono text-xs text-slate-600">{{ p.source_cluster_ids.join('、') }}</div>
          </div>
        </div>

        <!-- 包装履约轨对比 -->
        <div v-if="p.track_type === 'PACKAGING_FULFILLMENT'" class="border-t border-slate-100 px-5 py-4">
          <div class="mb-2 text-xs font-medium text-slate-500">箱规 / FBA 费用对比</div>
          <div class="grid grid-cols-2 gap-3 text-xs">
            <div class="rounded-lg bg-slate-50 p-3">
              <div class="text-slate-400">改造前</div>
              <div class="mt-1 font-medium text-slate-700">{{ p.package_size_old_cm?.join('×') }} cm</div>
              <div class="text-slate-500">体积重 {{ p.volumetric_weight_old_kg }} kg · {{ p.fba_tier_old }}</div>
            </div>
            <div class="rounded-lg bg-emerald-50 p-3">
              <div class="text-emerald-500">改造后</div>
              <div class="mt-1 font-medium text-emerald-800">{{ p.package_size_new_cm?.join('×') }} cm</div>
              <div class="text-emerald-600">体积重 {{ p.volumetric_weight_new_kg }} kg · {{ p.fba_tier_new }}</div>
            </div>
          </div>
          <div class="mt-3 rounded-lg bg-indigo-50 px-3 py-2 text-xs text-indigo-700">
            单件履约节省 {{ fmtUsd(p.fulfillment_saving_usd_per_unit ?? 0) }}
          </div>
        </div>

        <!-- 否决原因 -->
        <div v-if="p.status === 'VETOED' && p.veto_reason" class="border-t border-rose-100 bg-rose-50/60 px-5 py-3">
          <div class="text-xs font-medium text-rose-700">风控否决原因</div>
          <p class="mt-1 text-xs leading-relaxed text-rose-600">{{ p.veto_reason }}</p>
          <p v-if="p.fallback_applied" class="mt-1 text-xs text-amber-600">已自动应用免开模替代方案</p>
        </div>
      </section>
    </div>

    <!-- 证据抽屉 -->
    <Transition name="slide">
      <div v-if="evidenceOpen" class="fixed inset-y-0 right-0 z-40 w-full max-w-md bg-white shadow-xl">
        <div class="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <div class="min-w-0">
            <div class="truncate text-sm font-semibold text-slate-800">{{ activeProposal?.title }}</div>
            <div class="text-xs text-slate-400">证据溯源 · 评论与图片绑定</div>
          </div>
          <button class="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100" @click="evidenceOpen = false">
            <svg class="size-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="max-h-[calc(100vh-57px)] space-y-4 overflow-y-auto p-4">
          <div v-if="!activeEvidence" class="py-10 text-center text-sm text-slate-400">加载证据…</div>
          <div v-for="rv in activeEvidence?.reviews ?? []" :key="rv.review_id" class="rounded-xl border border-slate-200 p-4">
            <div class="flex items-center gap-2 text-xs">
              <span class="font-medium text-amber-500">{{ '★'.repeat(Math.round(rv.rating)) }}</span>
              <span class="text-slate-400">{{ rv.review_date }} · {{ rv.language.toUpperCase() }}</span>
            </div>
            <p class="mt-2 text-sm text-slate-700">{{ rv.translated_content }}</p>
            <div class="mt-1 flex flex-wrap gap-1">
              <span v-for="k in rv.highlight_keywords" :key="k" class="rounded bg-amber-50 px-1.5 py-0.5 text-[11px] font-medium text-amber-700">{{ k }}</span>
            </div>
            <div v-if="rv.images.length" class="mt-3 grid grid-cols-3 gap-2">
              <figure v-for="im in rv.images" :key="im.image_id" class="relative overflow-hidden rounded-lg">
                <img :src="im.storage_url" :alt="im.defect_category" class="aspect-square w-full object-cover" loading="lazy" />
                <span class="absolute bottom-0 left-0 right-0 bg-black/60 px-1.5 py-0.5 text-[10px] text-white">
                  {{ (im.confidence * 100).toFixed(0) }}%
                </span>
              </figure>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 聚合报告抽屉 -->
    <Transition name="slide">
      <div v-if="reportOpen" class="fixed inset-y-0 right-0 z-40 w-full max-w-lg bg-white shadow-xl">
        <div class="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <div class="min-w-0">
            <div class="text-sm font-semibold text-slate-800">LangGraph 洞察聚合报告</div>
            <div class="text-xs text-slate-400">{{ DEFAULT_TASK_ID }}</div>
          </div>
          <button class="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100" @click="reportOpen = false">
            <svg class="size-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div v-if="!report" class="p-12 text-center text-sm text-slate-400">聚合数据装载中…</div>
        <div v-else class="max-h-[calc(100vh-57px)] space-y-5 overflow-y-auto p-5">
          <!-- 任务摘要 -->
          <section class="rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 p-4 text-white">
            <div class="flex items-center justify-between">
              <span class="text-xs text-indigo-200">ASIN {{ report.task.asin }}</span>
              <span class="rounded-full bg-white/20 px-2 py-0.5 text-[11px]">{{ report.task.status }}</span>
            </div>
            <div class="mt-2 text-lg font-bold">{{ report.task.marketplace }} 站点 · {{ report.task.platform }} 平台</div>
            <div class="mt-1 text-xs text-indigo-200">任务进度 {{ report.task.progress }}%</div>
          </section>

          <!-- 关键指标 -->
          <section class="grid grid-cols-2 gap-3">
            <div class="rounded-xl border border-slate-200 p-3">
              <div class="text-xs text-slate-400">痛点聚类</div>
              <div class="mt-1 text-xl font-bold text-slate-800">{{ report.clusters.items.length }}</div>
            </div>
            <div class="rounded-xl border border-slate-200 p-3">
              <div class="text-xs text-slate-400">改款提案</div>
              <div class="mt-1 text-xl font-bold text-slate-800">
                {{ report.proposals.items.length }}
                <span class="ml-1 align-middle text-[11px] font-medium text-emerald-600">
                  {{ report.proposals.items.filter((x) => x.status === 'PASSED').length }} 通过
                </span>
              </div>
            </div>
            <div class="rounded-xl border border-slate-200 p-3">
              <div class="text-xs text-slate-400">视觉取证</div>
              <div class="mt-1 text-xl font-bold text-slate-800">{{ report.visual_evidences.items.length }}</div>
            </div>
            <div class="rounded-xl border border-slate-200 p-3">
              <div class="text-xs text-slate-400">财务结论</div>
              <div class="mt-1 text-sm font-bold" :class="report.financial?.veto_status === 'PASSED' ? 'text-emerald-600' : 'text-rose-600'">
                {{ report.financial?.veto_status === 'PASSED' ? '整体通过' : '触发熔断' }}
              </div>
            </div>
          </section>

          <!-- 高风险聚类 -->
          <section>
            <h4 class="mb-2 text-xs font-semibold text-slate-500">高风险聚类 Top 3</h4>
            <div class="space-y-2">
              <div v-for="c in reportTopClusters" :key="c.cluster_id" class="flex items-center gap-3 rounded-lg border border-slate-200 px-3 py-2">
                <span class="size-2 shrink-0 rounded-full" :class="c.severity_level === 'critical' ? 'bg-rose-500' : c.severity_level === 'moderate' ? 'bg-amber-500' : 'bg-sky-500'" />
                <span class="min-w-0 flex-1 truncate text-sm text-slate-700">{{ c.cluster_name }}</span>
                <span class="text-xs text-slate-400">{{ c.frequency }} 条</span>
                <span class="rounded-md px-1.5 py-0.5 text-[11px] font-bold" :class="{
                  'bg-rose-100 text-rose-700': c.severity_level === 'critical',
                  'bg-amber-100 text-amber-700': c.severity_level === 'moderate',
                  'bg-sky-100 text-sky-700': c.severity_level === 'minor',
                }">{{ c.severity_score.toFixed(1) }}</span>
              </div>
            </div>
          </section>

          <!-- 财务否决清单 -->
          <section v-if="report.financial?.vetoed_proposal_ids.length">
            <h4 class="mb-2 text-xs font-semibold text-slate-500">风控否决提案</h4>
            <div class="space-y-2">
              <div v-for="pid in report.financial.vetoed_proposal_ids" :key="pid" class="rounded-lg bg-rose-50 px-3 py-2 font-mono text-xs text-rose-700">
                {{ pid }}
              </div>
            </div>
          </section>

          <button
            class="inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-600"
            @click="handleExportRfc"
          >
            导出该报告的工程改款 RFC（.md）
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}
</style>
