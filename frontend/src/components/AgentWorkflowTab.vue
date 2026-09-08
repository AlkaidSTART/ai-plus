<script setup lang="ts">
import {
  Activity,
  Check,
  ChevronRight,
  Pause,
  Play,
  RotateCcw,
  Terminal,
  X,
} from 'lucide-vue-next';
import { onBeforeUnmount, ref } from 'vue';
import type { AgentNode, InsightTask, Marketplace } from '../types';

const props = defineProps<{
  currentTask: InsightTask;
}>();

const emit = defineEmits<{
  (e: 'taskUpdated', task: InsightTask): void;
}>();

const inputAsin = ref(props.currentTask.asin);
const selectedMarketplace = ref<Marketplace>(props.currentTask.marketplace);
const isStreaming = ref(false);
const activeNodeKey = ref<AgentNode>('dual_column_proposal');

const streamLogs = ref<string[]>([
  `09:20:15 [INIT] InsightX LangGraph runtime ready`,
  `09:20:16 [INGESTION] Connected to Amazon (${props.currentTask.marketplace})`,
  `09:20:17 [INGESTION] Fetched 3,840 reviews and 142 customer photos`,
  `09:20:18 [CLUSTERING] bge-m3 1024-dim embedding converged (5 clusters)`,
  `09:20:20 [VLM] Claude Vision identified shear crack on armrest ratchet`,
  `09:20:22 [PROPOSAL] Formulated dual-column RFC (3 physical, 3 packaging)`,
  `09:20:23 [FINANCIAL] Payback 3.8 months < threshold. Gate: APPROVED`,
]);

let timer: number | null = null;

const runSimulation = () => {
  if (isStreaming.value) return;
  isStreaming.value = true;
  streamLogs.value = [
    `10:00:00 [INIT] Launching pipeline for ASIN ${inputAsin.value} (${selectedMarketplace.value})`,
    `10:00:01 [INGESTION] Ingesting verified reviews & metadata...`,
  ];

  const clone = JSON.parse(JSON.stringify(props.currentTask)) as InsightTask;
  clone.status = 'running';
  clone.progress = 10;
  clone.nodes.forEach(n => (n.status = 'idle'));
  clone.nodes[0].status = 'running';
  activeNodeKey.value = 'ingestion';
  emit('taskUpdated', clone);

  let step = 0;
  timer = window.setInterval(() => {
    step++;
    if (step === 1) {
      streamLogs.value.push(`10:00:02 [INGESTION] Harvested 2,840 reviews, 142 defect images`);
      streamLogs.value.push(`10:00:03 [CLUSTERING] Running bge-m3 dense vector clustering...`);
      clone.nodes[0].status = 'completed';
      clone.nodes[1].status = 'running';
      clone.progress = 35;
      clone.currentNode = 'clustering';
      activeNodeKey.value = 'clustering';
      emit('taskUpdated', { ...clone });
    } else if (step === 2) {
      streamLogs.value.push(`10:00:04 [CLUSTERING] Extracted Top 5 mechanical & usability clusters`);
      streamLogs.value.push(`10:00:05 [VLM] Claude Vision running defect inspection on photos...`);
      clone.nodes[1].status = 'completed';
      clone.nodes[2].status = 'running';
      clone.progress = 60;
      clone.currentNode = 'vlm_inspection';
      activeNodeKey.value = 'vlm_inspection';
      emit('taskUpdated', { ...clone });
    } else if (step === 3) {
      streamLogs.value.push(`10:00:06 [VLM] Pinpointed brittle fatigue failure on PA6-GF component (98.2% conf)`);
      streamLogs.value.push(`10:00:07 [PROPOSAL] Dual-column engine calculating physical & tier-down specs...`);
      clone.nodes[2].status = 'completed';
      clone.nodes[3].status = 'running';
      clone.progress = 85;
      clone.currentNode = 'dual_column_proposal';
      activeNodeKey.value = 'dual_column_proposal';
      emit('taskUpdated', { ...clone });
    } else if (step >= 4) {
      if (timer) clearInterval(timer);
      isStreaming.value = false;
      clone.nodes[3].status = 'completed';
      clone.nodes[4].status = 'completed';
      clone.status = 'completed';
      clone.progress = 100;
      clone.currentNode = 'financial_veto';
      activeNodeKey.value = 'financial_veto';
      streamLogs.value.push(`10:00:08 [FINANCIAL] Payback 3.8 mo < 6.0 mo threshold. Veto Gate: APPROVED`);
      streamLogs.value.push(`10:00:09 [COMPLETE] Agent pipeline finished execution`);
      emit('taskUpdated', { ...clone });
    }
  }, 1400);
};

