<script setup lang="ts">
import {
  ExternalLink,
  Maximize2,
} from 'lucide-vue-next';
import { ref } from 'vue';
import type { PainPointCluster, VisualEvidence } from '../types';

defineProps<{
  clusters: PainPointCluster[];
  evidences: VisualEvidence[];
}>();

const emit = defineEmits<{
  (e: 'viewClusterEvidence', cluster: PainPointCluster): void;
  (e: 'viewPhotoDetail', evidence: VisualEvidence): void;
}>();

const activeSubTab = ref<'clusters' | 'visual'>('clusters');
const activeEvidenceModal = ref<VisualEvidence | null>(null);
</script>

<template>
  <div class="space-y-6">
    <!-- Top Header & Sub-View Switcher -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[rgba(255,255,255,0.06)]">
      <div>
        <h1 class="text-xl font-medium tracking-tight text-[#f7f8f8]">
          多模态视觉差评取证与 VOC 深度聚类
        </h1>
        <p class="text-xs text-[#8a8f98] mt-1">
          bge-m3 语义向量归一与 Claude Vision 买家实拍缺陷定位
        </p>
      </div>

      <!-- Segmented Control for Sub-Views -->
      <div class="flex items-center bg-[rgba(255,255,255,0.03)] p-0.5 rounded-lg border border-[rgba(255,255,255,0.07)]">
        <button
          @click="activeSubTab = 'clusters'"
          :class="[
            'px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
            activeSubTab === 'clusters'
              ? 'bg-[rgba(255,255,255,0.08)] text-[#f7f8f8]'
              : 'text-[#8a8f98] hover:text-[#f7f8f8]'
          ]"
        >
          痛点聚类 (Top 5)
        </button>
        <button
          @click="activeSubTab = 'visual'"
          :class="[
            'px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
            activeSubTab === 'visual'
              ? 'bg-[rgba(255,255,255,0.08)] text-[#f7f8f8]'
              : 'text-[#8a8f98] hover:text-[#f7f8f8]'
          ]"
        >
          买家实拍取证 (4 样本)
        </button>
      </div>
    </div>

    <!-- View 1: Pain Point Clusters (Clean, spacious list) -->
    <div v-if="activeSubTab === 'clusters'" class="space-y-4">
      <div class="ln-surface divide-y divide-[rgba(255,255,255,0.05)] overflow-hidden">
        <div
          v-for="(cluster, idx) in clusters"
          :key="cluster.id"
          class="p-5 hover:bg-[rgba(255,255,255,0.02)] transition-colors space-y-3"
        >
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div class="flex items-center gap-3">
              <span class="text-xs font-mono text-[#5e626e]">0{{ idx + 1 }}</span>
              <span class="text-sm font-medium text-[#f7f8f8]">{{ cluster.name }}</span>
              <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-[rgba(255,255,255,0.04)] text-[#8a8f98] border border-[rgba(255,255,255,0.06)]">
                {{ cluster.category }}
              </span>
            </div>

            <div class="flex items-center gap-4 text-xs font-mono text-[#8a8f98]">
              <span>频次: <strong class="text-[#f7f8f8]">{{ cluster.frequency }}</strong></span>
              <span>占比: {{ (cluster.shareRatio * 100).toFixed(1) }}%</span>
              <span class="text-amber-400">严重度: {{ cluster.severity.toFixed(1) }}</span>
            </div>
          </div>

          <!-- Customer Voice Translated -->
          <p class="text-xs text-[#8a8f98] pl-6 leading-relaxed">
            "{{ cluster.translatedQuote }}"
          </p>

          <div class="pl-6 pt-1 flex items-center justify-between">
            <span class="text-[11px] font-mono text-[#5e626e]">
              包含 {{ cluster.photoCount }} 张买家实拍缺陷图片
            </span>
            <button
              @click="emit('viewClusterEvidence', cluster)"
              class="text-xs font-mono text-[#7170ff] hover:text-[#828fff] flex items-center gap-1 transition-colors"
            >
              <span>查看支撑证据链</span>
              <ExternalLink class="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- View 2: Claude Vision Real Buyer Defect Photos -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
      <div
        v-for="ev in evidences"
        :key="ev.id"
        class="ln-surface overflow-hidden group"
      >
        <!-- Photo Container -->
        <div class="relative aspect-video bg-[#050607] overflow-hidden">
          <img
            :src="ev.imageUrl"
            :alt="ev.title"
            class="w-full h-full object-cover group-hover:scale-102 transition-transform duration-300"
          />

          <!-- Discreet Defect Tag -->
          <div class="absolute top-3 left-3 bg-[#08090a]/85 backdrop-blur-md px-2.5 py-1 rounded border border-[rgba(255,255,255,0.1)] text-[11px] font-mono text-[#f7f8f8]">
            {{ ev.defectType }} · {{ (ev.confidence * 100).toFixed(0) }}% 置信度
          </div>

          <!-- Fullscreen Inspect Button -->
          <button
            @click="activeEvidenceModal = ev"
            class="absolute bottom-3 right-3 p-1.5 rounded-md bg-[#08090a]/80 border border-[rgba(255,255,255,0.1)] text-[#8a8f98] hover:text-[#f7f8f8] transition-colors"
          >
            <Maximize2 class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- Details -->
        <div class="p-4 space-y-2">
          <div class="flex items-center justify-between text-xs">
            <h3 class="font-medium text-[#f7f8f8]">{{ ev.title }}</h3>
            <span class="text-[11px] font-mono text-[#5e626e]">{{ ev.damagedPart }}</span>
          </div>

          <p class="text-xs text-[#8a8f98] leading-relaxed">
            <span class="text-zinc-400 font-medium">成因诊断：</span>{{ ev.rootCause }}
          </p>

          <p class="text-[11px] text-[#5e626e] italic pt-1">
            "{{ ev.reviewText }}"
          </p>
        </div>
      </div>
    </div>

    <!-- Simple Image Modal -->
    <div
      v-if="activeEvidenceModal"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
      @click.self="activeEvidenceModal = null"
    >
      <div class="ln-surface max-w-xl w-full p-5 space-y-3 bg-[#0f1011]">
        <div class="flex items-center justify-between text-xs pb-2 border-b border-[rgba(255,255,255,0.06)]">
          <span class="font-medium text-[#f7f8f8]">{{ activeEvidenceModal.title }}</span>
          <button @click="activeEvidenceModal = null" class="text-[#8a8f98] hover:text-[#f7f8f8]">
            关闭
          </button>
        </div>

        <img :src="activeEvidenceModal.imageUrl" class="w-full aspect-video object-cover rounded-lg" />

        <div class="text-xs text-[#8a8f98] space-y-1">
          <div><strong class="text-[#f7f8f8]">物理归因：</strong>{{ activeEvidenceModal.rootCause }}</div>
          <div class="italic text-[11px]">"{{ activeEvidenceModal.reviewText }}"</div>
        </div>
      </div>
    </div>
  </div>
</template>
