<script setup lang="ts">
import gsap from 'gsap';
import {
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Cpu,
  Layers,
  LogIn,
  ShieldCheck,
  Sparkles,
  Wrench,
} from 'lucide-vue-next';
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import productLogo from '../assets/Product_logo.webp';

const emit = defineEmits<{
  (e: 'enter'): void;
  (e: 'openAuth'): void;
}>();

const cardsContainer = ref<HTMLElement | null>(null);
const activeIndex = ref(0);

const features = [
  {
    id: 1,
    tag: '01 · SPATIO-TEMPORAL',
    icon: Layers,
    title: '跨平台时序数据采集与语义对齐',
    headline: '打破 Amazon、TikTok Shop、Temu 平台数据孤岛',
    desc: '分钟级全景穿透监控竞品价格变动、BSR 排名波动与流量异动。通过 bge-m3 1024 维密集语义向量，将多语言俚语差评归一化至同一工业质量本体。',
    stat: '3,840+ 样本分钟级对齐',
    highlight: '消灭盲目选品的信息黑洞',
    color: '#7170ff',
  },
  {
    id: 2,
    tag: '02 · VISION FORENSICS',
    icon: Sparkles,
    title: '多模态视觉差评取证与缺陷诊断',
    headline: '跳出文本浅层分词，直接定位买家实拍破损',
    desc: '集成 Claude Vision 视觉大模型，自动过滤包装袋与无关背景，精准提取零件剪切脆断、高温形变、模具缩水与瓦楞纸箱跌落穿透的物理级证据链。',
    stat: '98.2% 物理缺陷定位置信度',
    highlight: '从买家实拍直通工厂工程图纸',
    color: '#06b6d4',
  },
  {
    id: 3,
    tag: '03 · DUAL-COLUMN ENGINE',
    icon: Wrench,
    title: '工厂级“双栏改款”工程决策引擎',
    headline: '告别空洞建议：左栏改本体，右栏降包装',
    desc: '出海工贸一体专属利器。左栏输出合金替代、公差修正与结构防呆等模具需求；右栏输出包装尺寸降阶 (Tier Down) 与抗摔缓冲，规避超规高额 FBA 配送费。',
    stat: '单件物流净省 $4.60 (年省 $4.6万)',
    highlight: '结构化可落地的模具与包材清单',
    color: '#10b981',
  },
  {
    id: 4,
    tag: '04 · FINANCIAL VETO',
    icon: ShieldCheck,
    title: '逆向财务约束与现金流否决熔断',
    headline: '不仅推荐改款，更在红海内卷前主动叫停',
    desc: '内嵌模具费、起订量 (MOQ)、物流抛重比与资金回流约束。当投资回报周期超出类目生命周期或毛利侵蚀严重时，直接触发强制熔断，守护企业利润底线。',
    stat: '动态回测吻合度 93.6%',
    highlight: '理性否决高危项目，提供免开模替代路线',
    color: '#f43f5e',
  },
];

let tl: gsap.core.Timeline | null = null;

const animateCards = () => {
  if (!cardsContainer.value) return;
  const cards = cardsContainer.value.querySelectorAll('.deal-card');

  cards.forEach((card, index) => {
    const offset = index - activeIndex.value;
    const isCenter = offset === 0;

    gsap.to(card, {
      duration: 0.65,
      ease: 'power3.out',
      x: offset * 90,
      y: isCenter ? -10 : Math.abs(offset) * 16,
      z: isCenter ? 120 : -Math.abs(offset) * 140,
      rotationY: offset * -12,
      rotationZ: offset * 2.5,
      scale: isCenter ? 1.04 : Math.max(0.78, 1 - Math.abs(offset) * 0.12),
      opacity: Math.abs(offset) > 2 ? 0 : 1 - Math.abs(offset) * 0.28,
      zIndex: 20 - Math.abs(offset),
      overwrite: 'auto',
    });
  });
};

