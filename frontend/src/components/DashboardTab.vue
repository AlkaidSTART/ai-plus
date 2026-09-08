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
</script>

<template>
  <div class="space-y-8">
    <!-- Clean Product Header & Title (Single breathing row) -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[rgba(255,255,255,0.06)]">
      <div class="space-y-1.5 max-w-3xl">
        <div class="flex items-center gap-2 text-xs font-mono text-[#8a8f98]">
          <span>{{ currentTask.asin }}</span>
          <span>·</span>
          <span>{{ currentTask.marketplace }} 站点</span>
          <span>·</span>
          <span>BSR #{{ currentTask.bsr }}</span>
          <span>·</span>
          <span>{{ currentTask.reviewCount.toLocaleString() }} 评价</span>
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
          <span>查看改款方案</span>
          <ArrowRight class="w-3.5 h-3.5 opacity-70" />
        </button>

        <button
          @click="emit('navigate', 'agent')"
          class="ln-btn px-3.5 py-2 flex items-center gap-2"
        >
          <Play class="w-3.5 h-3.5 text-zinc-400" />
          <span>运行新诊断</span>
        </button>
      </div>
    </div>

    <!-- 4 Clean, Quiet KPI Cards (Generous breathing room, no noise) -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="ln-surface p-5 space-y-1">
        <div class="text-xs text-[#8a8f98]">样本差评率</div>
        <div class="text-2xl font-semibold font-mono text-[#f7f8f8] tracking-tight">
          {{ (currentTask.negativeRate * 100).toFixed(1) }}%
        </div>
        <div class="text-[11px] text-[#5e626e] pt-1">
          共识别 645 条低星缺陷样本
        </div>
      </div>

      <div class="ln-surface p-5 space-y-1">
        <div class="text-xs text-[#8a8f98]">峰值痛点严重度</div>
        <div class="text-2xl font-semibold font-mono text-amber-400 tracking-tight">
          4.8 <span class="text-xs font-normal text-[#5e626e]">/ 5.0</span>
        </div>
        <div class="text-[11px] text-[#5e626e] pt-1">
          PA6 扶手支架应力集中断裂
        </div>
      </div>

      <div class="ln-surface p-5 space-y-1">
        <div class="text-xs text-[#8a8f98]">双栏可执行改款</div>
        <div class="text-2xl font-semibold font-mono text-[#f7f8f8] tracking-tight">
          6 <span class="text-xs font-normal text-[#5e626e]">项</span>
        </div>
        <div class="text-[11px] text-[#5e626e] pt-1">
          3 物理本体 + 3 包装降规方案
        </div>
      </div>

      <div class="ln-surface p-5 space-y-1">
        <div class="text-xs text-[#8a8f98]">单件 FBA 预期降本</div>
        <div class="text-2xl font-semibold font-mono text-emerald-400 tracking-tight">
          +$4.60
        </div>
        <div class="text-[11px] text-[#5e626e] pt-1">
          外箱尺寸降阶，预计年省 $46,000
        </div>
      </div>
    </div>

    <!-- Main Content Section: Clean 2-Column Split -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
      <!-- Left Column (7 cols): Top Pain Points Ranked List -->
      <div class="lg:col-span-7 space-y-4">
        <div class="flex items-center justify-between pb-1">
          <h2 class="text-sm font-medium text-[#f7f8f8] tracking-tight">
            核心质量与使用痛点聚类 (Top 5)
          </h2>
          <button
            @click="emit('navigate', 'voc')"
            class="text-xs text-[#8a8f98] hover:text-[#f7f8f8] flex items-center gap-1 transition-colors"
          >
            <span>视觉取证画廊</span>
            <ChevronRight class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- Clean Pain Point List (Table/Row format instead of bulky cards) -->
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
                <span>{{ cluster.frequency }} 次</span>
                <span class="text-amber-400">评级 {{ cluster.severity.toFixed(1) }}</span>
              </div>
            </div>

            <!-- Quiet Proportion Bar -->
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
            <span class="text-xs font-medium text-[#8a8f98]">逆向财务熔断状态</span>
            <span
              v-if="currentTask.status === 'completed'"
              class="flex items-center gap-1.5 text-xs font-mono text-emerald-400"
            >
              <CheckCircle2 class="w-3.5 h-3.5" />
              <span>准予立项开模</span>
            </span>
            <span
              v-else-if="currentTask.status === 'vetoed'"
              class="flex items-center gap-1.5 text-xs font-mono text-rose-400"
            >
              <ShieldAlert class="w-3.5 h-3.5" />
              <span>触发熔断否决</span>
            </span>
          </div>

          <p class="text-xs text-[#8a8f98] leading-relaxed">
            开模摊销 $4.00/件，物流包装 Tier Down 降本 $4.60/件，单件净毛利保持健康，回本周期 3.8 个月。
          </p>

          <button
            @click="emit('navigate', 'financial')"
            class="w-full py-2 px-3 ln-btn flex items-center justify-center gap-2 text-xs"
          >
            <Sliders class="w-3.5 h-3.5" />
            <span>调整财务与供应链沙盒</span>
          </button>
        </div>

        <!-- Monitored ASINs Switcher -->
        <div class="space-y-3">
          <div class="flex items-center justify-between text-xs text-[#8a8f98]">
            <span>所有任务列表</span>
            <span>{{ allTasks.length }} 个记录</span>
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
                <span v-if="task.status === 'completed'" class="text-emerald-400">完成</span>
                <span v-else-if="task.status === 'vetoed'" class="text-rose-400">熔断</span>
                <span v-else class="text-[#7170ff]">计算中</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
