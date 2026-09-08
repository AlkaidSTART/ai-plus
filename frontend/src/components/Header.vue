<script setup lang="ts">
import {
  ChevronDown,
  Globe,
  LogIn,
  LogOut,
  Sparkles,
} from 'lucide-vue-next';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import productLogo from '../assets/Product_logo.webp';
import { LOCALE_LABELS, setLocale, type SupportedLocale } from '../i18n';
import type { AuthUser, Marketplace } from '../types';

defineProps<{
  activeTab: 'dashboard' | 'agent' | 'voc' | 'proposals' | 'financial';
  selectedMarketplace: Marketplace;
  selectedAsin: string;
  isAgentRunning?: boolean;
  currentUser?: AuthUser | null;
}>();

const emit = defineEmits<{
  (e: 'update:activeTab', tab: 'dashboard' | 'agent' | 'voc' | 'proposals' | 'financial'): void;
  (e: 'update:selectedMarketplace', mp: Marketplace): void;
  (e: 'selectAsin', asin: string): void;
  (e: 'openAuth'): void;
  (e: 'openIntro'): void;
  (e: 'logout'): void;
}>();

const { t, locale } = useI18n();
const isUserMenuOpen = ref(false);

const marketplaces: Marketplace[] = ['US', 'DE', 'JP', 'UK'];

const navItems = computed(() => [
  { key: 'dashboard', label: t('nav.overview') },
  { key: 'agent', label: t('nav.workflow') },
  { key: 'voc', label: t('nav.visual') },
  { key: 'proposals', label: t('nav.proposals') },
  { key: 'financial', label: t('nav.financial') },
] as const);

const popularAsins = [
  { asin: 'B08N5WRWNW', name: '人体工学椅 (US)' },
  { asin: 'B09V7K4P92', name: '破壁料理机 (DE)' },
  { asin: 'B0CX87M2L1', name: '便携储能电源 (US)' },
];

const changeLocale = (target: SupportedLocale) => {
  setLocale(target);
};
</script>

