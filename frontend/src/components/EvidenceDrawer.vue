<script setup lang="ts">
import {
  Calendar,
  ExternalLink,
  Filter,
  Image as ImageIcon,
  Star,
  X,
} from 'lucide-vue-next';
import { computed, ref } from 'vue';

const props = defineProps<{
  isOpen: boolean;
  targetTitle: string;
  evidenceCount: number;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const ratingFilter = ref<number | null>(null);

interface MockReview {
  id: string;
  rating: number;
  date: string;
  title: string;
  content: string;
  translated: string;
  author: string;
  country: string;
  hasPhoto: boolean;
  photoUrl?: string;
  defectTag: string;
}

const mockReviews: MockReview[] = [
  {
    id: 'R1-AMZ-8821',
    rating: 1,
    date: '2026-08-14',
    author: 'Michael B.',
    country: 'United States',
    title: 'Snapped clean off on the 18th day',
    content: 'I was simply adjusting the armrest height while sitting down, and heard a loud plastic cracking sound. The inner gear teeth sheared completely off. Now the right arm is permanently stuck at the bottom position.',
    translated: '我只是坐着调节扶手高度，就听到很大的塑料断裂声。内部的齿轮咬合齿完全被剪切断了。现在右扶手卡死在最低位置，无法抬起。',
    hasPhoto: true,
    photoUrl: 'https://images.unsplash.com/photo-1580481077197-91f89345cbb6?auto=format&fit=crop&w=400&q=80',
    defectTag: 'PA6-GF 齿条应力撕裂',
  },
  {
    id: 'R1-AMZ-9932',
    rating: 1,
    date: '2026-08-20',
    author: 'Sarah Jenkins',
    country: 'United States',
    title: 'Box arrived in shredded state & parts scratched',
    content: 'FedEx delivery guy dropped the box and the corner split wide open. The heavy metal mechanism crushed through the cardboard and scratched the armrest. Package padding is nowhere near adequate for a 45 lb chair.',
    translated: 'FedEx 快递员把箱子放下时边角直接爆裂了。重型金属底盘刺穿了瓦楞纸板，把扶手刮花了。对于一张 45 磅重的椅子来说，这个包装缓冲垫厚度严重不足。',
    hasPhoto: true,
    photoUrl: 'https://images.unsplash.com/photo-1607344645866-009c320c5ab8?auto=format&fit=crop&w=400&q=80',
    defectTag: '单坑纸箱角部跌落击穿',
  },
  {
    id: 'R2-AMZ-6611',
    rating: 2,
    date: '2026-08-25',
    author: 'David Schmidt',
    country: 'Germany',
    title: 'Lumbar support has zero locking friction',
    content: 'Die Lordosenstütze rutscht ständig nach unten. Jedes Mal wenn man sich anlehnt, verliert die Rastung den Halt. Sehr frustrierend bei diesem Preis.',
    translated: '腰靠不断自发下滑。每次靠上去，卡位阻尼就会完全失效。在这个价位上体验极其令人沮丧。',
    hasPhoto: false,
    defectTag: '滑槽阻尼公差偏大',
  },
  {
    id: 'R3-AMZ-3320',
    rating: 1,
    date: '2026-09-01',
    author: 'Kenji T.',
    country: 'Japan',
    title: 'Ruined my wood flooring',
    content: 'フローリングに黒い擦り傷がたくさんつきました。キャスターの素材が硬すぎてゴムのカスが出ます。',
    translated: '木质地板上被蹭出了很多黑色划痕。脚轮的材质太硬，在地面摩擦会掉出黑色细屑。',
    hasPhoto: true,
    photoUrl: 'https://images.unsplash.com/photo-1505797149-43b0069ec26b?auto=format&fit=crop&w=400&q=80',
    defectTag: 'PU包胶轮碳黑析出',
  },
];

const filteredReviews = computed(() => {
  if (ratingFilter.value === null) return mockReviews;
  return mockReviews.filter(r => r.rating === ratingFilter.value);
});
</script>

<template>
  <!-- Background Backdrop -->
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 bg-zinc-950/70 backdrop-blur-sm transition-opacity duration-300"
    @click="emit('close')"
  />

  <!-- Slide-in Right Drawer -->
  <aside
    :class="[
      'fixed top-0 right-0 bottom-0 z-50 w-full max-w-xl bg-zinc-950/95 border-l border-zinc-800 p-6 shadow-2xl transition-transform duration-300 ease-out flex flex-col justify-between overflow-hidden',
      isOpen ? 'translate-x-0' : 'translate-x-full'
    ]"
  >
    <!-- Drawer Header -->
    <div class="space-y-3 pb-4 border-b border-zinc-800">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
            <ExternalLink class="w-4 h-4" />
          </span>
          <div>
            <h3 class="text-sm font-bold text-zinc-100">全链路证据端到端溯源</h3>
            <span class="text-[11px] font-mono text-zinc-400">100% 原始买家评级与真实实拍原声反查</span>
          </div>
        </div>

        <button
          @click="emit('close')"
          class="p-1.5 rounded-lg bg-zinc-900 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <div class="text-xs text-zinc-300 font-mono bg-zinc-900/80 p-2.5 rounded-lg border border-zinc-800">
        关联改款项: <span class="text-cyan-400 font-semibold">{{ targetTitle }}</span>
      </div>

      <!-- Filter Row -->
      <div class="flex items-center justify-between pt-1">
        <div class="flex items-center gap-1.5 text-xs">
          <Filter class="w-3.5 h-3.5 text-zinc-400" />
          <span class="text-zinc-400 text-[11px]">星级筛选:</span>
          <button
            @click="ratingFilter = null"
            :class="[
              'px-2 py-0.5 rounded text-[11px] font-mono transition-colors',
              ratingFilter === null ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-zinc-400 hover:text-zinc-200'
            ]"
          >
            全部 ({{ mockReviews.length }})
          </button>
          <button
            @click="ratingFilter = 1"
            :class="[
              'px-2 py-0.5 rounded text-[11px] font-mono transition-colors',
              ratingFilter === 1 ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' : 'text-zinc-400 hover:text-zinc-200'
            ]"
          >
            ★ 1星 (3)
          </button>
          <button
            @click="ratingFilter = 2"
            :class="[
              'px-2 py-0.5 rounded text-[11px] font-mono transition-colors',
              ratingFilter === 2 ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'text-zinc-400 hover:text-zinc-200'
            ]"
          >
            ★ 2星 (1)
          </button>
        </div>

        <span class="text-[11px] font-mono text-zinc-500">已对齐多语言翻译</span>
      </div>
    </div>

    <!-- Review Items Scroll List -->
    <div class="flex-1 overflow-y-auto py-4 space-y-4 pr-1 scrollbar-thin">
      <div
        v-for="rev in filteredReviews"
        :key="rev.id"
        class="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800/80 space-y-2.5 text-xs hover:border-zinc-700 transition-colors"
      >
        <!-- Review Meta Header -->
        <div class="flex items-center justify-between text-[11px] font-mono">
          <div class="flex items-center gap-1.5">
            <span class="text-amber-400 font-bold flex items-center gap-0.5">
              <Star class="w-3 h-3 fill-amber-400" />
              {{ rev.rating }}
            </span>
            <span class="text-zinc-400">· {{ rev.author }} ({{ rev.country }})</span>
          </div>

          <div class="flex items-center gap-1.5 text-zinc-500">
            <Calendar class="w-3 h-3" />
            <span>{{ rev.date }}</span>
          </div>
        </div>

        <!-- Defect Tag Pill -->
        <div>
          <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-rose-950/70 border border-rose-800 text-rose-300">
            {{ rev.defectTag }}
          </span>
        </div>

        <h4 class="font-bold text-zinc-100 text-xs">
          {{ rev.title }}
        </h4>

        <!-- Review Text in Original Language -->
        <p class="text-zinc-400 leading-relaxed italic">
          "{{ rev.content }}"
        </p>

        <!-- Chinese Alignment Translation -->
        <div class="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800/80 text-[11px] text-zinc-300 space-y-1">
          <span class="text-cyan-400 font-mono text-[10px] block font-semibold">↳ 中文语义对齐：</span>
          <p class="leading-relaxed">{{ rev.translated }}</p>
        </div>

        <!-- Photo preview if exists -->
        <div v-if="rev.hasPhoto && rev.photoUrl" class="flex items-center gap-2 pt-1">
          <div class="relative w-16 h-12 rounded-lg overflow-hidden border border-zinc-700">
            <img :src="rev.photoUrl" class="w-full h-full object-cover" />
            <span class="absolute bottom-0 right-0 bg-black/70 p-0.5 rounded text-[8px] text-white">
              <ImageIcon class="w-2.5 h-2.5" />
            </span>
          </div>
          <div class="text-[11px] text-zinc-400 font-mono">
            <span>买家上传实拍取证</span>
            <div class="text-emerald-400 text-[10px]">Claude Vision 已标注缺陷特征</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Drawer Footer -->
    <div class="pt-4 border-t border-zinc-800 flex items-center justify-between text-xs">
      <span class="text-zinc-500 font-mono text-[11px]">
        数据来源: Amazon Product API (NFR 幂等缓存)
      </span>
      <button
        @click="emit('close')"
        class="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-medium transition-colors"
      >
        完成查阅
      </button>
    </div>
  </aside>
</template>
