<script setup lang="ts">
import gsap from 'gsap';
import {
  ArrowRight,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Layers,
  LogIn,
  Pause,
  Play,
  Scan,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Wrench,
} from 'lucide-vue-next';
import { onBeforeUnmount, onMounted, ref } from 'vue';
import productLogo from '../assets/Product_logo.webp';

const emit = defineEmits<{
  (e: 'enter'): void;
  (e: 'openAuth'): void;
}>();

const containerRef = ref<HTMLElement | null>(null);
const cardsContainerRef = ref<HTMLElement | null>(null);
const progressBarRef = ref<HTMLElement | null>(null);

const activeIndex = ref(0);
const isAutoPlaying = ref(true);

const CARD_DURATION = 4.2; // seconds per card

const features = [
  {
    id: 0,
    tag: 'PILLAR 01 · SPATIO-TEMPORAL',
    icon: Layers,
    title: '跨平台全景时序穿透',
    tagline: 'Amazon · TikTok Shop · Temu 同品类动态对齐',
    summary: '消除跨境卖家在多款独立软件之间拼凑 Excel 的痛苦。打通三大出海平台同款 SKU，分钟级监控价格异动、排名跳变与流量套利空间。',
    accentColor: '#7170ff',
    badge: '3,840+ 样本分钟级对齐',
  },
  {
    id: 1,
    tag: 'PILLAR 02 · MULTIMODAL FORENSICS',
    icon: Sparkles,
    title: '多模态视觉差评取证',
    tagline: 'Claude Vision 直接从买家实拍图定位结构破损',
    summary: '突破传统 VOC 纯文本分词无法识别实拍图的死结。自动过滤无关背景，提取零件剪切脆断、高温软化与外箱跌落挤压的物理级证据链。',
    accentColor: '#06b6d4',
    badge: '98.2% 物理缺陷定位置信度',
  },
  {
    id: 2,
    tag: 'PILLAR 03 · DUAL-COLUMN REDESIGN',
    icon: Wrench,
    title: '工厂级“双栏改款”决策',
    tagline: '左栏改硬件本体，右栏降包装物流 FBA 费用',
    summary: '拒绝市面工具空洞的“建议提升质量”。自动拆解为左栏合金替换与防呆开模清单，右栏包装尺寸降阶 (Tier Down) 避开超规 FBA 费用。',
    accentColor: '#10b981',
    badge: '单件物流净省 $4.60 / 年省 $46,000',
  },
  {
    id: 3,
    tag: 'PILLAR 04 · REVERSE FINANCIAL VETO',
    icon: ShieldCheck,
    title: '逆向财务与现金流熔断',
    tagline: '不仅推改款，更在盲目开模与内卷前理性叫停',
    summary: '内嵌模具费、起订量 (MOQ) 与回本周期模型。当预期回本周期超过品类销售半衰期或毛利侵蚀过大时，直接触发强制熔断，守住现金流底线。',
    accentColor: '#f43f5e',
    badge: '历史时间切片回测吻合度 93.6%',
  },
];

let ctx: gsap.Context | null = null;
let progressTween: gsap.core.Tween | null = null;
let tiltX: ((val: number) => void) | null = null;
let tiltY: ((val: number) => void) | null = null;

