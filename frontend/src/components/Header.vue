<script setup lang="ts">
import {
  Check,
  ChevronDown,
  Columns2,
  Eye,
  LayoutDashboard,
  LogIn,
  LogOut,
  ShieldCheck,
  Sparkles,
  Workflow,
} from 'lucide-vue-next';
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import productLogo from '../assets/Product_logo.webp';
import { LOCALE_LABELS, setLocale, type SupportedLocale } from '../i18n';
import type { AuthUser, Marketplace } from '../types';

const props = defineProps<{
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

const isAsinMenuOpen = ref(false);
const isMarketplaceMenuOpen = ref(false);
const isLangMenuOpen = ref(false);
const isUserMenuOpen = ref(false);

const marketplaces: Marketplace[] = ['US', 'DE', 'JP', 'UK'];

const navItems = computed(() => [
  { key: 'dashboard', label: t('nav.overview'), icon: LayoutDashboard },
  { key: 'agent', label: t('nav.workflow'), icon: Workflow },
  { key: 'voc', label: t('nav.visual'), icon: Eye },
  { key: 'proposals', label: t('nav.proposals'), icon: Columns2 },
  { key: 'financial', label: t('nav.financial'), icon: ShieldCheck },
] as const);

const popularAsins: { asin: string; marketplace: Marketplace }[] = [
  { asin: 'B08N5WRWNW', marketplace: 'US' },
  { asin: 'B09V7K4P92', marketplace: 'DE' },
  { asin: 'B0CX87M2L1', marketplace: 'US' },
];

const getAsinName = (asin: string) => {
  return t(`header.products.${asin}`);
};

const currentLocaleInfo = computed(() => {
  return LOCALE_LABELS[locale.value as SupportedLocale] || LOCALE_LABELS.zh;
});

const closeAllDropdowns = () => {
  isAsinMenuOpen.value = false;
  isMarketplaceMenuOpen.value = false;
  isLangMenuOpen.value = false;
  isUserMenuOpen.value = false;
};

const toggleAsinMenu = () => {
  const willOpen = !isAsinMenuOpen.value;
  closeAllDropdowns();
  isAsinMenuOpen.value = willOpen;
};

const toggleMarketplaceMenu = () => {
  const willOpen = !isMarketplaceMenuOpen.value;
  closeAllDropdowns();
  isMarketplaceMenuOpen.value = willOpen;
};

const toggleLangMenu = () => {
  const willOpen = !isLangMenuOpen.value;
  closeAllDropdowns();
  isLangMenuOpen.value = willOpen;
};

const toggleUserMenu = () => {
  const willOpen = !isUserMenuOpen.value;
  closeAllDropdowns();
  isUserMenuOpen.value = willOpen;
};

const selectAsin = (asin: string) => {
  emit('selectAsin', asin);
  isAsinMenuOpen.value = false;
};

const selectMarketplace = (mp: Marketplace) => {
  emit('update:selectedMarketplace', mp);
  isMarketplaceMenuOpen.value = false;
};

const changeLocale = (target: SupportedLocale) => {
  setLocale(target);
  isLangMenuOpen.value = false;
};

const handleLogout = () => {
  emit('logout');
  isUserMenuOpen.value = false;
};

// ponytail: native document click listener handles dropdown dismissal; upgrade to floating-ui or @headlessui/vue when viewport-edge flipping is required.
const onDocumentClick = (e: MouseEvent) => {
  const target = e.target as HTMLElement | null;
  if (!target || !target.closest('[data-dropdown]')) {
    closeAllDropdowns();
  }
};

onMounted(() => {
  window.addEventListener('click', onDocumentClick);
});

onBeforeUnmount(() => {
  window.removeEventListener('click', onDocumentClick);
});
</script>

<template>
  <header class="sticky top-0 z-40 w-full border-b border-white/[0.07] bg-[#090a0d]/90 backdrop-blur-xl transition-all">
    <div class="max-w-[1600px] mx-auto px-3 sm:px-6">
      <div class="flex items-center justify-between h-14 gap-2 sm:gap-4">
        <!-- Left: Brand, ASIN Switcher & Agent Status -->
        <div class="flex items-center gap-2 sm:gap-3 shrink-0">
          <img
            :src="productLogo"
            alt="InsightX"
            class="h-6 sm:h-7 w-auto object-contain cursor-pointer transition-opacity hover:opacity-80 active:scale-95"
            @click="emit('openIntro')"
            :title="t('header.introTooltip')"
          />

          <span class="text-zinc-700 font-mono select-none hidden md:inline">/</span>

          <!-- ASIN Dropdown -->
          <div class="relative" data-dropdown>
            <button
              @click="toggleAsinMenu"
              class="flex items-center gap-1.5 sm:gap-2 h-8 px-2 sm:px-2.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.08] hover:border-white/[0.15] text-xs transition-all cursor-pointer select-none"
              :title="`${selectedAsin} · ${getAsinName(selectedAsin)}`"
            >
              <span class="text-[11px] font-mono text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/20 font-medium">
                {{ selectedAsin }}
              </span>
              <span class="text-zinc-300 font-medium truncate max-w-[70px] sm:max-w-[120px] hidden sm:inline">
                {{ getAsinName(selectedAsin) }}
              </span>
              <ChevronDown
                class="w-3 h-3 text-zinc-500 transition-transform duration-150"
                :class="{ 'rotate-180': isAsinMenuOpen }"
              />
            </button>

            <!-- Dropdown Menu -->
            <div
              v-if="isAsinMenuOpen"
              class="absolute left-0 mt-1.5 w-64 p-1.5 rounded-xl bg-[#111215] border border-white/[0.1] shadow-2xl z-50 text-xs space-y-1 backdrop-blur-xl"
            >
              <div class="px-2 py-1 text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
                {{ t('header.selectProduct') }}
              </div>
              <button
                v-for="item in popularAsins"
                :key="item.asin"
                @click="selectAsin(item.asin)"
                class="w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-left transition-colors cursor-pointer"
                :class="selectedAsin === item.asin
                  ? 'bg-indigo-500/15 text-white border border-indigo-500/30'
                  : 'text-zinc-300 hover:text-white hover:bg-white/[0.04] border border-transparent'"
              >
                <div class="flex flex-col min-w-0 pr-2">
                  <div class="flex items-center gap-1.5">
                    <span class="font-mono text-xs text-indigo-300 font-medium">{{ item.asin }}</span>
                    <span class="text-[10px] font-mono text-zinc-500 bg-white/[0.04] px-1 rounded">
                      {{ item.marketplace }}
                    </span>
                  </div>
                  <span class="text-[11px] text-zinc-400 truncate mt-0.5">
                    {{ getAsinName(item.asin) }}
                  </span>
                </div>
                <Check v-if="selectedAsin === item.asin" class="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              </button>
            </div>
          </div>

          <!-- Agent Status Badge -->
          <div
            class="hidden md:flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] font-mono select-none transition-colors border"
            :class="isAgentRunning
              ? 'bg-amber-500/10 border-amber-500/25 text-amber-300'
              : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'"
            :title="isAgentRunning ? t('header.agentRunning') : t('header.agentReady')"
          >
            <span class="relative flex h-2 w-2">
              <span
                v-if="isAgentRunning"
                class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"
              />
              <span
                class="relative inline-flex rounded-full h-2 w-2"
                :class="isAgentRunning ? 'bg-amber-400' : 'bg-emerald-400'"
              />
            </span>
            <span class="hidden 2xl:inline font-medium">
              {{ isAgentRunning ? t('header.agentRunning') : t('header.agentReady') }}
            </span>
          </div>
        </div>

        <!-- Desktop Nav Tabs (xl+ screens) -->
        <nav class="hidden 2xl:flex items-center gap-0.5 p-1 bg-white/[0.025] border border-white/[0.06] rounded-lg">
          <button
            v-for="item in navItems"
            :key="item.key"
            @click="emit('update:activeTab', item.key)"
            :class="[
              'h-7 px-2.5 rounded-md text-xs font-medium transition-all duration-150 flex items-center gap-1.5 select-none shrink-0',
              activeTab === item.key
                ? 'bg-white/[0.1] text-white shadow-xs font-semibold'
                : 'text-[#8a8f98] hover:text-[#d0d6e0] hover:bg-white/[0.04]'
            ]"
            :title="item.label"
          >
            <component
              :is="item.icon"
              class="w-3.5 h-3.5 shrink-0"
              :class="activeTab === item.key ? 'text-indigo-400' : 'text-zinc-500'"
            />
            <span class="whitespace-nowrap tracking-tight">{{ item.label }}</span>
          </button>
        </nav>

        <!-- Right Utilities: Tour, Lang, Marketplace, User Profile -->
        <div class="flex items-center gap-1 sm:gap-2 shrink-0">
          <!-- Tour CTA Button -->
          <button
            @click="emit('openIntro')"
            class="hidden md:flex items-center gap-1.5 h-8 px-2 sm:px-2.5 rounded-lg text-xs font-medium text-zinc-300 hover:text-white bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.08] hover:border-white/[0.15] transition-all cursor-pointer"
            :title="t('header.introTooltip')"
          >
            <Sparkles class="w-3.5 h-3.5 text-indigo-400 shrink-0" />
            <span class="hidden xl:inline">{{ t('header.intro') }}</span>
          </button>

          <!-- Language Selector Dropdown -->
          <div class="relative" data-dropdown>
            <button
              @click="toggleLangMenu"
              class="flex items-center gap-1.5 h-8 px-2 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.08] hover:border-white/[0.15] text-xs text-zinc-300 transition-all cursor-pointer select-none"
              title="Switch Language"
            >
              <span class="text-sm leading-none">{{ currentLocaleInfo.flag }}</span>
              <span class="font-mono text-[11px] font-medium hidden sm:inline">{{ locale.toUpperCase() }}</span>
              <ChevronDown
                class="w-3 h-3 text-zinc-500 transition-transform duration-150"
                :class="{ 'rotate-180': isLangMenuOpen }"
              />
            </button>

            <!-- Language Dropdown Menu -->
            <div
              v-if="isLangMenuOpen"
              class="absolute right-0 mt-1.5 w-44 p-1.5 rounded-xl bg-[#111215] border border-white/[0.1] shadow-2xl z-50 text-xs space-y-0.5 backdrop-blur-xl"
            >
              <button
                v-for="(info, key) in LOCALE_LABELS"
                :key="key"
                @click="changeLocale(key)"
                class="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-left transition-colors cursor-pointer"
                :class="locale === key
                  ? 'bg-indigo-500/15 text-indigo-300 font-medium'
                  : 'text-zinc-300 hover:text-white hover:bg-white/[0.04]'"
              >
                <div class="flex items-center gap-2">
                  <span class="text-sm leading-none">{{ info.flag }}</span>
                  <span>{{ info.native }}</span>
                </div>
                <Check v-if="locale === key" class="w-3.5 h-3.5 text-indigo-400" />
              </button>
            </div>
          </div>

          <!-- Marketplace Toggle: Mobile Dropdown (< sm), Segmented Control (sm+) -->
          <div class="relative sm:hidden" data-dropdown>
            <button
              @click="toggleMarketplaceMenu"
              class="flex items-center gap-1 h-8 px-2 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.08] hover:border-white/[0.15] text-xs font-mono font-semibold text-zinc-300 transition-all cursor-pointer select-none"
              title="Marketplace"
            >
              <span>{{ selectedMarketplace }}</span>
              <ChevronDown
                class="w-3 h-3 text-zinc-500 transition-transform duration-150"
                :class="{ 'rotate-180': isMarketplaceMenuOpen }"
              />
            </button>

            <div
              v-if="isMarketplaceMenuOpen"
              class="absolute right-0 mt-1.5 w-32 p-1.5 rounded-xl bg-[#111215] border border-white/[0.1] shadow-2xl z-50 text-xs space-y-0.5 backdrop-blur-xl"
            >
              <button
                v-for="mp in marketplaces"
                :key="mp"
                @click="selectMarketplace(mp)"
                class="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-left font-mono transition-colors cursor-pointer"
                :class="selectedMarketplace === mp
                  ? 'bg-indigo-500/15 text-indigo-300 font-semibold'
                  : 'text-zinc-300 hover:text-white hover:bg-white/[0.04]'"
              >
                <span>{{ mp }}</span>
                <Check v-if="selectedMarketplace === mp" class="w-3.5 h-3.5 text-indigo-400" />
              </button>
            </div>
          </div>

          <div class="hidden sm:flex items-center bg-white/[0.03] p-0.5 rounded-lg border border-white/[0.08]">
            <button
              v-for="mp in marketplaces"
              :key="mp"
              @click="emit('update:selectedMarketplace', mp)"
              :class="[
                'text-[11px] font-mono px-2 py-0.5 rounded-md transition-all font-medium',
                selectedMarketplace === mp
                  ? 'bg-white/[0.12] text-white shadow-xs'
                  : 'text-zinc-400 hover:text-zinc-200'
              ]"
            >
              {{ mp }}
            </button>
          </div>

          <!-- User Auth Profile or Login Button -->
          <div class="relative pl-1 border-l border-white/[0.08]" data-dropdown>
            <!-- If logged in -->
            <div v-if="currentUser" class="relative">
              <button
                @click="toggleUserMenu"
                class="flex items-center gap-1.5 h-8 p-1 pl-1.5 pr-2 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.08] hover:border-white/[0.15] transition-all cursor-pointer text-xs"
                :title="currentUser.name"
              >
                <div class="w-5 h-5 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-[10px] font-semibold text-indigo-300">
                  {{ currentUser.name.slice(0, 1).toUpperCase() }}
                </div>
                <span class="hidden md:inline text-xs font-medium text-zinc-300 max-w-[80px] truncate">
                  {{ currentUser.name }}
                </span>
                <ChevronDown
                  class="w-3 h-3 text-zinc-500 transition-transform duration-150"
                  :class="{ 'rotate-180': isUserMenuOpen }"
                />
              </button>

              <!-- User Dropdown Menu -->
              <div
                v-if="isUserMenuOpen"
                class="absolute right-0 mt-1.5 w-52 p-1.5 rounded-xl bg-[#111215] border border-white/[0.1] shadow-2xl z-50 text-xs space-y-1 backdrop-blur-xl"
              >
                <div class="px-2.5 py-2 border-b border-white/[0.06]">
                  <div class="font-medium text-white truncate">{{ currentUser.name }}</div>
                  <div class="text-[10px] font-mono text-zinc-400 truncate mt-0.5">{{ currentUser.roleName }}</div>
                  <div class="text-[10px] font-mono text-zinc-500 truncate">{{ currentUser.email }}</div>
                </div>

                <button
                  @click="handleLogout"
                  class="w-full text-left px-2.5 py-2 rounded-lg text-rose-400 hover:text-rose-300 hover:bg-rose-950/30 flex items-center gap-2 transition-colors cursor-pointer"
                >
                  <LogOut class="w-3.5 h-3.5" />
                  <span>{{ t('header.logout') }}</span>
                </button>
              </div>
            </div>

            <!-- If not logged in -->
            <button
              v-else
              @click="emit('openAuth')"
              class="flex items-center gap-1.5 h-8 px-2.5 sm:px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-all shadow-xs shadow-indigo-500/25 cursor-pointer shrink-0"
            >
              <LogIn class="w-3.5 h-3.5" />
              <span>{{ t('header.login') }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Secondary Sub-Navigation Strip (Screens < 2xl: mobile/tablet/laptop/desktop) -->
      <div class="2xl:hidden flex items-center gap-1.5 py-1.5 border-t border-white/[0.06] overflow-x-auto scrollbar-none">
        <button
          v-for="item in navItems"
          :key="item.key"
          @click="emit('update:activeTab', item.key)"
          :class="[
            'h-7 px-2.5 rounded-md text-xs font-medium whitespace-nowrap transition-colors flex items-center gap-1.5 shrink-0 select-none',
            activeTab === item.key
              ? 'bg-white/[0.12] text-white shadow-xs font-semibold'
              : 'text-[#8a8f98] hover:text-[#d0d6e0] hover:bg-white/[0.04]'
          ]"
        >
          <component
            :is="item.icon"
            class="w-3.5 h-3.5 shrink-0"
            :class="activeTab === item.key ? 'text-indigo-400' : 'text-zinc-500'"
          />
          <span>{{ item.label }}</span>
        </button>
      </div>
    </div>
  </header>
</template>