const nextCard = () => {
  if (activeIndex.value < features.length - 1) {
    activeIndex.value++;
    animateCards();
  } else {
    activeIndex.value = 0;
    animateCards();
  }
};

const prevCard = () => {
  if (activeIndex.value > 0) {
    activeIndex.value--;
    animateCards();
  } else {
    activeIndex.value = features.length - 1;
    animateCards();
  }
};

onMounted(async () => {
  await nextTick();
  if (!cardsContainer.value) return;

  // Intro Entrance Animation Timeline
  tl = gsap.timeline();

  tl.from('.intro-hero-text', {
    y: 24,
    opacity: 0,
    duration: 0.7,
    ease: 'power3.out',
    stagger: 0.1,
  });

  tl.from(
    '.deal-card',
    {
      y: 180,
      z: -400,
      scale: 0.6,
      rotationX: 25,
      opacity: 0,
      duration: 0.85,
      stagger: 0.12,
      ease: 'back.out(1.2)',
      onComplete: () => {
        animateCards();
      },
    },
    '-=0.4'
  );

  tl.from(
    '.intro-footer-actions',
    {
      y: 16,
      opacity: 0,
      duration: 0.5,
      ease: 'power2.out',
    },
    '-=0.3'
  );
});

onBeforeUnmount(() => {
  if (tl) tl.kill();
});
</script>

