<script setup lang="ts">
import gsap from 'gsap';
import {
  ArrowRight,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Layers,
  LogIn,
  Scan,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Wrench,
} from 'lucide-vue-next';
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import productLogo from '../assets/Product_logo.webp';

const emit = defineEmits<{
  (e: 'enter'): void;
  (e: 'openAuth'): void;
}>();

const activeIndex = ref(0);
const heroCard = ref<HTMLElement | null>(null);

const features = [
  {
    id: 0,
    tag: 'PILLAR 01 · SPATIO-TEMPORAL INGESTION',
    icon: Layers,
    title: '跨平台全景时序穿透',
    tagline: 'Amazon · TikTok Shop · Temu 同品类动态对齐',
    summary: '消除跨境卖家在多款独立软件之间拼凑 Excel 的痛苦。打通三大出海平台同款 SKU，分钟级监控价格异动、排名跳变与流量套利空间。',
    accentColor: '#7170ff',
    badge: '3,840+ 样本分钟级对齐',
  },
  {
    id: 1,
    tag: 'PILLAR 02 · MULTIMODAL VLM FORENSICS',
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

let mainTl: gsap.core.Timeline | null = null;

// Deal active card directly toward the viewer's face with dramatic 3D velocity
const dealCardToFace = (_fromIndex: number, toIndex: number, direction: 'next' | 'prev') => {
  const card = heroCard.value;
  if (!card) return;

  // Outgoing animation: active card flips violently up and past the user's camera
  const flyTl = gsap.timeline();

  flyTl.to(card, {
    duration: 0.22,
    ease: 'power3.in',
    z: 320,
    y: direction === 'next' ? -120 : 120,
    rotationX: direction === 'next' ? -18 : 18,
    scale: 1.15,
    opacity: 0,
    onComplete: () => {
      activeIndex.value = toIndex;

      // Incoming animation: new card slams forward from deep space right into viewer's face
      gsap.fromTo(
        card,
        {
          z: -420,
          y: direction === 'next' ? 90 : -90,
          rotationX: direction === 'next' ? 14 : -14,
          scale: 0.82,
          opacity: 0,
        },
        {
          duration: 0.55,
          ease: 'back.out(1.4)',
          z: 0,
          y: 0,
          rotationX: 0,
          scale: 1,
          opacity: 1,
          clearProps: 'transform',
        }
      );
    },
  });
};

const goTo = (index: number) => {
  if (index === activeIndex.value) return;
  const dir = index > activeIndex.value ? 'next' : 'prev';
  dealCardToFace(activeIndex.value, index, dir);
};

const handleNext = () => {
  const nextIdx = (activeIndex.value + 1) % features.length;
  dealCardToFace(activeIndex.value, nextIdx, 'next');
};

const handlePrev = () => {
  const prevIdx = (activeIndex.value - 1 + features.length) % features.length;
  dealCardToFace(activeIndex.value, prevIdx, 'prev');
};

// Subtle 3D mouse parallax tilt
const handleMouseMove = (e: MouseEvent) => {
  if (!heroCard.value) return;
  const rect = heroCard.value.getBoundingClientRect();
  const centerX = rect.left + rect.width / 2;
  const centerY = rect.top + rect.height / 2;
  const mouseX = e.clientX - centerX;
  const mouseY = e.clientY - centerY;

  const tiltX = (mouseY / (rect.height / 2)) * -6;
  const tiltY = (mouseX / (rect.width / 2)) * 6;

  gsap.to(heroCard.value, {
    duration: 0.35,
    ease: 'power1.out',
    rotationX: tiltX,
    rotationY: tiltY,
    transformPerspective: 1200,
  });
};

const handleMouseLeave = () => {
  if (!heroCard.value) return;
  gsap.to(heroCard.value, {
    duration: 0.6,
    ease: 'power2.out',
    rotationX: 0,
    rotationY: 0,
  });
};

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
    handleNext();
  } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
    handlePrev();
  } else if (e.key === 'Enter') {
    emit('enter');
  }
};

