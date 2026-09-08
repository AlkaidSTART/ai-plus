<script setup lang="ts">
import {
  ChevronDown,
} from 'lucide-vue-next';
import productLogo from '../assets/Product_logo.webp';
import type { Marketplace } from '../types';

defineProps<{
  activeTab: 'dashboard' | 'agent' | 'voc' | 'proposals' | 'financial';
  selectedMarketplace: Marketplace;
  selectedAsin: string;
  isAgentRunning?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:activeTab', tab: 'dashboard' | 'agent' | 'voc' | 'proposals' | 'financial'): void;
  (e: 'update:selectedMarketplace', mp: Marketplace): void;
  (e: 'selectAsin', asin: string): void;
}>();

const marketplaces: Marketplace[] = ['US', 'DE', 'JP', 'UK'];

const navItems = [
  { key: 'dashboard', label: '全景总览' },
  { key: 'agent', label: '诊断流程' },
  { key: 'voc', label: '视觉取证' },
  { key: 'proposals', label: '双栏改款' },
  { key: 'financial', label: '财务风控' },
] as const;

const popularAsins = [
  { asin: 'B08N5WRWNW', name: '人体工学椅 (US)' },
  { asin: 'B09V7K4P92', name: '破壁料理机 (DE)' },
  { asin: 'B0CX87M2L1', name: '便携储能电源 (US)' },
];
</script>

<template>
  <header class="sticky top-0 z-40 border-b border-[rgba(255,255,255,0.07)] bg-[#08090a]/90 backdrop-blur-xl">
    <div class="max-w-6xl mx-auto px-4 sm:px-6">
      <div class="flex items-center justify-between h-14 gap-4">
        <!-- Brand & Product Breadcrumb -->
        <div class="flex items-center gap-3 shrink-0">
          <div class="flex items-center gap-2">
            <img :src="productLogo" alt="InsightX" class="h-7 w-auto object-contain" />
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

        <!-- Navigation Tabs (Clean Linear-Style Segmented List) -->
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

        <!-- Right Side: Marketplace & Status Dot -->
        <div class="flex items-center gap-3 shrink-0">
          <!-- Marketplace Pills -->
          <div class="flex items-center bg-[rgba(255,255,255,0.03)] p-0.5 rounded-md border border-[rgba(255,255,255,0.06)]">
            <button
              v-for="mp in marketplaces"
              :key="mp"
              @click="emit('update:selectedMarketplace', mp)"
              :class="[
                'text-[11px] font-mono px-2 py-0.5 rounded transition-colors',
                selectedMarketplace === mp
                  ? 'bg-[rgba(255,255,255,0.1)] text-[#f7f8f8]'
                  : 'text-zinc-500 hover:text-zinc-300'
              ]"
            >
              {{ mp }}
            </button>
          </div>

          <!-- Status Indicator: Quiet 6px dot -->
          <div class="flex items-center gap-2 text-xs font-mono text-[#8a8f98] pl-2 border-l border-[rgba(255,255,255,0.06)]">
            <span
              :class="[
                'w-1.5 h-1.5 rounded-full',
                isAgentRunning ? 'bg-[#7170ff] animate-pulse' : 'bg-[#10b981]'
              ]"
            />
            <span class="hidden md:inline text-[11px]">
              {{ isAgentRunning ? 'Agent 计算中' : '就绪' }}
            </span>
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
