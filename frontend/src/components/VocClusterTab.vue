<script setup lang="ts">
import {
  AlertTriangle,
  Camera,
  ExternalLink,
  Maximize2,
  Sparkles,
  Tag,
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

const selectedCategory = ref<string>('全部');
const activeEvidenceModal = ref<VisualEvidence | null>(null);

const categories = ['全部', '结构强度', '规格公差', '材质升级', '包装与履约', '表面处理'];
</script>

<template>
  <div class="space-y-8">
    <!-- Header Summary -->
    <div class="glass-panel rounded-2xl p-6">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 class="text-lg font-bold text-zinc-100 flex items-center gap-2">
            <Sparkles class="w-5 h-5 text-cyan-400" />
            <span>多模态视觉差评取证与多语言深度 VOC</span>
          </h2>
          <p class="text-xs text-zinc-400 mt-1">
            突破传统文本分词局限：基于 bge-m3 密集语义向量聚类与 Claude Vision 实拍缺陷定位，直击物理缺陷根因。
          </p>
        </div>

        <!-- Filter Pills -->
        <div class="flex items-center gap-1 bg-zinc-900/80 p-1 rounded-xl border border-zinc-800 overflow-x-auto">
          <button
            v-for="cat in categories"
            :key="cat"
            @click="selectedCategory = cat"
            :class="[
              'px-3 py-1 text-xs rounded-lg transition-colors whitespace-nowrap font-medium',
              selectedCategory === cat
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                : 'text-zinc-400 hover:text-zinc-200'
            ]"
          >
            {{ cat }}
          </button>
        </div>
      </div>
    </div>

    <!-- Section 1: bge-m3 Top Pain Point Clusters -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold text-zinc-200 flex items-center gap-2">
          <Tag class="w-4 h-4 text-cyan-400" />
          <span>Top 5 核心质量痛点聚类 (语义归一)</span>
        </h3>
        <span class="text-xs font-mono text-zinc-400">
          基于 pgvector 余弦相似度收敛
        </span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="cluster in clusters"
          :key="cluster.id"
          class="glass-panel glass-panel-hover rounded-xl p-5 space-y-4 flex flex-col justify-between"
        >
          <div class="space-y-3">
            <div class="flex items-center justify-between text-xs">
              <span class="px-2 py-0.5 rounded text-[11px] font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                {{ cluster.category }}
              </span>
              <div class="flex items-center gap-1 text-amber-400 font-mono text-xs">
                <AlertTriangle class="w-3.5 h-3.5" />
                <span>严重度 {{ cluster.severity.toFixed(1) }}</span>
              </div>
            </div>

            <h4 class="text-sm font-bold text-zinc-100 leading-snug">
              {{ cluster.name }}
            </h4>

            <!-- Stats Badge -->
            <div class="flex items-center gap-4 text-xs font-mono text-zinc-400">
              <span>频次: <strong class="text-cyan-400">{{ cluster.frequency }}</strong></span>
              <span>占比: <strong class="text-zinc-200">{{ (cluster.shareRatio * 100).toFixed(1) }}%</strong></span>
              <span>实拍图: <strong class="text-emerald-400">{{ cluster.photoCount }} 张</strong></span>
            </div>

            <!-- Customer Quote -->
            <div class="p-3 rounded-lg bg-zinc-950/70 border border-zinc-800/80 text-xs space-y-1.5">
              <p class="text-zinc-400 italic">"{{ cluster.sampleQuote }}"</p>
              <p class="text-zinc-300 text-[11px] border-t border-zinc-800/80 pt-1.5">
                ↳ 翻译：{{ cluster.translatedQuote }}
              </p>
            </div>
          </div>

          <!-- Bottom Evidence Trigger -->
          <button
            @click="emit('viewClusterEvidence', cluster)"
            class="w-full py-2 px-3 rounded-lg bg-zinc-800/80 hover:bg-zinc-700 text-cyan-300 hover:text-cyan-200 text-xs font-mono flex items-center justify-center gap-1.5 border border-zinc-700 hover:border-cyan-500/40 transition-all"
          >
            <ExternalLink class="w-3.5 h-3.5" />
            <span>查看支撑证据链 ({{ cluster.frequency }} 评论 / {{ cluster.photoCount }} 实拍)</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Section 2: Claude Vision Multimodal Buyer Defect Photos -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-sm font-semibold text-zinc-200 flex items-center gap-2">
            <Camera class="w-4 h-4 text-emerald-400" />
            <span>Claude Vision 买家实拍图物理缺陷取证画廊</span>
          </h3>
          <p class="text-xs text-zinc-400 mt-0.5">
            视觉大模型自动过滤包装垃圾背景，精准定位断裂、破损部位与材料成因
          </p>
        </div>
        <span class="text-xs font-mono text-zinc-400">
          已取证 4 幅高危典型样品
        </span>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          v-for="ev in evidences"
          :key="ev.id"
          class="glass-panel glass-panel-hover rounded-xl overflow-hidden flex flex-col justify-between group"
        >
          <!-- Image Box with Bounding Box Overlay -->
          <div class="relative aspect-4/3 bg-zinc-950 overflow-hidden">
            <img
              :src="ev.imageUrl"
              :alt="ev.title"
              class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 opacity-85 group-hover:opacity-100"
            />

            <!-- Bounding Box Indicator Simulation -->
            <div
              v-if="ev.bbox"
              class="absolute border-2 border-rose-500/90 bg-rose-500/20 rounded shadow-[0_0_10px_rgba(244,63,94,0.5)] pointer-events-none"
              :style="{
                left: `${ev.bbox.x}%`,
                top: `${ev.bbox.y}%`,
                width: `${ev.bbox.w}%`,
                height: `${ev.bbox.h}%`
              }"
            >
              <span class="absolute -top-5 left-0 bg-rose-600 text-white font-mono text-[9px] px-1 py-0.5 rounded shadow">
                DEFECT ({{ (ev.confidence * 100).toFixed(0) }}%)
              </span>
            </div>

            <!-- Inspect Button overlay -->
            <button
              @click="activeEvidenceModal = ev"
              class="absolute bottom-2 right-2 p-1.5 rounded-lg bg-zinc-900/80 backdrop-blur-md border border-zinc-700 text-zinc-200 hover:text-cyan-400 opacity-0 group-hover:opacity-100 transition-opacity"
              title="全屏检视"
            >
              <Maximize2 class="w-3.5 h-3.5" />
            </button>
          </div>

          <!-- Content Details -->
          <div class="p-4 space-y-2.5 flex-1 flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between text-[11px] font-mono text-zinc-400 mb-1">
                <span class="text-rose-400 font-semibold">{{ ev.defectType }}</span>
                <span class="text-cyan-400">置信度: {{ (ev.confidence * 100).toFixed(1) }}%</span>
              </div>

              <h4 class="text-xs font-bold text-zinc-100 leading-snug">
                {{ ev.title }}
              </h4>

              <p class="text-[11px] text-zinc-400 mt-1">
                受损部件: <strong class="text-zinc-300 font-mono">{{ ev.damagedPart }}</strong>
              </p>
            </div>

            <!-- Physical Root Cause Box -->
            <div class="p-2.5 rounded-lg bg-zinc-950/80 border border-zinc-800/80 text-[11px] text-zinc-300 space-y-1">
              <span class="text-cyan-400 font-semibold block text-[10px] uppercase font-mono">物理归因诊断:</span>
              <p class="leading-relaxed text-zinc-400">{{ ev.rootCause }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Fullscreen Modal Viewer for Photo Evidence -->
    <div
      v-if="activeEvidenceModal"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/80 backdrop-blur-md"
      @click.self="activeEvidenceModal = null"
    >
      <div class="glass-panel max-w-2xl w-full rounded-2xl p-6 space-y-4 border border-zinc-700/80 shadow-2xl relative">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold text-zinc-100 flex items-center gap-2">
            <Camera class="w-4 h-4 text-cyan-400" />
            <span>{{ activeEvidenceModal.title }}</span>
          </h3>
          <button
            @click="activeEvidenceModal = null"
            class="text-xs font-mono text-zinc-400 hover:text-zinc-200 px-2 py-1 rounded bg-zinc-800"
          >
            关闭 [ESC]
          </button>
        </div>

        <div class="relative rounded-xl overflow-hidden aspect-video bg-zinc-950">
          <img
            :src="activeEvidenceModal.imageUrl"
            class="w-full h-full object-cover"
          />
          <div
            v-if="activeEvidenceModal.bbox"
            class="absolute border-2 border-rose-500 bg-rose-500/20 rounded shadow-[0_0_20px_rgba(244,63,94,0.6)]"
            :style="{
              left: `${activeEvidenceModal.bbox.x}%`,
              top: `${activeEvidenceModal.bbox.y}%`,
              width: `${activeEvidenceModal.bbox.w}%`,
              height: `${activeEvidenceModal.bbox.h}%`
            }"
          >
            <span class="absolute -top-6 left-0 bg-rose-600 text-white font-mono text-xs px-1.5 py-0.5 rounded shadow">
              {{ activeEvidenceModal.defectType }} · 置信度 {{ (activeEvidenceModal.confidence * 100).toFixed(1) }}%
            </span>
          </div>
        </div>

        <div class="p-4 rounded-xl bg-zinc-900/90 border border-zinc-800 space-y-2 text-xs">
          <div class="grid grid-cols-2 gap-2 text-zinc-300 font-mono text-[11px]">
            <div>受损部位: <span class="text-zinc-100">{{ activeEvidenceModal.damagedPart }}</span></div>
            <div>买家评级: <span class="text-amber-400">★ 1 星差评</span></div>
          </div>
          <div class="text-zinc-300 pt-1 border-t border-zinc-800">
            <strong class="text-cyan-400">物理工程根因：</strong>{{ activeEvidenceModal.rootCause }}
          </div>
          <div class="text-zinc-400 italic pt-1">
            "{{ activeEvidenceModal.reviewText }}"
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
