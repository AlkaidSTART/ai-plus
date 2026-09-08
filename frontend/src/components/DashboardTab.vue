<script setup lang="ts">
import {
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  Play,
  ShieldAlert,
  Sliders,
  Wrench,
} from 'lucide-vue-next';
import { useI18n } from 'vue-i18n';
import type { InsightTask, PainPointCluster } from '../types';

defineProps<{
  currentTask: InsightTask;
  allTasks: InsightTask[];
  clusters: PainPointCluster[];
}>();

const emit = defineEmits<{
  (e: 'navigate', tab: 'dashboard' | 'agent' | 'voc' | 'proposals' | 'financial'): void;
  (e: 'selectTask', taskId: string): void;
  (e: 'startNewTask'): void;
}>();

const { t } = useI18n();
</script>

<template>
  <div class="space-y-8">
    <!-- Clean Product Header & Title (Single breathing row) -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[rgba(255,255,255,0.06)]">
      <div class="space-y-1.5 max-w-3xl">
        <div class="flex items-center gap-2 text-xs font-mono text-[#8a8f98]">
          <span>{{ currentTask.asin }}</span>
          <span>·</span>
          <span>{{ currentTask.marketplace }} {{ t('header.marketplace') }}</span>
          <span>·</span>
          <span>BSR #{{ currentTask.bsr }}</span>
          <span>·</span>
          <span>{{ currentTask.reviewCount.toLocaleString() }} Reviews</span>
        </div>
        <h1 class="text-xl sm:text-2xl font-medium tracking-tight text-[#f7f8f8]">
          {{ currentTask.productTitle }}
        </h1>
      </div>

      <!-- Quick Action Buttons -->
      <div class="flex items-center gap-2 shrink-0">
        <button
          @click="emit('navigate', 'proposals')"
          class="ln-btn-primary px-3.5 py-2 flex items-center gap-2"
        >
          <Wrench class="w-3.5 h-3.5" />
          <span>{{ t('dashboard.viewProposals') }}</span>
          <ArrowRight class="w-3.5 h-3.5 opacity-70" />
        </button>

        <button
          @click="emit('navigate', 'agent')"
          class="ln-btn px-3.5 py-2 flex items-center gap-2"
        >
          <Play class="w-3.5 h-3.5 text-zinc-400" />
          <span>{{ t('dashboard.runNew') }}</span>
        </button>
      </div>
    </div>

    <!-- 4 Clean, Quiet KPI Cards -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="ln-surface p-5 space-y-1">
        <div class="text-xs text-[#8a8f98]">{{ t('dashboard.negativeRate') }}</div>
        <div class="text-2xl font-semibold font-mono text-[#f7f8f8] tracking-tight">
          {{ (currentTask.negativeRate * 100).toFixed(1) }}%
        </div>
        <div class="text-[11px] text-[#5e626e] pt-1">
          {{ t('dashboard.negativeSub') }}
        </div>
      </div>

      <div class="ln-surface p-5 space-y-1">
        <div class="text-xs text-[#8a8f98]">{{ t('dashboard.peakSeverity') }}</div>
        <div class="text-2xl font-semibold font-mono text-amber-400 tracking-tight">
          4.8 <span class="text-xs font-normal text-[#5e626e]">/ 5.0</span>
        </div>
        <div class="text-[11px] text-[#5e626e] pt-1">
          {{ t('dashboard.peakSub') }}
        </div>
      </div>

      <div class="ln-surface p-5 space-y-1">
        <div class="text-xs text-[#8a8f98]">{{ t('dashboard.proposalsCount') }}</div>
        <div class="text-2xl font-semibold font-mono text-[#f7f8f8] tracking-tight">
          6 <span class="text-xs font-normal text-[#5e626e]">{{ t('common.items') }}</span>
        </div>
        <div class="text-[11px] text-[#5e626e] pt-1">
          {{ t('dashboard.proposalsSub') }}
        </div>
      </div>

      <div class="ln-surface p-5 space-y-1">
        <div class="text-xs text-[#8a8f98]">{{ t('dashboard.fbaSavings') }}</div>
        <div class="text-2xl font-semibold font-mono text-emerald-400 tracking-tight">
          +$4.60
        </div>
        <div class="text-[11px] text-[#5e626e] pt-1">
          {{ t('dashboard.fbaSavingsSub') }}
        </div>
      </div>
    </div>

    <!-- Main Content Section: Clean 2-Column Split -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
      <!-- Left Column (7 cols): Top Pain Points Ranked List -->
      <div class="lg:col-span-7 space-y-4">
        <div class="flex items-center justify-between pb-1">
          <h2 class="text-sm font-medium text-[#f7f8f8] tracking-tight">
            {{ t('dashboard.topPainPoints') }}
          </h2>
          <button
            @click="emit('navigate', 'voc')"
            class="text-xs text-[#8a8f98] hover:text-[#f7f8f8] flex items-center gap-1 transition-colors"
          >
            <span>{{ t('dashboard.galleryLink') }}</span>
            <ChevronRight class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- Clean Pain Point List -->
        <div class="ln-surface divide-y divide-[rgba(255,255,255,0.05)] overflow-hidden">
          <div
            v-for="(cluster, idx) in clusters"
            :key="cluster.id"
            class="p-4 hover:bg-[rgba(255,255,255,0.02)] transition-colors cursor-pointer group space-y-2"
            @click="emit('navigate', 'voc')"
          >
            <div class="flex items-center justify-between text-xs">
              <div class="flex items-center gap-2.5">
                <span class="text-xs font-mono text-[#5e626e]">0{{ idx + 1 }}</span>
                <span class="font-medium text-[#f7f8f8] group-hover:text-[#7170ff] transition-colors">
                  {{ cluster.name }}
                </span>
              </div>
              <div class="flex items-center gap-3 font-mono text-[11px] text-[#8a8f98]">
                <span>{{ cluster.frequency }} {{ t('dashboard.frequency') }}</span>
                <span class="text-amber-400">{{ t('dashboard.rating') }} {{ cluster.severity.toFixed(1) }}</span>
              </div>
            </div>

            <!-- Proportion Bar -->
            <div class="w-full bg-[rgba(255,255,255,0.06)] h-1 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full bg-[#7170ff] transition-all"
                :style="{ width: `${cluster.shareRatio * 100}%` }"
              />
            </div>

            <p class="text-[11px] text-[#8a8f98] line-clamp-1">
              "{{ cluster.translatedQuote }}"
            </p>
          </div>
        </div>
      </div>

      <!-- Right Column (5 cols): Decision Status & Tasks -->
      <div class="lg:col-span-5 space-y-6">
        <!-- Decision Gate Mini Card -->
        <div class="ln-surface p-5 space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-[#8a8f98]">{{ t('dashboard.financialStatus') }}</span>
            <span
              v-if="currentTask.status === 'completed'"
              class="flex items-center gap-1.5 text-xs font-mono text-emerald-400"
            >
              <CheckCircle2 class="w-3.5 h-3.5" />
              <span>{{ t('dashboard.approved') }}</span>
            </span>
            <span
              v-else-if="currentTask.status === 'vetoed'"
              class="flex items-center gap-1.5 text-xs font-mono text-rose-400"
            >
              <ShieldAlert class="w-3.5 h-3.5" />
              <span>{{ t('dashboard.vetoed') }}</span>
            </span>
          </div>

          <p class="text-xs text-[#8a8f98] leading-relaxed">
            {{ t('dashboard.financialDesc') }}
          </p>

          <button
            @click="emit('navigate', 'financial')"
            class="w-full py-2 px-3 ln-btn flex items-center justify-center gap-2 text-xs"
          >
            <Sliders class="w-3.5 h-3.5" />
            <span>{{ t('dashboard.adjustSandbox') }}</span>
          </button>
        </div>

        <!-- Monitored ASINs Switcher -->
        <div class="space-y-3">
          <div class="flex items-center justify-between text-xs text-[#8a8f98]">
            <span>{{ t('dashboard.taskList') }}</span>
            <span>{{ allTasks.length }} {{ t('common.items') }}</span>
          </div>

          <div class="ln-surface divide-y divide-[rgba(255,255,255,0.05)] overflow-hidden">
            <div
              v-for="task in allTasks"
              :key="task.id"
              @click="emit('selectTask', task.id)"
              :class="[
                'p-3.5 flex items-center justify-between text-xs cursor-pointer transition-colors',
                currentTask.id === task.id
                  ? 'bg-[rgba(255,255,255,0.04)] text-[#f7f8f8]'
                  : 'hover:bg-[rgba(255,255,255,0.02)] text-[#8a8f98]'
              ]"
            >
              <div class="space-y-0.5">
                <div class="font-mono font-medium text-[#f7f8f8]">{{ task.asin }}</div>
                <div class="text-[11px] text-[#5e626e] line-clamp-1 max-w-[200px]">
                  {{ task.productTitle }}
                </div>
              </div>

              <div class="text-right font-mono text-[11px]">
                <span v-if="task.status === 'completed'" class="text-emerald-400">{{ t('common.completed') }}</span>
                <span v-else-if="task.status === 'vetoed'" class="text-rose-400">{{ t('common.vetoed') }}</span>
                <span v-else class="text-[#7170ff]">{{ t('common.running') }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
