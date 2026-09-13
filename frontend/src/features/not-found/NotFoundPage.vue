<script setup lang="ts">
import { Compass } from '@lucide/vue'
import { RouterLink } from 'vue-router'
import EmptyState from '@/components/EmptyState.vue'
import { Button } from '@/components/ui/button'
</script>

<template>
  <div class="mx-auto flex w-full max-w-[1440px] items-center justify-center p-4 lg:p-6">
    <EmptyState :icon="Compass" title="页面不存在" description="请从侧边栏导航进入有效页面">
      <Button as-child variant="outline">
        <RouterLink to="/dashboard">返回战略决策大盘</RouterLink>
      </Button>
    </EmptyState>
  </div>
</template>