<template>
  <header class="sticky top-0 z-40 border-b border-[rgba(255,255,255,0.07)] bg-[#08090a]/90 backdrop-blur-xl">
    <div class="max-w-6xl mx-auto px-4 sm:px-6">
      <div class="flex items-center justify-between h-14 gap-4">
        <!-- Brand & Product Breadcrumb -->
        <div class="flex items-center gap-3 shrink-0">
          <div class="flex items-center gap-2">
            <img :src="productLogo" alt="InsightX" class="h-7 w-auto object-contain cursor-pointer" @click="emit('openIntro')" title="查看产品介绍" />
            <span class="text-zinc-600 font-mono">/</span>
            <div class="relative flex items-center">
              <select
                :value="selectedAsin"
                @change="emit('selectAsin', ($event.target as HTMLSelectElement).value)"
                class="appearance-none bg-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.06)] border border-[rgba(255,255,255,0.08)] rounded-md pl-2.5 pr-7 py-1 text-xs font-mono text-zinc-300 focus:outline-none cursor-pointer transition-colors"
              >
                <option v-for="item in popularAsins" :key="item.asin" :value="item.asin" class="bg-[#0f1011] text-zinc-200">
                  {{ item.asin }} · {{ item.name }}
                </option>
              </select>
              <ChevronDown class="w-3 h-3 text-zinc-500 absolute right-2 pointer-events-none" />
            </div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <nav class="hidden sm:flex items-center gap-1">
          <button
            v-for="item in navItems"
            :key="item.key"
            @click="emit('update:activeTab', item.key)"
            :class="[
              'px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150',
              activeTab === item.key
                ? 'bg-[rgba(255,255,255,0.08)] text-[#f7f8f8] shadow-sm'
                : 'text-[#8a8f98] hover:text-[#d0d6e0] hover:bg-[rgba(255,255,255,0.03)]'
            ]"
          >
            {{ item.label }}
          </button>
        </nav>

        <!-- Right Side: Intro CTA, Marketplace, i18n & User Profile -->
        <div class="flex items-center gap-2 shrink-0">
          <!-- Re-watch Intro CTA -->
          <button
            @click="emit('openIntro')"
            class="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono text-zinc-400 hover:text-zinc-200 bg-[rgba(255,255,255,0.02)] hover:bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.06)] transition-colors"
            title="重新播放 GSAP 产品介绍"
          >
            <Sparkles class="w-3 h-3 text-[#7170ff]" />
            <span>产品介绍</span>
          </button>

          <!-- i18n Language Selector Dropdown -->
          <div class="relative flex items-center">
            <Globe class="w-3.5 h-3.5 text-zinc-500 mr-1 hidden md:inline" />
            <select
              :value="locale"
              @change="changeLocale(($event.target as HTMLSelectElement).value as SupportedLocale)"
              class="appearance-none bg-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.06)] border border-[rgba(255,255,255,0.08)] rounded-md pl-2 pr-5 py-0.5 text-[11px] font-mono text-zinc-300 focus:outline-none cursor-pointer transition-colors"
              title="Switch Language"
            >
              <option v-for="(info, key) in LOCALE_LABELS" :key="key" :value="key" class="bg-[#0f1011] text-zinc-200">
                {{ info.flag }} {{ info.native }}
              </option>
            </select>
            <ChevronDown class="w-3 h-3 text-zinc-500 absolute right-1 pointer-events-none" />
          </div>

          <!-- Marketplace Pills -->
          <div class="flex items-center bg-[rgba(255,255,255,0.03)] p-0.5 rounded-md border border-[rgba(255,255,255,0.06)]">
            <button
              v-for="mp in marketplaces"
              :key="mp"
              @click="emit('update:selectedMarketplace', mp)"
              :class="[
                'text-[11px] font-mono px-1.5 py-0.5 rounded transition-colors',
                selectedMarketplace === mp
                  ? 'bg-[rgba(255,255,255,0.1)] text-[#f7f8f8]'
                  : 'text-zinc-500 hover:text-zinc-300'
              ]"
            >
              {{ mp }}
            </button>
          </div>

          <!-- User Auth Profile or Login Button -->
          <div class="relative pl-1 border-l border-[rgba(255,255,255,0.06)]">
            <!-- If logged in -->
            <div v-if="currentUser" class="relative">
              <button
                @click="isUserMenuOpen = !isUserMenuOpen"
                class="flex items-center gap-1.5 p-1 rounded-md hover:bg-[rgba(255,255,255,0.05)] transition-colors text-xs"
              >
                <div class="w-6 h-6 rounded-full bg-[#7170ff]/20 border border-[#7170ff]/40 flex items-center justify-center text-[11px] font-medium text-[#7170ff]">
                  {{ currentUser.name.slice(0, 1) }}
                </div>
                <span class="hidden md:inline text-[11px] font-mono text-zinc-300 max-w-[80px] truncate">
                  {{ currentUser.name }}
                </span>
                <ChevronDown class="w-3 h-3 text-zinc-500" />
              </button>

              <!-- Dropdown Menu -->
              <div
                v-if="isUserMenuOpen"
                class="absolute right-0 mt-2 w-48 p-2 rounded-xl bg-[#121316] border border-[rgba(255,255,255,0.1)] shadow-2xl z-50 text-xs space-y-1"
                @click="isUserMenuOpen = false"
              >
                <div class="px-2 py-1.5 border-b border-[rgba(255,255,255,0.06)] space-y-0.5">
                  <div class="font-medium text-[#f7f8f8] truncate">{{ currentUser.name }}</div>
                  <div class="text-[10px] font-mono text-[#8a8f98]">{{ currentUser.roleName }}</div>
                </div>

                <button
                  @click="emit('logout')"
                  class="w-full text-left px-2 py-1.5 rounded-lg text-rose-400 hover:bg-rose-950/30 flex items-center gap-2 transition-colors"
                >
                  <LogOut class="w-3.5 h-3.5" />
                  <span>退出登录</span>
                </button>
              </div>
            </div>

            <!-- If not logged in -->
            <button
              v-else
              @click="emit('openAuth')"
              class="ln-btn px-2.5 py-1 text-[11px] flex items-center gap-1 text-[#d0d6e0] hover:text-white"
            >
              <LogIn class="w-3 h-3" />
              <span>登录</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Mobile Tab Row -->
      <div class="sm:hidden flex items-center space-x-1 py-1.5 border-t border-[rgba(255,255,255,0.05)] overflow-x-auto scrollbar-none">
        <button
          v-for="item in navItems"
          :key="item.key"
          @click="emit('update:activeTab', item.key)"
          :class="[
            'px-2.5 py-1 rounded text-xs font-medium whitespace-nowrap transition-colors',
            activeTab === item.key
              ? 'bg-[rgba(255,255,255,0.08)] text-[#f7f8f8]'
              : 'text-[#8a8f98]'
          ]"
        >
          {{ item.label }}
        </button>
      </div>
    </div>
  </header>
</template>