<template>
  <div class="fixed inset-0 z-50 flex flex-col justify-between bg-[#08090a] text-[#f7f8f8] overflow-hidden select-none">
    <!-- Subtle Background Ambient Grid & Radial Lighting -->
    <div class="absolute inset-0 pointer-events-none opacity-20 bg-[radial-gradient(#262933_1px,transparent_1px)] [background-size:24px_24px]" />
    <div class="absolute top-1/4 left-1/2 -translate-x-1/2 w-[700px] h-[500px] bg-[#5e6ad2]/10 rounded-full blur-[140px] pointer-events-none" />

    <!-- Top Minimal Navbar -->
    <header class="relative z-10 max-w-6xl mx-auto w-full px-6 py-6 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <img :src="productLogo" alt="InsightX" class="h-8 w-auto object-contain" />
        <span class="text-xs font-mono text-zinc-500 hidden sm:inline">/ Industrial AI Decision System</span>
      </div>

      <div class="flex items-center gap-3">
        <button
          @click="emit('openAuth')"
          class="ln-btn px-3.5 py-1.5 flex items-center gap-1.5 text-xs text-[#d0d6e0] hover:text-white"
        >
          <LogIn class="w-3.5 h-3.5" />
          <span>登录 / 注册</span>
        </button>

        <button
          @click="emit('enter')"
          class="ln-btn-primary px-3.5 py-1.5 flex items-center gap-1.5 text-xs"
        >
          <span>进入系统</span>
          <ArrowRight class="w-3.5 h-3.5" />
        </button>
      </div>
    </header>

    <!-- Center Stage: Hero & 3D Interactive Card Dealing Stage -->
    <main class="relative z-10 max-w-5xl mx-auto w-full px-6 flex flex-col items-center justify-center flex-1 py-4">
      <!-- Title Block -->
      <div class="text-center space-y-2 mb-8 max-w-2xl">
        <div class="intro-hero-text inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-[11px] font-mono text-[#8a8f98]">
          <Cpu class="w-3 h-3 text-[#7170ff]" />
          <span>全球跨境电商 AI 市场洞察与动态决策系统</span>
        </div>

        <h1 class="intro-hero-text text-2xl sm:text-4xl font-semibold tracking-tight text-[#f7f8f8] leading-tight">
          拒绝盲目推爆款 · 守住出海利润底线
        </h1>

        <p class="intro-hero-text text-xs sm:text-sm text-[#8a8f98] max-w-lg mx-auto leading-relaxed">
          依托多源时序数据、多语言向量对齐与 Claude Vision 实拍缺陷取证，交付工厂级工程改款与逆向财务熔断。
        </p>
      </div>

      <!-- 3D Card Deck Container -->
      <div
        ref="cardsContainer"
        class="relative w-full max-w-xl h-80 flex items-center justify-center [perspective:1200px] [transform-style:preserve-3d]"
      >
        <div
          v-for="(feat, idx) in features"
          :key="feat.id"
          @click="activeIndex = idx; animateCards()"
          :class="[
            'deal-card absolute w-[360px] sm:w-[440px] p-6 rounded-2xl border cursor-pointer select-none transition-shadow',
            activeIndex === idx
              ? 'bg-[#121316]/95 border-[rgba(255,255,255,0.18)] shadow-[0_20px_50px_rgba(0,0,0,0.8)]'
              : 'bg-[#0f1011]/90 border-[rgba(255,255,255,0.06)] shadow-lg'
          ]"
        >
          <!-- Card Header -->
          <div class="flex items-center justify-between text-xs pb-3 border-b border-[rgba(255,255,255,0.06)] mb-4">
            <span class="font-mono font-medium text-[11px] tracking-wider" :style="{ color: feat.color }">
              {{ feat.tag }}
            </span>
            <div class="p-1.5 rounded-lg bg-[rgba(255,255,255,0.04)] text-zinc-300">
              <component :is="feat.icon" class="w-4 h-4" />
            </div>
          </div>

          <!-- Card Core Content -->
          <div class="space-y-2">
            <h3 class="text-base font-semibold text-[#f7f8f8] tracking-tight">
              {{ feat.title }}
            </h3>
            <p class="text-xs font-medium text-zinc-300 leading-snug">
              {{ feat.headline }}
            </p>
            <p class="text-xs text-[#8a8f98] leading-relaxed line-clamp-3">
              {{ feat.desc }}
            </p>
          </div>

          <!-- Card Highlight Stat Footer -->
          <div class="mt-5 pt-3 border-t border-[rgba(255,255,255,0.06)] flex items-center justify-between text-xs font-mono">
            <span class="text-emerald-400 font-medium">✓ {{ feat.stat }}</span>
            <span class="text-zinc-500 text-[11px]">{{ idx + 1 }} / 4</span>
          </div>
        </div>
      </div>

      <!-- Navigation Deck Dots & Controls -->
      <div class="intro-footer-actions flex items-center gap-6 mt-6">
        <button
          @click="prevCard"
          class="p-2 rounded-full ln-btn text-[#8a8f98] hover:text-[#f7f8f8]"
          title="上一张"
        >
          <ChevronLeft class="w-4 h-4" />
        </button>

        <div class="flex items-center gap-2">
          <button
            v-for="(_, i) in features"
            :key="i"
            @click="activeIndex = i; animateCards()"
            :class="[
              'h-1.5 rounded-full transition-all duration-300',
              activeIndex === i ? 'w-6 bg-[#7170ff]' : 'w-1.5 bg-[rgba(255,255,255,0.15)] hover:bg-[rgba(255,255,255,0.3)]'
            ]"
          />
        </div>

        <button
          @click="nextCard"
          class="p-2 rounded-full ln-btn text-[#8a8f98] hover:text-[#f7f8f8]"
          title="下一张"
        >
          <ChevronRight class="w-4 h-4" />
        </button>
      </div>
    </main>

    <!-- Bottom Footer Bar with Quick Direct Entry -->
    <footer class="relative z-10 max-w-6xl mx-auto w-full px-6 py-6 border-t border-[rgba(255,255,255,0.06)] flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-[#5e626e]">
      <div>
        <span>工贸一体出海 · 产业带白牌制造 · 品牌型跨境卖家专属</span>
      </div>

      <div class="flex items-center gap-4">
        <button
          @click="emit('enter')"
          class="text-xs font-mono text-[#8a8f98] hover:text-[#f7f8f8] flex items-center gap-1 transition-colors"
        >
          <span>免登录直接探索大盘工作区</span>
          <ArrowRight class="w-3 h-3" />
        </button>
      </div>
    </footer>
  </div>
</template>