// Silky 3D transform layout for all 4 cards simultaneously
const updateCardsLayout = (direction: 'next' | 'prev' = 'next') => {
  if (!cardsContainerRef.value) return;
  const cards = cardsContainerRef.value.querySelectorAll<HTMLElement>('.deck-card-item');

  cards.forEach((card, idx) => {
    // Relative offset in cyclical loop: -1 (outgoing), 0 (active), 1 (next), 2 (last)
    let offset = idx - activeIndex.value;
    if (offset < -1) offset += features.length;
    if (offset > 2) offset -= features.length;

    const isCenter = offset === 0;

    let targetZ = 0;
    let targetX = 0;
    let targetY = 0;
    let targetRotY = 0;
    let targetScale = 1;
    let targetOpacity = 1;
    let zIndex = 10;

    if (isCenter) {
      targetZ = 0;
      targetX = 0;
      targetY = 0;
      targetRotY = 0;
      targetScale = 1;
      targetOpacity = 1;
      zIndex = 20;
    } else if (offset === 1) {
      targetZ = -140;
      targetX = 64;
      targetY = 16;
      targetRotY = -8;
      targetScale = 0.92;
      targetOpacity = 0.65;
      zIndex = 15;
    } else if (offset === 2) {
      targetZ = -260;
      targetX = 120;
      targetY = 32;
      targetRotY = -14;
      targetScale = 0.84;
      targetOpacity = 0.35;
      zIndex = 10;
    } else {
      // Outgoing card (offset < 0): flies past viewer smoothly
      targetZ = 200;
      targetX = direction === 'next' ? -90 : 90;
      targetY = -30;
      targetRotY = direction === 'next' ? 12 : -12;
      targetScale = 1.08;
      targetOpacity = 0;
      zIndex = 5;
    }

    gsap.to(card, {
      x: targetX,
      y: targetY,
      z: targetZ,
      rotationY: targetRotY,
      scale: targetScale,
      opacity: targetOpacity,
      duration: 0.7,
      ease: 'power3.out',
      overwrite: 'auto',
    });

    card.style.zIndex = `${zIndex}`;
    card.style.pointerEvents = isCenter ? 'auto' : 'none';
  });

  restartProgressBar();
};

const restartProgressBar = () => {
  if (!progressBarRef.value) return;
  progressTween?.kill();

  if (!isAutoPlaying.value) {
    gsap.set(progressBarRef.value, { scaleX: 0 });
    return;
  }

  gsap.set(progressBarRef.value, { scaleX: 0, transformOrigin: 'left center' });
  progressTween = gsap.to(progressBarRef.value, {
    scaleX: 1,
    duration: CARD_DURATION,
    ease: 'none',
    onComplete: () => {
      goToNext();
    },
  });
};

const goToNext = () => {
  activeIndex.value = (activeIndex.value + 1) % features.length;
  updateCardsLayout('next');
};

const goToPrev = () => {
  activeIndex.value = (activeIndex.value - 1 + features.length) % features.length;
  updateCardsLayout('prev');
};

const goToIndex = (index: number) => {
  if (index === activeIndex.value) return;
  const dir = index > activeIndex.value ? 'next' : 'prev';
  activeIndex.value = index;
  updateCardsLayout(dir);
};

const toggleAutoPlay = () => {
  isAutoPlaying.value = !isAutoPlaying.value;
  if (isAutoPlaying.value) {
    restartProgressBar();
  } else {
    progressTween?.pause();
    if (progressBarRef.value) {
      gsap.to(progressBarRef.value, { scaleX: 0, duration: 0.2 });
    }
  }
};

const handleCardMouseEnter = () => {
  if (isAutoPlaying.value) {
    progressTween?.pause();
  }
};

const handleCardMouseLeave = () => {
  if (isAutoPlaying.value) {
    progressTween?.resume();
  }
  // Reset mouse tilt smoothly
  if (cardsContainerRef.value) {
    gsap.to(cardsContainerRef.value, {
      rotationX: 0,
      rotationY: 0,
      duration: 0.6,
      ease: 'power2.out',
    });
  }
};

const handleMouseMove = (e: MouseEvent) => {
  if (!cardsContainerRef.value || !tiltX || !tiltY) return;
  const rect = cardsContainerRef.value.getBoundingClientRect();
  const centerX = rect.left + rect.width / 2;
  const centerY = rect.top + rect.height / 2;
  const offsetX = (e.clientX - centerX) / (rect.width / 2);
  const offsetY = (e.clientY - centerY) / (rect.height / 2);

  tiltX(offsetY * -5);
  tiltY(offsetX * 5);
};

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
    goToNext();
  } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
    goToPrev();
  } else if (e.key === 'Enter') {
    emit('enter');
  }
};

