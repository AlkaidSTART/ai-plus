<script setup lang="ts">
import type { FunctionalComponent } from 'vue'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'

/** 统一空态：图标 + 标题 + 说明 + 可选操作区。用于无数据/数据不足/阶段未开放。 */
defineProps<{
  icon?: FunctionalComponent
  title: string
  description?: string
}>()
</script>

<template>
  <Empty>
    <EmptyHeader>
      <EmptyMedia v-if="icon" variant="icon" class="animate-in fade-in zoom-in-95 duration-300">
        <component :is="icon" />
      </EmptyMedia>
      <EmptyTitle>{{ title }}</EmptyTitle>
      <EmptyDescription v-if="description">{{ description }}</EmptyDescription>
    </EmptyHeader>
    <EmptyContent v-if="$slots.default">
      <slot />
    </EmptyContent>
  </Empty>
</template>
