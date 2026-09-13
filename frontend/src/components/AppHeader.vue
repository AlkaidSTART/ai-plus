<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Bell, Plus } from '@lucide/vue'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const ui = useUiStore()
const title = computed(() => (route.meta.title as string | undefined) ?? '')
</script>

<template>
  <header class="flex h-14 shrink-0 items-center gap-2 border-b px-4">
    <SidebarTrigger class="-ml-1" />
    <Separator orientation="vertical" class="mr-2 !h-4" />
    <Breadcrumb>
      <BreadcrumbList>
        <BreadcrumbItem>
          <BreadcrumbPage>{{ title }}</BreadcrumbPage>
        </BreadcrumbItem>
      </BreadcrumbList>
    </Breadcrumb>
    <div class="ml-auto flex items-center gap-2">
      <Button size="sm" @click="ui.newTaskDialogOpen = true">
        <Plus />
        新建诊断任务
      </Button>
      <Button variant="ghost" size="icon" disabled title="告警中心为后续阶段能力">
        <Bell />
      </Button>
    </div>
  </header>
</template>