onMounted(() => {
  window.addEventListener('keydown', handleKeydown);

  ctx = gsap.context(() => {
    // QuickTo for ultra-smooth 120fps mouse parallax without creating new tweens
    if (cardsContainerRef.value) {
      tiltX = gsap.quickTo(cardsContainerRef.value, 'rotationX', { duration: 0.4, ease: 'power2.out' });
      tiltY = gsap.quickTo(cardsContainerRef.value, 'rotationY', { duration: 0.4, ease: 'power2.out' });
    }

    // High-end entrance choreography
    const entranceTl = gsap.timeline();

    entranceTl.from('.cinematic-header', {
      y: -16,
      opacity: 0,
      duration: 0.6,
      ease: 'power2.out',
    });

    entranceTl.from(
      '.cinematic-title',
      {
        y: 28,
        opacity: 0,
        duration: 0.7,
        stagger: 0.1,
        ease: 'power3.out',
      },
      '-=0.3'
    );

    entranceTl.from(
      '.deck-card-item',
      {
        z: -300,
        scale: 0.8,
        opacity: 0,
        duration: 0.8,
        stagger: 0.08,
        ease: 'power3.out',
        onComplete: () => {
          updateCardsLayout();
        },
      },
      '-=0.4'
    );

    entranceTl.from(
      '.cinematic-controls',
      {
        y: 16,
        opacity: 0,
        duration: 0.5,
        ease: 'power2.out',
      },
      '-=0.3'
    );
  }, containerRef.value || undefined);
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown);
  progressTween?.kill();
  ctx?.revert();
});
</script>

