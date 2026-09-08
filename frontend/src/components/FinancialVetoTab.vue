<script setup lang="ts">
import {
  AlertOctagon,
  CheckCircle2,
  RotateCcw,
} from 'lucide-vue-next';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const moldCost = ref(12000);
const moq = ref(3000);
const unitPrice = ref(189.99);
const baseMarginPercent = ref(28);
const targetPaybackMonths = ref(6);
const monthlySales = ref(400);
const fbaSavingsPerUnit = ref(4.60);
const physicalCostDelta = ref(1.45);

const amortizedMoldCost = computed(() => {
  if (moq.value <= 0) return 0;
  return moldCost.value / moq.value;
});

const netUnitProfitDelta = computed(() => {
  return fbaSavingsPerUnit.value - physicalCostDelta.value - amortizedMoldCost.value;
});

const projectedMarginPercent = computed(() => {
  const baseMarginDollar = unitPrice.value * (baseMarginPercent.value / 100);
  const newMarginDollar = baseMarginDollar + netUnitProfitDelta.value;
  return Math.max(0, (newMarginDollar / unitPrice.value) * 100);
});

const breakevenUnits = computed(() => {
  const marginPerUnit = unitPrice.value * (projectedMarginPercent.value / 100);
  if (marginPerUnit <= 0) return 999999;
  return Math.ceil(moldCost.value / marginPerUnit);
});

const calculatedPaybackMonths = computed(() => {
  if (monthlySales.value <= 0) return 999;
  return Number((breakevenUnits.value / monthlySales.value).toFixed(1));
});

const isVetoed = computed(() => {
  return (
    calculatedPaybackMonths.value > targetPaybackMonths.value ||
    projectedMarginPercent.value < 15 ||
    amortizedMoldCost.value > unitPrice.value * 0.15
  );
});

const resetDefaults = () => {
  moldCost.value = 12000;
  moq.value = 3000;
  unitPrice.value = 189.99;
  baseMarginPercent.value = 28;
  targetPaybackMonths.value = 6;
  monthlySales.value = 400;
  fbaSavingsPerUnit.value = 4.60;
  physicalCostDelta.value = 1.45;
};

const applyVetoScenario = () => {
  moldCost.value = 45000;
  moq.value = 1500;
  unitPrice.value = 149.99;
  baseMarginPercent.value = 18;
  targetPaybackMonths.value = 6;
  monthlySales.value = 200;
  fbaSavingsPerUnit.value = 1.20;
  physicalCostDelta.value = 8.50;
};
</script>