onMounted(async () => {
  window.addEventListener('keydown', handleKeydown);
  await nextTick();

  mainTl = gsap.timeline();

  // 1. Scene entrance
  mainTl.from('.cinematic-brand', {
    y: -20,
    opacity: 0,
    duration: 0.6,
    ease: 'power2.out',
  });

  mainTl.from(
    '.cinematic-hero-text',
    {
      y: 35,
      opacity: 0,
      duration: 0.75,
      stagger: 0.12,
      ease: 'power3.out',
    },
    '-=0.3'
  );

  // 2. The Hero Card explodes forward into face
  mainTl.from(
    heroCard.value,
    {
      z: -600,
      scale: 0.65,
      rotationX: 25,
      opacity: 0,
      duration: 0.9,
      ease: 'expo.out',
    },
    '-=0.4'
  );

  mainTl.from(
    '.deck-controls',
    {
      y: 20,
      opacity: 0,
      duration: 0.5,
      ease: 'power2.out',
    },
    '-=0.3'
  );
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown);
  if (mainTl) mainTl.kill();
});
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex flex-col justify-between bg-[#060709] text-[#f7f8f8] overflow-hidden select-none"
    @mousemove="handleMouseMove"
    @mouseleave="handleMouseLeave"
  >
    <!-- Cinematic Atmosphere: Anamorphic Horizontal Laser Flare + Spatial Grid -->
    <div class="absolute inset-0 pointer-events-none">
      <!-- Deep space grid -->
      <div class="absolute inset-0 opacity-[0.14] bg-[radial-gradient(#393e4f_1px,transparent_1px)] [background-size:28px_28px]" />

      <!-- High-tech laser streak across top -->
      <div class="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[#7170ff]/60 to-transparent" />
      <div class="absolute -top-32 left-1/2 -translate-x-1/2 w-[800px] h-[350px] bg-gradient-to-b from-[#7170ff]/15 via-[#06b6d4]/8 to-transparent blur-[120px]" />
    </div>

    <!-- Top Minimalist Bar -->
    <header class="cinematic-brand relative z-20 max-w-6xl mx-auto w-full px-6 py-5 flex items-center justify-between border-b border-[rgba(255,255,255,0.05)]">
      <div class="flex items-center gap-3">
        <img :src="productLogo" alt="InsightX" class="h-8 w-auto object-contain drop-shadow-[0_0_12px_rgba(113,112,255,0.3)]" />
        <span class="text-zinc-600 font-mono">/</span>
        <span class="text-xs font-mono tracking-widest text-[#8a8f98] uppercase">
          AI Industrial Decision System
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
          class="ln-btn-primary px-3.5 py-1.5 flex items-center gap-1.5 text-xs font-medium shadow-[0_0_20px_rgba(113,112,255,0.25)]"
        >
          <span>直接进入大盘</span>
          <ArrowRight class="w-3.5 h-3.5" />
        </button>
      </div>
    </header>

    <!-- Center Stage: The Hero Card Dealt Directly Into Your Face -->
    <main class="relative z-20 max-w-5xl mx-auto w-full px-6 flex flex-col items-center justify-center flex-1 py-3">
      <!-- Impact Headlines -->
      <div class="text-center space-y-2 mb-6 max-w-3xl">
        <div class="cinematic-hero-text inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] text-[11px] font-mono text-[#8a8f98]">
          <span class="w-2 h-2 rounded-full bg-[#7170ff] animate-ping" />
          <span>破除“只荐爆款不控风险”死结 · 工贸一体专属工业级闭环</span>
        </div>

        <h1 class="cinematic-hero-text text-2xl sm:text-4xl md:text-5xl font-bold tracking-tight text-[#f7f8f8] leading-tight">
          从海量差评取证，到工厂工程图纸
        </h1>

        <p class="cinematic-hero-text text-xs sm:text-sm text-[#8a8f98] max-w-xl mx-auto leading-relaxed">
          打通多源时序感知、多模态视觉定损、双栏改款决策与逆向财务熔断。
        </p>
      </div>

      <!-- 3D Card Stage with High Perspective Depth -->
      <div
        ref="cardStage"
        class="relative w-full max-w-2xl h-[380px] sm:h-[400px] flex items-center justify-center [perspective:1400px] [transform-style:preserve-3d]"
      >
        <!-- Background Shadow Deck (Giving physical multi-card depth behind active card) -->
        <div class="absolute w-[92%] sm:w-[96%] h-full rounded-2xl bg-[#090a0e]/60 border border-[rgba(255,255,255,0.04)] [transform:translateZ(-140px)_translateY(16px)_scale(0.92)] pointer-events-none opacity-60" />
        <div class="absolute w-[86%] sm:w-[90%] h-full rounded-2xl bg-[#07080b]/50 border border-[rgba(255,255,255,0.02)] [transform:translateZ(-260px)_translateY(28px)_scale(0.85)] pointer-events-none opacity-30" />

        <!-- THE HERO ACTIVE CARD (Snaps directly in front of the viewer) -->
        <div
          ref="heroCard"
          class="relative w-full h-full rounded-2xl bg-[#0e0f13]/95 border border-[rgba(255,255,255,0.16)] shadow-[0_25px_70px_rgba(0,0,0,0.9),inset_0_1px_0_rgba(255,255,255,0.2)] p-6 sm:p-7 flex flex-col justify-between overflow-hidden backdrop-blur-2xl transition-shadow group cursor-grab active:cursor-grabbing"
        >
          <!-- Specular corner highlight -->
          <div class="absolute top-0 right-0 w-48 h-48 bg-gradient-to-bl from-white/5 via-transparent to-transparent pointer-events-none" />

          <!-- Card Header Row -->
          <div class="flex items-center justify-between pb-3 border-b border-[rgba(255,255,255,0.07)]">
            <div class="flex items-center gap-2.5">
              <div
                class="p-2 rounded-xl border"
                :style="{
                  backgroundColor: `${features[activeIndex].accentColor}18`,
                  borderColor: `${features[activeIndex].accentColor}40`,
                  color: features[activeIndex].accentColor,
                }"
              >
                <component :is="features[activeIndex].icon" class="w-4 h-4" />
              </div>

              <div>
                <span
                  class="text-[10px] font-mono tracking-widest font-semibold block uppercase"
                  :style="{ color: features[activeIndex].accentColor }"
                >
                  {{ features[activeIndex].tag }}
                </span>
                <h3 class="text-base sm:text-lg font-bold text-[#f7f8f8] tracking-tight">
                  {{ features[activeIndex].title }}
                </h3>
              </div>
            </div>

            <!-- Card Badge -->
            <div class="text-[11px] font-mono px-2.5 py-1 rounded-full bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.08)] text-zinc-300">
              {{ features[activeIndex].badge }}
            </div>
          </div>

          <!-- Card Live Interactive Feature Simulation Showcase -->
          <div class="py-3 flex-1 flex flex-col justify-center space-y-3">
            <div class="space-y-1">
              <h4 class="text-xs sm:text-sm font-semibold text-zinc-200">
                {{ features[activeIndex].tagline }}
              </h4>
              <p class="text-xs text-[#8a8f98] leading-relaxed">
                {{ features[activeIndex].summary }}
              </p>
            </div>

            <!-- DYNAMIC INTERACTIVE COMPONENT PREVIEW FOR EACH PILLAR -->
            <!-- 1. Spatio-Temporal Ingestion Live Ticker -->
            <div
              v-if="activeIndex === 0"
              class="p-3 rounded-xl bg-[#06070a] border border-[rgba(255,255,255,0.06)] grid grid-cols-3 gap-2 text-center font-mono text-[11px]"
            >
              <div class="p-2 rounded bg-zinc-900/50 space-y-0.5">
                <div class="text-[#8a8f98] text-[10px]">Amazon (US)</div>
                <div class="text-[#f7f8f8] font-bold">$189.99</div>
                <div class="text-emerald-400 text-[9px] flex items-center justify-center gap-0.5">
                  <TrendingUp class="w-2.5 h-2.5" /> BSR #142
                </div>
              </div>

              <div class="p-2 rounded bg-zinc-900/50 space-y-0.5 border border-cyan-500/20">
                <div class="text-[#8a8f98] text-[10px]">TikTok Shop</div>
                <div class="text-cyan-400 font-bold">$159.00</div>
                <div class="text-cyan-300 text-[9px] flex items-center justify-center gap-0.5">
                  <TrendingUp class="w-2.5 h-2.5" /> 流量 +340%
                </div>
              </div>

              <div class="p-2 rounded bg-zinc-900/50 space-y-0.5">
                <div class="text-[#8a8f98] text-[10px]">Temu Global</div>
                <div class="text-[#f7f8f8] font-bold">$139.50</div>
                <div class="text-rose-400 text-[9px] flex items-center justify-center gap-0.5">
                  <TrendingDown class="w-2.5 h-2.5" /> 杀价 -18%
                </div>
              </div>
            </div>

            <!-- 2. Claude Vision Forensics Bounding Box Simulation -->
            <div
              v-else-if="activeIndex === 1"
              class="relative rounded-xl overflow-hidden bg-[#050608] border border-[rgba(255,255,255,0.06)] p-2.5 flex items-center justify-between"
            >
              <div class="flex items-center gap-3">
                <div class="relative w-14 h-12 rounded-lg bg-zinc-900 overflow-hidden border border-rose-500/60 shrink-0">
                  <div class="absolute inset-0 bg-rose-500/20" />
                  <div class="absolute top-1 left-1 text-[8px] font-mono text-rose-300 bg-rose-950 px-1 rounded">
                    CRACK
                  </div>
                  <Scan class="w-6 h-6 text-rose-400 absolute bottom-1 right-1 opacity-70" />
                </div>
                <div class="space-y-0.5">
                  <div class="text-xs font-mono text-rose-400 font-semibold">
                    3D 扶手升降支架齿条应力撕裂
                  </div>
                  <div class="text-[11px] text-zinc-400 font-mono">
                    成因：倒角 R 角仅 0.4mm，侧向 35kg 载荷产生剪切脆断
                  </div>
                </div>
              </div>
              <div class="text-right font-mono text-[10px] text-cyan-400 shrink-0 pl-2">
                Claude 3.5 VLM<br />置信度 98.2%
              </div>
            </div>

            <!-- 3. Dual-Column Blueprint Comparison -->
            <div
              v-else-if="activeIndex === 2"
              class="grid grid-cols-2 gap-2 text-xs font-mono"
            >
              <div class="p-2.5 rounded-xl bg-cyan-950/20 border border-cyan-800/40 space-y-1">
                <div class="text-cyan-400 font-bold text-[10px]">左栏 · 硬件本体工程</div>
                <div class="text-zinc-200 text-[11px] truncate">Zamak-3 锌合金压铸骨架</div>
                <div class="text-[#8a8f98] text-[10px]">增额: +$1.45 | 工期: 14天</div>
              </div>

              <div class="p-2.5 rounded-xl bg-emerald-950/20 border border-emerald-800/40 space-y-1">
                <div class="text-emerald-400 font-bold text-[10px]">右栏 · 包装 Tier Down</div>
                <div class="text-zinc-200 text-[11px] truncate">外箱长边紧凑压降 6.5cm</div>
                <div class="text-emerald-400 text-[10px] font-bold">单件净省: $4.60 USD</div>
              </div>
            </div>

            <!-- 4. Reverse Financial Veto Gate -->
            <div
              v-else
              class="p-2.5 rounded-xl bg-emerald-950/20 border border-emerald-800/40 flex items-center justify-between font-mono text-xs"
            >
              <div class="space-y-0.5">
                <div class="text-emerald-400 font-bold flex items-center gap-1">
                  <CheckCircle2 class="w-3.5 h-3.5" />
                  <span>DECISION: APPROVED (准予开模)</span>
                </div>
                <div class="text-zinc-400 text-[10px]">
                  测算回本: 3.8 个月 &lt; 6.0 个月生命周期 | 年化降本 $46,000
                </div>
              </div>
              <div class="text-right text-[10px] text-zinc-500">
                毛利安全垫 32.4%
              </div>
            </div>
          </div>

          <!-- Card Footer Action Row -->
          <div class="pt-3 border-t border-[rgba(255,255,255,0.06)] flex items-center justify-between text-xs font-mono">
            <span class="text-zinc-500 text-[11px]">
              按键盘 [← / →] 翻牌，按 [Enter] 进入
            </span>

            <button
              @click="handleNext"
              class="text-[#7170ff] hover:text-[#828fff] flex items-center gap-1 font-medium transition-colors"
            >
              <span>下一张核心能力</span>
              <ChevronRight class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      <!-- Deck Progress Scrubber -->
      <div class="deck-controls flex items-center justify-center gap-4 mt-6 w-full max-w-xl">
        <button
          @click="handlePrev"
          class="p-2 rounded-full ln-btn text-[#8a8f98] hover:text-[#f7f8f8]"
          title="上一张 (←)"
        >
          <ChevronLeft class="w-4 h-4" />
        </button>

        <!-- 4 Steps Interactive Tabs -->
        <div class="flex items-center gap-1.5 bg-[rgba(255,255,255,0.03)] p-1 rounded-xl border border-[rgba(255,255,255,0.06)] flex-1 justify-between">
          <button
            v-for="(f, i) in features"
            :key="f.id"
            @click="goTo(i)"
            :class="[
              'flex-1 py-1 px-2 rounded-lg text-[11px] font-mono transition-all text-center truncate',
              activeIndex === i
                ? 'bg-[rgba(255,255,255,0.1)] text-[#f7f8f8] font-semibold shadow-sm'
                : 'text-[#8a8f98] hover:text-zinc-300'
            ]"
          >
            0{{ i + 1 }} {{ f.title.slice(0, 4) }}
          </button>
        </div>

        <button
          @click="handleNext"
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
        <span>出海工贸一体企业 · 产业带白牌制造 · 品牌型跨境卖家专属</span>
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
