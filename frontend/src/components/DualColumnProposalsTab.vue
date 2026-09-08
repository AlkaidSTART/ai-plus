<script setup lang="ts">
import {
  Box,
  Download,
  ExternalLink,
  Wrench,
} from 'lucide-vue-next';
import { useI18n } from 'vue-i18n';
import type { PackagingProposal, PhysicalProposal } from '../types';

defineProps<{
  physicalProposals: PhysicalProposal[];
  packagingProposals: PackagingProposal[];
}>();

const emit = defineEmits<{
  (e: 'viewEvidence', target: { title: string; count: number }): void;
  (e: 'exportRfc'): void;
}>();

const { t } = useI18n();
</script>

<template>
  <div class="space-y-6">
    <!-- Top Executive Header & Net ROI Summary -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[rgba(255,255,255,0.06)]">
      <div class="space-y-1">
        <h1 class="text-xl font-medium tracking-tight text-[#f7f8f8]">
          {{ t('proposals.title') }}
        </h1>
        <p class="text-xs text-[#8a8f98]">
          {{ t('proposals.subtitle') }}
        </p>
      </div>

      <div class="flex items-center gap-3">
        <!-- Minimal Net Profit Pill -->
        <div class="flex items-center gap-3 px-3 py-1.5 rounded-lg bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] text-xs font-mono">
          <span class="text-[#8a8f98]">{{ t('proposals.costDelta') }} <strong class="text-amber-400">+$2.95</strong></span>
          <span class="text-zinc-600">|</span>
          <span class="text-[#8a8f98]">{{ t('proposals.logisticsSavings') }} <strong class="text-emerald-400">-$5.90</strong></span>
          <span class="text-zinc-600">|</span>
          <span class="text-emerald-400 font-medium">{{ t('proposals.netGain') }}</span>
        </div>

        <button
          @click="emit('exportRfc')"
          class="ln-btn px-3 py-1.5 flex items-center gap-1.5"
        >
          <Download class="w-3.5 h-3.5" />
          <span>{{ t('common.export') }}</span>
        </button>
      </div>
    </div>

    <!-- Dual Column Layout: Left Physical vs Right Packaging -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
      <!-- Left Column: Physical Product Optimization -->
      <div class="space-y-4">
        <div class="flex items-center justify-between pb-2 border-b border-[rgba(255,255,255,0.06)]">
          <div class="flex items-center gap-2">
            <Wrench class="w-4 h-4 text-[#7170ff]" />
            <h2 class="text-xs font-semibold text-[#f7f8f8] uppercase tracking-wider">
              {{ t('proposals.leftTitle') }}
            </h2>
          </div>
          <span class="text-[11px] font-mono text-[#8a8f98]">{{ t('proposals.leftSubtitle') }}</span>
        </div>

        <div class="space-y-3">
          <div
            v-for="prop in physicalProposals"
            :key="prop.id"
            class="ln-surface p-4 space-y-3 hover:border-[rgba(255,255,255,0.12)] transition-colors"
          >
            <div class="flex items-center justify-between text-xs">
              <span class="font-medium text-[#f7f8f8]">{{ prop.title }}</span>
              <span class="text-[11px] font-mono text-[#8a8f98]">{{ prop.category }}</span>
            </div>

            <!-- Problem -> Solution in clean typography -->
            <div class="space-y-1.5 text-xs text-[#8a8f98] leading-relaxed">
              <p><strong class="text-zinc-400">{{ t('proposals.originalFlaw') }}</strong>{{ prop.problemStatement }}</p>
              <p><strong class="text-zinc-400">{{ t('proposals.engineeringPlan') }}</strong>{{ prop.actionPlan }}</p>
            </div>

            <!-- Factory Spec Code Snippet -->
            <div class="p-2 rounded bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.05)] text-[11px] font-mono text-zinc-300">
              <span class="text-zinc-500">SPEC: </span>{{ prop.engineeringSpec }}
            </div>

            <!-- Footer: Cost Delta, Lead Time, Evidence -->
            <div class="flex items-center justify-between text-[11px] font-mono pt-1 text-[#8a8f98]">
              <div class="flex items-center gap-3">
                <span>{{ t('proposals.costDelta') }}: <strong class="text-zinc-300">+${{ prop.costDeltaUsd.toFixed(2) }}</strong></span>
                <span>{{ t('proposals.leadTime') }} {{ prop.leadTimeDays }} {{ t('common.days') }}</span>
              </div>

              <button
                @click="emit('viewEvidence', { title: prop.title, count: prop.evidenceCount })"
                class="text-[#7170ff] hover:text-[#828fff] flex items-center gap-1 transition-colors"
              >
                <span>{{ t('proposals.traceEvidence', { count: prop.evidenceCount }) }}</span>
                <ExternalLink class="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column: Packaging & Logistics Optimization -->
      <div class="space-y-4">
        <div class="flex items-center justify-between pb-2 border-b border-[rgba(255,255,255,0.06)]">
          <div class="flex items-center gap-2">
            <Box class="w-4 h-4 text-emerald-400" />
            <h2 class="text-xs font-semibold text-[#f7f8f8] uppercase tracking-wider">
              {{ t('proposals.rightTitle') }}
            </h2>
          </div>
          <span class="text-[11px] font-mono text-[#8a8f98]">{{ t('proposals.rightSubtitle') }}</span>
        </div>

        <div class="space-y-3">
          <div
            v-for="pkg in packagingProposals"
            :key="pkg.id"
            class="ln-surface p-4 space-y-3 hover:border-[rgba(255,255,255,0.12)] transition-colors"
          >
            <div class="flex items-center justify-between text-xs">
              <span class="font-medium text-[#f7f8f8]">{{ pkg.title }}</span>
              <span class="text-[11px] font-mono text-[#8a8f98]">{{ pkg.category }}</span>
            </div>

            <!-- Problem -> Solution in clean typography -->
            <div class="space-y-1.5 text-xs text-[#8a8f98] leading-relaxed">
              <p><strong class="text-zinc-400">{{ t('proposals.shippingFlaw') }}</strong>{{ pkg.problemStatement }}</p>
              <p><strong class="text-zinc-400">{{ t('proposals.packagingPlan') }}</strong>{{ pkg.actionPlan }}</p>
            </div>

            <!-- Packaging Metric Snippet -->
            <div class="p-2 rounded bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.05)] text-[11px] font-mono text-zinc-300">
              <span class="text-zinc-500">SAVINGS: </span>{{ pkg.engineeringSpec }}
            </div>

            <!-- Footer: FBA Savings, Lead Time, Evidence -->
            <div class="flex items-center justify-between text-[11px] font-mono pt-1 text-[#8a8f98]">
              <div class="flex items-center gap-3">
                <span>{{ t('proposals.unitSavings') }} <strong class="text-emerald-400">${{ pkg.fbaSavingsPerUnit.toFixed(2) }}</strong></span>
                <span>{{ t('proposals.leadTime') }} {{ pkg.leadTimeDays }} {{ t('common.days') }}</span>
              </div>

              <button
                @click="emit('viewEvidence', { title: pkg.title, count: pkg.evidenceCount })"
                class="text-[#7170ff] hover:text-[#828fff] flex items-center gap-1 transition-colors"
              >
                <span>{{ t('proposals.traceEvidence', { count: pkg.evidenceCount }) }}</span>
                <ExternalLink class="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
