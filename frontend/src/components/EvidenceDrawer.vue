<script setup lang="ts">
import {
  Calendar,
  X,
} from 'lucide-vue-next';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

defineProps<{
  isOpen: boolean;
  targetTitle: string;
  evidenceCount: number;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const { t } = useI18n();

const ratingFilter = ref<number | null>(null);

interface MockReview {
  id: string;
  rating: number;
  date: string;
  author: string;
  country: string;
  title: string;
  content: string;
  translated: string;
  defectTag: string;
}

const mockReviews: MockReview[] = [
  {
    id: 'R1-AMZ-8821',
    rating: 1,
    date: '2026-08-14',
    author: 'Michael B.',
    country: 'US',
    title: 'Snapped clean off on the 18th day',
    content: 'I was simply adjusting the armrest height while sitting down, and heard a loud plastic cracking sound. The inner gear teeth sheared completely off.',
    translated: '我只是坐着调节扶手高度，就听到很大的塑料断裂声。内部的齿轮咬合齿完全被剪切断了。',
    defectTag: 'PA6-GF 齿条应力撕裂',
  },
  {
    id: 'R1-AMZ-9932',
    rating: 1,
    date: '2026-08-20',
    author: 'Sarah Jenkins',
    country: 'US',
    title: 'Box arrived in shredded state',
    content: 'FedEx delivery guy dropped the box and the corner split wide open. The heavy metal mechanism crushed through the cardboard.',
    translated: 'FedEx 快递员把箱子放下时边角直接爆裂了。重型金属底盘刺穿了瓦楞纸板，把扶手刮花了。',
    defectTag: '单坑纸箱角部跌落击穿',
  },
  {
    id: 'R2-AMZ-6611',
    rating: 2,
    date: '2026-08-25',
    author: 'David Schmidt',
    country: 'DE',
    title: 'Lumbar support has zero locking friction',
    content: 'Die Lordosenstütze rutscht ständig nach unten. Jedes Mal wenn man sich anlehnt, verliert die Rastung den Halt.',
    translated: '腰靠不断自发下滑。每次靠上去，卡位阻尼就会完全失效。',
    defectTag: '滑槽阻尼公差偏大',
  },
  {
    id: 'R3-AMZ-3320',
    rating: 1,
    date: '2026-09-01',
    author: 'Kenji T.',
    country: 'JP',
    title: 'Ruined my wood flooring',
    content: 'フローリングに黒い擦り伤がたくさんつきました。キャスターの素材が硬すぎてゴムのカスが出ます。',
    translated: '木质地板上被蹭出了很多黑色划痕。脚轮的材质太硬，在地面摩擦会掉出黑色细屑。',
    defectTag: 'PU包胶轮碳黑析出',
  },
];

const filteredReviews = computed(() => {
  if (ratingFilter.value === null) return mockReviews;
  return mockReviews.filter(r => r.rating === ratingFilter.value);
});
</script>

<template>
  <!-- Backdrop -->
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm transition-opacity"
    @click="emit('close')"
  />

  <!-- Right Slide Drawer -->
  <aside
    :class="[
      'fixed top-0 right-0 bottom-0 z-50 w-full max-w-lg bg-[#0c0d0e] border-l border-[rgba(255,255,255,0.08)] p-6 shadow-2xl transition-transform duration-200 ease-out flex flex-col justify-between overflow-hidden',
      isOpen ? 'translate-x-0' : 'translate-x-full'
    ]"
  >
    <!-- Header -->
    <div class="space-y-3 pb-4 border-b border-[rgba(255,255,255,0.06)]">
      <div class="flex items-center justify-between">
        <h2 class="text-sm font-medium text-[#f7f8f8]">{{ t('drawer.title') }}</h2>
        <button
          @click="emit('close')"
          class="p-1 text-[#8a8f98] hover:text-[#f7f8f8] transition-colors"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <div class="text-xs text-[#8a8f98] line-clamp-1 font-mono">
        {{ t('drawer.related') }} <span class="text-[#f7f8f8]">{{ targetTitle }}</span>
      </div>

      <!-- Rating Filter -->
      <div class="flex items-center gap-1.5 pt-1 text-xs font-mono">
        <span class="text-[#5e626e] text-[11px]">{{ t('drawer.ratingFilter') }}</span>
        <button
          @click="ratingFilter = null"
          :class="[
            'px-2 py-0.5 rounded text-[11px] transition-colors',
            ratingFilter === null ? 'bg-[rgba(255,255,255,0.1)] text-[#f7f8f8]' : 'text-[#8a8f98] hover:text-[#f7f8f8]'
          ]"
        >
          {{ t('drawer.all') }}
        </button>
        <button
          @click="ratingFilter = 1"
          :class="[
            'px-2 py-0.5 rounded text-[11px] transition-colors',
            ratingFilter === 1 ? 'bg-[rgba(255,255,255,0.1)] text-[#f7f8f8]' : 'text-[#8a8f98] hover:text-[#f7f8f8]'
          ]"
        >
          {{ t('drawer.star1') }}
        </button>
        <button
          @click="ratingFilter = 2"
          :class="[
            'px-2 py-0.5 rounded text-[11px] transition-colors',
            ratingFilter === 2 ? 'bg-[rgba(255,255,255,0.1)] text-[#f7f8f8]' : 'text-[#8a8f98] hover:text-[#f7f8f8]'
          ]"
        >
          {{ t('drawer.star2') }}
        </button>
      </div>
    </div>

    <!-- Review List -->
    <div class="flex-1 overflow-y-auto py-4 space-y-3 pr-1 scrollbar-thin">
      <div
        v-for="rev in filteredReviews"
        :key="rev.id"
        class="p-3.5 rounded-lg bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] space-y-2 text-xs"
      >
        <div class="flex items-center justify-between text-[11px] font-mono text-[#8a8f98]">
          <div class="flex items-center gap-1.5">
            <span class="text-amber-400 font-medium">★ {{ rev.rating }}</span>
            <span>· {{ rev.author }} ({{ rev.country }})</span>
          </div>
          <div class="flex items-center gap-1 text-[#5e626e]">
            <Calendar class="w-3 h-3" />
            <span>{{ rev.date }}</span>
          </div>
        </div>

        <div class="text-[#f7f8f8] font-medium">{{ rev.title }}</div>
        <p class="text-[#8a8f98] leading-relaxed italic text-[11px]">"{{ rev.content }}"</p>
        <p class="text-zinc-300 text-[11px] pt-1 border-t border-[rgba(255,255,255,0.04)]">
          ↳ {{ rev.translated }}
        </p>
      </div>
    </div>

    <!-- Footer -->
    <div class="pt-3 border-t border-[rgba(255,255,255,0.06)] flex items-center justify-between text-[11px] text-[#5e626e] font-mono">
      <span>{{ t('drawer.verifiedReview') }}</span>
      <button
        @click="emit('close')"
        class="ln-btn px-3 py-1 text-xs"
      >
        {{ t('common.close') }}
      </button>
    </div>
  </aside>
</template>