<template>
  <div
    ref="containerRef"
    class="fixed inset-0 z-50 flex flex-col justify-between bg-[#07080a] text-[#f7f8f8] overflow-hidden select-none"
    @mousemove="handleMouseMove"
  >
    <!-- Background Texture: Architectural Subtle Grid & Quiet Ambient Blur -->
    <div class="absolute inset-0 pointer-events-none">
      <div class="absolute inset-0 opacity-[0.08] bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:32px_32px]" />
      <div class="absolute top-1/4 left-1/2 -translate-x-1/2 w-[720px] h-[360px] bg-[#5e6ad2]/10 rounded-full blur-[140px]" />
    </div>

    <!-- Top Minimalist Bar -->
    <header class="cinematic-header relative z-20 max-w-6xl mx-auto w-full px-6 py-5 flex items-center justify-between border-b border-[rgba(255,255,255,0.06)]">
      <div class="flex items-center gap-3">
        <img :src="productLogo" alt="InsightX" class="h-8 w-auto object-contain" />
        <span class="text-zinc-600 font-mono">/</span>
        <span class="text-[11px] font-mono tracking-wider text-[#8a8f98] uppercase">
          Cross-Border AI Decision System
        </span>
      </div>

      <div class="flex items-center gap-3">
        <button
          @click="emit('openAuth')"
          class="ln-btn px-3.5 py-1.5 flex items-center gap-1.5 text-xs text-[#d0d6e0] hover:text-white"
        >
          <LogIn class="w-3.5 h-3.5" />
          <span>体验角色登录</span>
        </button>

        <button
          @click="emit('enter')"
          class="ln-btn-primary px-3.5 py-1.5 flex items-center gap-1.5 text-xs font-medium"
        >
          <span>进入系统大盘</span>
          <ArrowRight class="w-3.5 h-3.5" />
        </button>
      </div>
    </header>

    <!-- Center Stage -->
    <main class="relative z-20 max-w-5xl mx-auto w-full px-6 flex flex-col items-center justify-center flex-1 py-4">
      <!-- Title Block -->
      <div class="text-center space-y-2 mb-6 max-w-2xl">
        <div class="cinematic-title inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] text-[11px] font-mono text-[#8a8f98]">
          <span class="w-1.5 h-1.5 rounded-full bg-[#7170ff] animate-pulse" />
          <span>工贸一体出海专属 · 拒绝盲目跟风开模</span>
        </div>

        <h1 class="cinematic-title text-2xl sm:text-4xl font-semibold tracking-tight text-[#f7f8f8] leading-tight">
          从海量差评取证，到工厂工程图纸
        </h1>

        <p class="cinematic-title text-xs sm:text-sm text-[#8a8f98] max-w-lg mx-auto leading-relaxed">
          基于多模态视觉定损与双栏改款决策，为跨境制造交付工程级立项清单与财务熔断。
        </p>
      </div>

      <!-- 3D Card Stack Container (All 4 cards rendered together for silky GPU transform) -->
      <div
        ref="cardsContainerRef"
        @mouseenter="handleCardMouseEnter"
        @mouseleave="handleCardMouseLeave"
        class="relative w-full max-w-2xl h-[380px] sm:h-[400px] flex items-center justify-center [perspective:1400px] [transform-style:preserve-3d]"
        style="will-change: transform;"
      >
        <!-- Card 0: Spatio-Temporal Ingestion -->
        <div
          class="deck-card-item absolute inset-0 rounded-2xl bg-[#0d0e12]/95 border border-[rgba(255,255,255,0.14)] p-6 sm:p-7 flex flex-col justify-between overflow-hidden shadow-[0_25px_60px_rgba(0,0,0,0.8),inset_0_1px_0_rgba(255,255,255,0.15)] backdrop-blur-xl"
          style="will-change: transform, opacity;"
        >
          <!-- Top progress line on active card -->
          <div
            v-if="activeIndex === 0"
            ref="progressBarRef"
            class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-[#7170ff] to-[#06b6d4] origin-left"
          />

          <!-- Header -->
          <div class="flex items-center justify-between pb-3 border-b border-[rgba(255,255,255,0.06)]">
            <div class="flex items-center gap-2.5">
              <div class="p-2 rounded-xl bg-[#7170ff]/15 border border-[#7170ff]/30 text-[#7170ff]">
                <Layers class="w-4 h-4" />
              </div>
              <div>
                <span class="text-[10px] font-mono tracking-widest font-semibold block text-[#7170ff] uppercase">
                  {{ features[0].tag }}
                </span>
                <h3 class="text-base font-semibold text-[#f7f8f8] tracking-tight">
                  {{ features[0].title }}
                </h3>
              </div>
            </div>
            <span class="text-[11px] font-mono px-2.5 py-1 rounded-full bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-zinc-300">
              {{ features[0].badge }}
            </span>
          </div>

          <!-- Body -->
          <div class="py-3 flex-1 flex flex-col justify-center space-y-3">
            <div class="space-y-1">
              <h4 class="text-xs sm:text-sm font-semibold text-zinc-200">
                {{ features[0].tagline }}
              </h4>
              <p class="text-xs text-[#8a8f98] leading-relaxed">
                {{ features[0].summary }}
              </p>
            </div>

            <!-- Simulation: Multi-platform Ticker -->
            <div class="p-3 rounded-xl bg-[#060709] border border-[rgba(255,255,255,0.06)] grid grid-cols-3 gap-2 text-center font-mono text-[11px]">
              <div class="p-2 rounded bg-zinc-900/60 space-y-0.5">
                <div class="text-[#8a8f98] text-[10px]">Amazon US</div>
                <div class="text-[#f7f8f8] font-bold">$189.99</div>
                <div class="text-emerald-400 text-[9px] flex items-center justify-center gap-0.5">
                  <TrendingUp class="w-2.5 h-2.5" /> BSR #142
                </div>
              </div>
              <div class="p-2 rounded bg-zinc-900/60 space-y-0.5 border border-[#7170ff]/25">
                <div class="text-[#8a8f98] text-[10px]">TikTok Shop</div>
                <div class="text-[#7170ff] font-bold">$159.00</div>
                <div class="text-[#7170ff] text-[9px] flex items-center justify-center gap-0.5">
                  <TrendingUp class="w-2.5 h-2.5" /> 流量 +340%
                </div>
              </div>
              <div class="p-2 rounded bg-zinc-900/60 space-y-0.5">
                <div class="text-[#8a8f98] text-[10px]">Temu Global</div>
                <div class="text-[#f7f8f8] font-bold">$139.50</div>
                <div class="text-rose-400 text-[9px] flex items-center justify-center gap-0.5">
                  <TrendingDown class="w-2.5 h-2.5" /> 杀价 -18%
                </div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="pt-3 border-t border-[rgba(255,255,255,0.06)] flex items-center justify-between text-xs font-mono">
            <span class="text-zinc-500 text-[11px]">按 [← / →] 切换 · 悬停暂停</span>
            <button @click="goToNext" class="text-[#7170ff] hover:text-[#828fff] flex items-center gap-1 font-medium transition-colors">
              <span>下一张能力</span>
              <ChevronRight class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <!-- Card 1: VLM Defect Forensics -->
        <div
          class="deck-card-item absolute inset-0 rounded-2xl bg-[#0d0e12]/95 border border-[rgba(255,255,255,0.14)] p-6 sm:p-7 flex flex-col justify-between overflow-hidden shadow-[0_25px_60px_rgba(0,0,0,0.8),inset_0_1px_0_rgba(255,255,255,0.15)] backdrop-blur-xl"
          style="will-change: transform, opacity;"
        >
          <div
            v-if="activeIndex === 1"
            ref="progressBarRef"
            class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-[#06b6d4] to-[#10b981] origin-left"
          />

          <div class="flex items-center justify-between pb-3 border-b border-[rgba(255,255,255,0.06)]">
            <div class="flex items-center gap-2.5">
              <div class="p-2 rounded-xl bg-[#06b6d4]/15 border border-[#06b6d4]/30 text-[#06b6d4]">
                <Sparkles class="w-4 h-4" />
              </div>
              <div>
                <span class="text-[10px] font-mono tracking-widest font-semibold block text-[#06b6d4] uppercase">
                  {{ features[1].tag }}
                </span>
                <h3 class="text-base font-semibold text-[#f7f8f8] tracking-tight">
                  {{ features[1].title }}
                </h3>
              </div>
            </div>
            <span class="text-[11px] font-mono px-2.5 py-1 rounded-full bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-zinc-300">
              {{ features[1].badge }}
            </span>
          </div>

          <div class="py-3 flex-1 flex flex-col justify-center space-y-3">
            <div class="space-y-1">
              <h4 class="text-xs sm:text-sm font-semibold text-zinc-200">
                {{ features[1].tagline }}
              </h4>
              <p class="text-xs text-[#8a8f98] leading-relaxed">
                {{ features[1].summary }}
              </p>
            </div>

            <!-- Simulation: VLM Scan Line -->
            <div class="relative rounded-xl overflow-hidden bg-[#050608] border border-[rgba(255,255,255,0.06)] p-3 flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="relative w-14 h-12 rounded-lg bg-zinc-900 overflow-hidden border border-rose-500/60 shrink-0 flex items-center justify-center">
                  <div class="absolute inset-0 bg-rose-500/15" />
                  <Scan class="w-6 h-6 text-rose-400 opacity-80" />
                </div>
                <div class="space-y-0.5">
                  <div class="text-xs font-mono text-rose-400 font-semibold">
                    3D 扶手升降卡扣应力剪切断裂
                  </div>
                  <div class="text-[11px] text-zinc-400 font-mono">
                    物理根因：倒角 R 角仅 0.4mm，侧向 35kg 载荷产生疲劳脆断
                  </div>
                </div>
              </div>
              <div class="text-right font-mono text-[10px] text-cyan-400 shrink-0 pl-2">
                Claude 3.5 VLM<br />置信度 98.2%
              </div>
            </div>
          </div>

          <div class="pt-3 border-t border-[rgba(255,255,255,0.06)] flex items-center justify-between text-xs font-mono">
            <span class="text-zinc-500 text-[11px]">按 [← / →] 切换 · 悬停暂停</span>
            <button @click="goToNext" class="text-[#06b6d4] hover:text-[#38bdf8] flex items-center gap-1 font-medium transition-colors">
              <span>下一张能力</span>
              <ChevronRight class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <!-- Card 2: Dual-Column Redesign -->
        <div
          class="deck-card-item absolute inset-0 rounded-2xl bg-[#0d0e12]/95 border border-[rgba(255,255,255,0.14)] p-6 sm:p-7 flex flex-col justify-between overflow-hidden shadow-[0_25px_60px_rgba(0,0,0,0.8),inset_0_1px_0_rgba(255,255,255,0.15)] backdrop-blur-xl"
          style="will-change: transform, opacity;"
        >
          <div
            v-if="activeIndex === 2"
            ref="progressBarRef"
            class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-[#10b981] to-[#f43f5e] origin-left"
          />

          <div class="flex items-center justify-between pb-3 border-b border-[rgba(255,255,255,0.06)]">
            <div class="flex items-center gap-2.5">
              <div class="p-2 rounded-xl bg-[#10b981]/15 border border-[#10b981]/30 text-[#10b981]">
                <Wrench class="w-4 h-4" />
              </div>
              <div>
                <span class="text-[10px] font-mono tracking-widest font-semibold block text-[#10b981] uppercase">
                  {{ features[2].tag }}
                </span>
                <h3 class="text-base font-semibold text-[#f7f8f8] tracking-tight">
                  {{ features[2].title }}
                </h3>
              </div>
            </div>
            <span class="text-[11px] font-mono px-2.5 py-1 rounded-full bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-zinc-300">
              {{ features[2].badge }}
            </span>
          </div>

          <div class="py-3 flex-1 flex flex-col justify-center space-y-3">
            <div class="space-y-1">
              <h4 class="text-xs sm:text-sm font-semibold text-zinc-200">
                {{ features[2].tagline }}
              </h4>
              <p class="text-xs text-[#8a8f98] leading-relaxed">
                {{ features[2].summary }}
              </p>
            </div>

            <!-- Simulation: Dual Column Blueprint -->
            <div class="grid grid-cols-2 gap-2.5 text-xs font-mono">
              <div class="p-2.5 rounded-xl bg-cyan-950/20 border border-cyan-800/40 space-y-1">
                <div class="text-cyan-400 font-bold text-[10px]">左栏 · 硬件本体工程</div>
                <div class="text-zinc-200 text-[11px] truncate">Zamak-3 压铸骨架 (±0.03mm)</div>
                <div class="text-[#8a8f98] text-[10px]">增额: +$1.45 | 工期: 14天</div>
              </div>
              <div class="p-2.5 rounded-xl bg-emerald-950/20 border border-emerald-800/40 space-y-1">
                <div class="text-emerald-400 font-bold text-[10px]">右栏 · 包装 Tier Down</div>
                <div class="text-zinc-200 text-[11px] truncate">外箱长边紧凑压降 6.5cm</div>
                <div class="text-emerald-400 text-[10px] font-bold">单件净省: $4.60 USD</div>
              </div>
            </div>
          </div>

          <div class="pt-3 border-t border-[rgba(255,255,255,0.06)] flex items-center justify-between text-xs font-mono">
            <span class="text-zinc-500 text-[11px]">按 [← / →] 切换 · 悬停暂停</span>
            <button @click="goToNext" class="text-[#10b981] hover:text-[#34d399] flex items-center gap-1 font-medium transition-colors">
              <span>下一张能力</span>
              <ChevronRight class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <!-- Card 3: Financial Veto -->
        <div
          class="deck-card-item absolute inset-0 rounded-2xl bg-[#0d0e12]/95 border border-[rgba(255,255,255,0.14)] p-6 sm:p-7 flex flex-col justify-between overflow-hidden shadow-[0_25px_60px_rgba(0,0,0,0.8),inset_0_1px_0_rgba(255,255,255,0.15)] backdrop-blur-xl"
          style="will-change: transform, opacity;"
        >
          <div
            v-if="activeIndex === 3"
            ref="progressBarRef"
            class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-[#f43f5e] to-[#7170ff] origin-left"
          />

          <div class="flex items-center justify-between pb-3 border-b border-[rgba(255,255,255,0.06)]">
            <div class="flex items-center gap-2.5">
              <div class="p-2 rounded-xl bg-[#f43f5e]/15 border border-[#f43f5e]/30 text-[#f43f5e]">
                <ShieldCheck class="w-4 h-4" />
              </div>
              <div>
                <span class="text-[10px] font-mono tracking-widest font-semibold block text-[#f43f5e] uppercase">
                  {{ features[3].tag }}
                </span>
                <h3 class="text-base font-semibold text-[#f7f8f8] tracking-tight">
                  {{ features[3].title }}
                </h3>
              </div>
            </div>
            <span class="text-[11px] font-mono px-2.5 py-1 rounded-full bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-zinc-300">
              {{ features[3].badge }}
            </span>
          </div>

          <div class="py-3 flex-1 flex flex-col justify-center space-y-3">
            <div class="space-y-1">
              <h4 class="text-xs sm:text-sm font-semibold text-zinc-200">
                {{ features[3].tagline }}
              </h4>
              <p class="text-xs text-[#8a8f98] leading-relaxed">
                {{ features[3].summary }}
              </p>
            </div>

            <!-- Simulation: Financial Decision Gate -->
            <div class="p-3 rounded-xl bg-emerald-950/20 border border-emerald-800/40 flex items-center justify-between font-mono text-xs">
              <div class="space-y-0.5">
                <div class="text-emerald-400 font-bold flex items-center gap-1.5">
                  <CheckCircle2 class="w-4 h-4" />
                  <span>DECISION: APPROVED (准予开模)</span>
                </div>
                <div class="text-zinc-400 text-[10px]">
                  测算回本: 3.8 个月 &lt; 6.0 个月阈值 | 年降本 $46,000
                </div>
              </div>
              <div class="text-right text-[10px] text-zinc-500">
                毛利安全垫 32.4%
              </div>
            </div>
          </div>

          <div class="pt-3 border-t border-[rgba(255,255,255,0.06)] flex items-center justify-between text-xs font-mono">
            <span class="text-zinc-500 text-[11px]">按 [← / →] 切换 · 悬停暂停</span>
            <button @click="goToNext" class="text-[#f43f5e] hover:text-[#fb7185] flex items-center gap-1 font-medium transition-colors">
              <span>下一张能力</span>
              <ChevronRight class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      <!-- Cinematic Stepper Controls with Dynamic Fill Indicator -->
      <div class="cinematic-controls flex items-center justify-center gap-3 mt-7 w-full max-w-xl">
        <button
          @click="goToPrev"
          class="p-2 rounded-full ln-btn text-[#8a8f98] hover:text-[#f7f8f8]"
          title="上一张 (←)"
        >
          <ChevronLeft class="w-4 h-4" />
        </button>

        <button
          @click="toggleAutoPlay"
          class="p-2 rounded-full ln-btn text-[#8a8f98] hover:text-[#f7f8f8]"
          :title="isAutoPlaying ? '暂停轮播' : '恢复轮播'"
        >
          <Pause v-if="isAutoPlaying" class="w-4 h-4 text-[#7170ff]" />
          <Play v-else class="w-4 h-4" />
        </button>

        <!-- 4 Step Interactive Pills -->
        <div class="flex items-center gap-1.5 bg-[rgba(255,255,255,0.03)] p-1 rounded-xl border border-[rgba(255,255,255,0.06)] flex-1 justify-between">
          <button
            v-for="(f, i) in features"
            :key="f.id"
            @click="goToIndex(i)"
            :class="[
              'flex-1 py-1.5 px-2 rounded-lg text-[11px] font-mono transition-all text-center truncate',
              activeIndex === i
                ? 'bg-[rgba(255,255,255,0.1)] text-[#f7f8f8] font-semibold shadow-sm'
                : 'text-[#8a8f98] hover:text-zinc-300'
            ]"
          >
            0{{ i + 1 }} {{ f.title.slice(0, 4) }}
          </button>
        </div>

        <button
          @click="goToNext"
          class="p-2 rounded-full ln-btn text-[#8a8f98] hover:text-[#f7f8f8]"
          title="下一张 (→)"
        >
          <ChevronRight class="w-4 h-4" />
        </button>
      </div>
    </main>

    <!-- Bottom Footer Bar -->
    <footer class="relative z-20 max-w-6xl mx-auto w-full px-6 py-4 border-t border-[rgba(255,255,255,0.05)] flex flex-col sm:flex-row items-center justify-between gap-3 text-xs font-mono text-[#5e626e]">
      <div>
        <span>工贸一体出海 · 产业带白牌制造 · 品牌型跨境卖家专属</span>
      </div>

      <div class="flex items-center gap-4">
        <button
          @click="emit('enter')"
          class="text-xs font-mono text-zinc-300 hover:text-white flex items-center gap-1.5 transition-colors group"
        >
          <span>进入 InsightX 工业级大盘工作区</span>
          <ArrowRight class="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
        </button>
      </div>
    </footer>
  </div>
</template>
