<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from './components/layout/AppLayout.vue'

const route = useRoute()
// 登录页等公开路由不套用主布局（无侧边栏/顶栏）
const isPublic = computed(() => route.meta.public === true)
</script>

<template>
  <AppLayout v-if="!isPublic">
    <template #default>
      <router-view v-slot="{ Component }">
        <Transition name="fade-up" mode="out-in">
          <component :is="Component" />
        </Transition>
      </router-view>
    </template>
  </AppLayout>
  <router-view v-else v-slot="{ Component }">
    <Transition name="fade-up" mode="out-in">
      <component :is="Component" />
    </Transition>
  </router-view>
</template>