<template>
  <div class="space-y-6">
    <!-- Top Header & Preset Controls -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[rgba(255,255,255,0.06)]">
      <div class="space-y-1">
        <h1 class="text-xl font-medium tracking-tight text-[#f7f8f8]">
          {{ t('financial.title') }}
        </h1>
        <p class="text-xs text-[#8a8f98]">
          {{ t('financial.subtitle') }}
        </p>
      </div>

      <div class="flex items-center gap-2">
        <button
          @click="applyVetoScenario"
          class="ln-btn px-3 py-1.5 text-xs text-rose-400 hover:text-rose-300"
        >
          {{ t('financial.caseBlender') }}
        </button>
        <button
          @click="resetDefaults"
          class="p-1.5 ln-btn"
          :title="t('common.retry')"
        >
          <RotateCcw class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>

    <!-- Quiet, Minimalist Decision Status Banner -->
    <div
      :class="[
        'ln-surface p-5 space-y-3 transition-colors',
        isVetoed
          ? 'border-rose-500/30 bg-rose-950/10'
          : 'border-emerald-500/30 bg-emerald-950/10'
      ]"
    >
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <AlertOctagon v-if="isVetoed" class="w-4 h-4 text-rose-400" />
          <CheckCircle2 v-else class="w-4 h-4 text-emerald-400" />
          <span class="text-xs font-semibold text-[#f7f8f8]">
            {{ isVetoed ? t('financial.vetoedTitle') : t('financial.approvedTitle') }}
          </span>
        </div>

        <span class="text-xs font-mono text-[#8a8f98]">
          {{ t('financial.calculatedPayback', { months: calculatedPaybackMonths, threshold: targetPaybackMonths }) }}
        </span>
      </div>

      <p class="text-xs text-[#8a8f98] leading-relaxed">
        <span v-if="isVetoed">
          {{ t('financial.vetoedDesc') }}
        </span>
        <span v-else>
          {{ t('financial.approvedDesc') }}
        </span>
      </p>
    </div>

    <!-- 2-Column Split: Sliders vs Calculation Summary -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
      <!-- Left (7 cols): Clean Sliders -->
      <div class="lg:col-span-7 ln-surface p-6 space-y-5">
        <div class="text-xs font-medium text-[#f7f8f8] pb-2 border-b border-[rgba(255,255,255,0.06)]">
          {{ t('financial.parametersTitle') }}
        </div>

        <div class="space-y-4 text-xs">
          <!-- Mold Cost -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="text-[#8a8f98]">{{ t('financial.moldCost') }}</span>
              <span class="font-mono text-[#f7f8f8]">${{ moldCost.toLocaleString() }}</span>
            </div>
            <input
              v-model.number="moldCost"
              type="range"
              min="2000"
              max="60000"
              step="1000"
              class="w-full accent-[#7170ff] cursor-pointer"
            />
          </div>

          <!-- MOQ -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="text-[#8a8f98]">{{ t('financial.moq') }}</span>
              <span class="font-mono text-[#f7f8f8]">{{ moq.toLocaleString() }} {{ t('common.units') }}</span>
            </div>
            <input
              v-model.number="moq"
              type="range"
              min="500"
              max="10000"
              step="250"
              class="w-full accent-[#7170ff] cursor-pointer"
            />
          </div>

          <!-- Unit Selling Price -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="text-[#8a8f98]">{{ t('financial.retailPrice') }}</span>
              <span class="font-mono text-[#f7f8f8]">${{ unitPrice.toFixed(2) }}</span>
            </div>
            <input
              v-model.number="unitPrice"
              type="range"
              min="50"
              max="500"
              step="5"
              class="w-full accent-[#7170ff] cursor-pointer"
            />
          </div>

          <!-- Target Payback -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="text-[#8a8f98]">{{ t('financial.targetPayback') }}</span>
              <span class="font-mono text-[#f7f8f8]">{{ targetPaybackMonths }} {{ t('common.months') }}</span>
            </div>
            <input
              v-model.number="targetPaybackMonths"
              type="range"
              min="2"
              max="12"
              step="1"
              class="w-full accent-[#7170ff] cursor-pointer"
            />
          </div>
        </div>
      </div>

      <!-- Right (5 cols): Dynamic Output Summary -->
      <div class="lg:col-span-5 ln-surface p-6 space-y-4">
        <div class="text-xs font-medium text-[#f7f8f8] pb-2 border-b border-[rgba(255,255,255,0.06)]">
          {{ t('financial.metricsTitle') }}
        </div>

        <div class="space-y-3 font-mono text-xs text-[#8a8f98]">
          <div class="flex items-center justify-between">
            <span>{{ t('financial.moldAmortization') }}</span>
            <span class="text-[#f7f8f8]">${{ amortizedMoldCost.toFixed(2) }}</span>
          </div>

          <div class="flex items-center justify-between">
            <span>{{ t('financial.logisticsBenefit') }}</span>
            <span class="text-emerald-400">-${{ fbaSavingsPerUnit.toFixed(2) }}</span>
          </div>

          <div class="flex items-center justify-between">
            <span>{{ t('financial.projectedMargin') }}</span>
            <span
              :class="projectedMarginPercent < 20 ? 'text-rose-400 font-bold' : 'text-[#f7f8f8] font-bold'"
            >
              {{ projectedMarginPercent.toFixed(1) }}%
            </span>
          </div>

          <div class="flex items-center justify-between">
            <span>{{ t('financial.breakeven') }}</span>
            <span class="text-[#f7f8f8]">{{ breakevenUnits }} {{ t('common.units') }}</span>
          </div>

          <div class="flex items-center justify-between pt-2 border-t border-[rgba(255,255,255,0.06)]">
            <span class="text-zinc-300 font-medium">{{ t('financial.estimatedPayback') }}</span>
            <span
              :class="isVetoed ? 'text-rose-400 font-bold text-sm' : 'text-emerald-400 font-bold text-sm'"
            >
              {{ calculatedPaybackMonths }} {{ t('common.months') }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Quiet Historical Backtest Summary -->
    <div class="ln-surface p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
      <div class="space-y-0.5">
        <div class="text-[#f7f8f8] font-medium">{{ t('financial.backtestTitle') }}</div>
        <div class="text-[#8a8f98] text-[11px]">{{ t('financial.backtestDesc') }}</div>
      </div>
      <div class="font-mono text-emerald-400 font-medium shrink-0">
        {{ t('financial.backtestScore') }}
      </div>
    </div>
  </div>
</template>