const stopSimulation = () => {
  if (timer) clearInterval(timer);
  isStreaming.value = false;
  streamLogs.value.push(`[PAUSE] Execution stopped by user`);
};

onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
});
</script>

<template>
  <div class="space-y-8">
    <!-- Top Action Bar -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[rgba(255,255,255,0.06)]">
      <div class="space-y-1">
        <h1 class="text-xl font-medium tracking-tight text-[#f7f8f8]">
          LangGraph 多智能体诊断流程
        </h1>
        <p class="text-xs text-[#8a8f98]">
          数据采集、语义聚类、视觉取证、双栏改款与逆向风控 5 节点闭环编排
        </p>
      </div>

      <!-- Execution Controls -->
      <div class="flex items-center gap-2">
        <div class="flex items-center gap-2">
          <input
            v-model="inputAsin"
            type="text"
            class="bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] rounded-md px-2.5 py-1.5 text-xs font-mono text-[#f7f8f8] w-32 focus:outline-none focus:border-[rgba(255,255,255,0.2)]"
            placeholder="ASIN"
          />

          <select
            v-model="selectedMarketplace"
            class="bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] rounded-md px-2 py-1.5 text-xs font-mono text-[#8a8f98] focus:outline-none cursor-pointer"
          >
            <option value="US">US</option>
            <option value="DE">DE</option>
            <option value="JP">JP</option>
            <option value="UK">UK</option>
          </select>
        </div>

        <button
          v-if="!isStreaming"
          @click="runSimulation"
          class="ln-btn-primary px-3.5 py-1.5 flex items-center gap-1.5"
        >
          <Play class="w-3 h-3 fill-current" />
          <span>执行流程</span>
        </button>

        <button
          v-else
          @click="stopSimulation"
          class="ln-btn px-3.5 py-1.5 flex items-center gap-1.5 text-amber-400"
        >
          <Pause class="w-3 h-3 fill-current" />
          <span>暂停</span>
        </button>

        <button
          @click="runSimulation"
          class="p-1.5 ln-btn"
          title="重试"
        >
          <RotateCcw class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>

    <!-- Minimalist Horizontal Stepper (Clean Linear timeline) -->
    <div class="ln-surface p-4 sm:p-5">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div
          v-for="(node, idx) in currentTask.nodes"
          :key="node.key"
          @click="activeNodeKey = node.key"
          :class="[
            'flex items-center gap-3 cursor-pointer py-1 px-2 rounded-md transition-colors',
            activeNodeKey === node.key
              ? 'bg-[rgba(255,255,255,0.05)]'
              : 'hover:bg-[rgba(255,255,255,0.02)]'
          ]"
        >
          <!-- Status Indicator Dot -->
          <div class="flex items-center justify-center w-5 h-5 rounded-full border border-[rgba(255,255,255,0.1)] shrink-0">
            <Check v-if="node.status === 'completed'" class="w-3 h-3 text-emerald-400" />
            <Activity v-else-if="node.status === 'running'" class="w-3 h-3 text-[#7170ff] animate-spin" />
            <X v-else-if="node.status === 'vetoed'" class="w-3 h-3 text-rose-400" />
            <span v-else class="text-[10px] font-mono text-[#5e626e]">{{ idx + 1 }}</span>
          </div>

          <div class="space-y-0.5">
            <div
              :class="[
                'text-xs font-medium',
                activeNodeKey === node.key ? 'text-[#f7f8f8]' : 'text-[#8a8f98]'
              ]"
            >
              {{ node.name }}
            </div>
            <div class="text-[10px] font-mono text-[#5e626e]">
              {{ node.durationMs ? `${node.durationMs}ms` : '就绪' }}
            </div>
          </div>

          <ChevronRight
            v-if="idx < currentTask.nodes.length - 1"
            class="hidden md:block w-3.5 h-3.5 text-zinc-700 ml-auto"
          />
        </div>
      </div>
    </div>

    <!-- 2-Column Split: Node State Inspector & Event Stream -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
      <!-- Node Inspector Card -->
      <div class="ln-surface p-5 space-y-3">
        <div class="flex items-center justify-between text-xs pb-2 border-b border-[rgba(255,255,255,0.06)]">
          <span class="font-medium text-[#f7f8f8]">节点状态检视</span>
          <span class="font-mono text-[#8a8f98]">Node: {{ activeNodeKey }}</span>
        </div>

        <div class="text-xs font-mono space-y-2 text-[#8a8f98] pt-1">
          <div v-if="activeNodeKey === 'ingestion'" class="space-y-1.5">
            <div class="text-[#f7f8f8]">数据采集源：Amazon {{ currentTask.marketplace }}</div>
            <div>• 清洗评论样本：3,840 条</div>
            <div>• 买家缺陷实拍：142 张</div>
            <div>• 类目排名：BSR #{{ currentTask.bsr }}</div>
          </div>

          <div v-else-if="activeNodeKey === 'clustering'" class="space-y-1.5">
            <div class="text-[#f7f8f8]">模型：bge-m3 (Dense 1024-d 向量)</div>
            <div>• 归纳痛点聚类：Top 5</div>
            <div>• 峰值质量抱怨：3D 扶手卡扣脆断 (占比 38.5%)</div>
            <div>• 多语言对齐：EN / DE / JA 映射至统一中文本体</div>
          </div>

          <div v-else-if="activeNodeKey === 'vlm_inspection'" class="space-y-1.5">
            <div class="text-[#f7f8f8]">多模态视觉：Claude 3.5 Sonnet Vision</div>
            <div>• 视觉定位样本：89 处机械损坏特征</div>
            <div>• 物理成因：PA6+GF 倒角 R 角过小，剪切应力集中</div>
          </div>

          <div v-else-if="activeNodeKey === 'dual_column_proposal'" class="space-y-1.5">
            <div class="text-[#f7f8f8]">改款决策：双栏工程方案已就绪</div>
            <div>• 产品本体：Zamak-3 锌合金骨架 + 硅胶阻尼滚轮</div>
            <div>• 包装履约：外箱长边缩减 6.5cm，规避超规 FBA 费用</div>
          </div>

          <div v-else class="space-y-1.5">
            <div class="text-emerald-400">逆向风控状态：APPROVED (通过)</div>
            <div>• 开模总费用：$12,000 USD</div>
            <div>• 预计回本周期：3.8 个月 (安全阈值: 6.0 个月)</div>
            <div>• 决议建议：准予立项开模</div>
          </div>
        </div>
      </div>

      <!-- Realtime Event Stream Log Terminal -->
      <div class="ln-surface p-5 space-y-3">
        <div class="flex items-center justify-between text-xs pb-2 border-b border-[rgba(255,255,255,0.06)]">
          <div class="flex items-center gap-1.5 text-[#f7f8f8] font-medium">
            <Terminal class="w-3.5 h-3.5 text-[#8a8f98]" />
            <span>实时事件日志</span>
          </div>
          <span class="text-[11px] font-mono text-[#5e626e]">SSE 直连</span>
        </div>

        <div class="h-48 overflow-y-auto space-y-1.5 font-mono text-[11px] text-[#8a8f98] scrollbar-thin select-text">
          <div
            v-for="(log, i) in streamLogs"
            :key="i"
            :class="[
              log.includes('APPROVED')
                ? 'text-emerald-400 font-medium'
                : log.includes('VETOED')
                  ? 'text-rose-400 font-medium'
                  : 'text-[#8a8f98]'
            ]"
          >
            {{ log }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
