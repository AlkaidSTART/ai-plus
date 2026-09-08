<script setup lang="ts">
import {
  Box,
  Calendar,
  DollarSign,
  Download,
  ExternalLink,
  TrendingUp,
  Wrench,
} from 'lucide-vue-next';
import type { PackagingProposal, PhysicalProposal } from '../types';

defineProps<{
  physicalProposals: PhysicalProposal[];
  packagingProposals: PackagingProposal[];
}>();

const emit = defineEmits<{
  (e: 'viewEvidence', target: { title: string; count: number }): void;
  (e: 'exportRfc'): void;
}>();
</script>

<template>
  <div class="space-y-6">
    <!-- Top Executive Summary Bar -->
    <div class="glass-panel rounded-2xl p-6 relative overflow-hidden">
      <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
        <div class="space-y-1.5">
          <div class="flex items-center gap-2">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-cyan-950 border border-cyan-700/60 text-cyan-300">
              ENGINEERING RFC · v1.0
            </span>
            <span class="text-xs text-zinc-400">工贸一体出海专属落地决策</span>
          </div>

          <h2 class="text-xl sm:text-2xl font-bold text-zinc-100 flex items-center gap-2">
            <Wrench class="w-6 h-6 text-cyan-400" />
            <span>工厂级“双栏改款”决策引擎</span>
          </h2>

          <p class="text-xs text-zinc-400 max-w-2xl leading-relaxed">
            告别空洞报表：系统自动将差评痛点转化为模具厂图纸要求与包装厂打样规格，分别对接硬件研发与供应链物流。
          </p>
        </div>

        <!-- Metric Stat Pill Box -->
        <div class="flex flex-wrap items-center gap-3">
          <div class="p-3 rounded-xl bg-zinc-900/90 border border-zinc-800 text-xs font-mono">
            <div class="text-zinc-400 text-[10px]">本体改款增额 / 件</div>
            <div class="text-amber-400 font-bold text-sm">+$2.95 USD</div>
          </div>

          <div class="p-3 rounded-xl bg-zinc-900/90 border border-zinc-800 text-xs font-mono">
            <div class="text-zinc-400 text-[10px]">包装履约降本 / 件</div>
            <div class="text-emerald-400 font-bold text-sm">-$5.90 USD</div>
          </div>

          <div class="p-3 rounded-xl bg-emerald-950/40 border border-emerald-500/40 text-xs font-mono">
            <div class="text-emerald-300 text-[10px] flex items-center gap-1">
              <TrendingUp class="w-3 h-3" />
              <span>单件综合净利提升</span>
            </div>
            <div class="text-emerald-400 font-bold text-sm">+$2.95 USD / 件</div>
          </div>

          <button
            @click="emit('exportRfc')"
            class="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 text-xs font-medium transition-colors"
          >
            <Download class="w-4 h-4 text-cyan-400" />
            <span>导出工程 RFC 报告</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Dual Column Container -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
      <!-- Left Column: Physical Product Optimization -->
      <div class="space-y-4">
        <div class="flex items-center justify-between pb-2 border-b border-zinc-800">
          <div class="flex items-center gap-2">
            <div class="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              <Wrench class="w-4 h-4" />
            </div>
            <div>
              <h3 class="text-sm font-bold text-zinc-100">左栏：产品物理本体优化</h3>
              <p class="text-[11px] text-zinc-400">对接模具厂、结构工程师与材料供应商</p>
            </div>
          </div>
          <span class="text-xs font-mono px-2 py-0.5 rounded bg-zinc-800 text-cyan-400">
            {{ physicalProposals.length }} 项工程提案
          </span>
        </div>

        <div class="space-y-4">
          <div
            v-for="prop in physicalProposals"
            :key="prop.id"
            class="glass-panel glass-panel-hover rounded-xl p-5 space-y-3.5 border-l-4 border-l-cyan-500"
          >
            <!-- Header Tag & Cluster Ref -->
            <div class="flex items-center justify-between text-xs">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-800">
                {{ prop.category }}
              </span>
              <span class="text-[11px] text-zinc-400 font-mono">
                关联痛点: {{ prop.targetClusterName.slice(0, 14) }}...
              </span>
            </div>

            <!-- Title -->
            <h4 class="text-sm font-bold text-zinc-100 leading-snug">
              {{ prop.title }}
            </h4>

            <!-- Problem vs Action -->
            <div class="space-y-2 text-xs">
              <div class="p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800/80 space-y-1">
                <span class="text-rose-400 font-semibold text-[10px] block uppercase font-mono">原缺陷陈述:</span>
                <p class="text-zinc-400 leading-relaxed">{{ prop.problemStatement }}</p>
              </div>

              <div class="p-2.5 rounded-lg bg-cyan-950/20 border border-cyan-800/30 space-y-1">
                <span class="text-cyan-400 font-semibold text-[10px] block uppercase font-mono">改款工程方案:</span>
                <p class="text-zinc-200 leading-relaxed">{{ prop.actionPlan }}</p>
              </div>
            </div>

            <!-- Factory Spec Code Block -->
            <div class="p-3 rounded-lg bg-zinc-950 border border-zinc-800/90 font-mono text-[11px] text-zinc-300 space-y-1">
              <span class="text-zinc-500 text-[10px]">FACTORY_SPEC / 模具图纸要求:</span>
              <p class="text-emerald-400">{{ prop.engineeringSpec }}</p>
            </div>

            <!-- Cost & Lead Time Footer -->
            <div class="flex items-center justify-between pt-2 border-t border-zinc-800/80 text-xs">
              <div class="flex items-center gap-3 font-mono text-[11px]">
                <span class="flex items-center gap-1 text-zinc-400">
                  <DollarSign class="w-3.5 h-3.5 text-amber-400" />
                  <span>单件增额: <strong class="text-zinc-200">+${{ prop.costDeltaUsd.toFixed(2) }}</strong></span>
                </span>
                <span class="flex items-center gap-1 text-zinc-400">
                  <Calendar class="w-3.5 h-3.5 text-cyan-400" />
                  <span>打样: <strong class="text-zinc-200">{{ prop.leadTimeDays }}天</strong></span>
                </span>
              </div>

              <button
                @click="emit('viewEvidence', { title: prop.title, count: prop.evidenceCount })"
                class="flex items-center gap-1 text-[11px] text-cyan-400 hover:text-cyan-300 font-mono"
              >
                <ExternalLink class="w-3 h-3" />
                <span>溯源 ({{ prop.evidenceCount }}评 / {{ prop.photoCount }}图)</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column: Packaging & Logistics Optimization -->
      <div class="space-y-4">
        <div class="flex items-center justify-between pb-2 border-b border-zinc-800">
          <div class="flex items-center gap-2">
            <div class="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <Box class="w-4 h-4" />
            </div>
            <div>
              <h3 class="text-sm font-bold text-zinc-100">右栏：包装履约降本优化</h3>
              <p class="text-[11px] text-zinc-400">对接包装打样厂、FBA 物流专员与质检</p>
            </div>
          </div>
          <span class="text-xs font-mono px-2 py-0.5 rounded bg-zinc-800 text-emerald-400">
            {{ packagingProposals.length }} 项包装提案
          </span>
        </div>

        <div class="space-y-4">
          <div
            v-for="pkg in packagingProposals"
            :key="pkg.id"
            class="glass-panel glass-panel-hover rounded-xl p-5 space-y-3.5 border-l-4 border-l-emerald-500"
          >
            <!-- Header Tag & Cluster Ref -->
            <div class="flex items-center justify-between text-xs">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800">
                {{ pkg.category }}
              </span>
              <span class="text-[11px] text-zinc-400 font-mono">
                关联痛点: {{ pkg.targetClusterName.slice(0, 14) }}...
              </span>
            </div>

            <!-- Title -->
            <h4 class="text-sm font-bold text-zinc-100 leading-snug">
              {{ pkg.title }}
            </h4>

            <!-- Problem vs Action -->
            <div class="space-y-2 text-xs">
              <div class="p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800/80 space-y-1">
                <span class="text-amber-400 font-semibold text-[10px] block uppercase font-mono">履约/包装缺陷:</span>
                <p class="text-zinc-400 leading-relaxed">{{ pkg.problemStatement }}</p>
              </div>

              <div class="p-2.5 rounded-lg bg-emerald-950/20 border border-emerald-800/30 space-y-1">
                <span class="text-emerald-400 font-semibold text-[10px] block uppercase font-mono">包材降本方案:</span>
                <p class="text-zinc-200 leading-relaxed">{{ pkg.actionPlan }}</p>
              </div>
            </div>

            <!-- Packaging Spec Block -->
            <div class="p-3 rounded-lg bg-zinc-950 border border-zinc-800/90 font-mono text-[11px] text-zinc-300 space-y-1">
              <span class="text-zinc-500 text-[10px]">PACKAGING_METRIC / 物流收益:</span>
              <p class="text-cyan-400">{{ pkg.engineeringSpec }}</p>
            </div>

            <!-- FBA Savings & Lead Time Footer -->
            <div class="flex items-center justify-between pt-2 border-t border-zinc-800/80 text-xs">
              <div class="flex items-center gap-3 font-mono text-[11px]">
                <span class="flex items-center gap-1 text-zinc-400">
                  <DollarSign class="w-3.5 h-3.5 text-emerald-400" />
                  <span>单件省: <strong class="text-emerald-400">${{ pkg.fbaSavingsPerUnit.toFixed(2) }}</strong></span>
                </span>
                <span class="flex items-center gap-1 text-zinc-400">
                  <Calendar class="w-3.5 h-3.5 text-cyan-400" />
                  <span>打样: <strong class="text-zinc-200">{{ pkg.leadTimeDays }}天</strong></span>
                </span>
              </div>

              <button
                @click="emit('viewEvidence', { title: pkg.title, count: pkg.evidenceCount })"
                class="flex items-center gap-1 text-[11px] text-cyan-400 hover:text-cyan-300 font-mono"
              >
                <ExternalLink class="w-3 h-3" />
                <span>溯源 ({{ pkg.evidenceCount }} 评)</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
