<script setup lang="ts">
import { computed } from 'vue'
import { Badge } from '@/components/ui/badge'
import type { Severity } from '@/types/domain'

/** 痛点严重度徽章：Critical / Moderate / Minor。 */
const props = defineProps<{ severity: Severity }>()

const MAP: Record<Severity, { label: string; class: string }> = {
  CRITICAL: { label: '严重', class: 'border-red-200 bg-danger-soft text-destructive' },
  MODERATE: { label: '中等', class: 'border-amber-200 bg-warning-soft text-warning' },
  MINOR: { label: '轻微', class: 'border-slate-200 bg-neutral-soft text-slate-500' },
}

const item = computed(() => MAP[props.severity])
</script>

<template>
  <Badge variant="outline" :class="item.class">{{ item.label }}</Badge>
</template>
