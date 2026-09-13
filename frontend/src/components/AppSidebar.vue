<script setup lang="ts">
import {
  Factory,
  LayoutDashboard,
  MessageSquareText,
  Radar,
  ShieldCheck,
} from '@lucide/vue'
import { RouterLink, useRoute } from 'vue-router'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar'

/** 主导航 = PRD 第四节 5 个模块。 */
const items = [
  { to: '/dashboard', title: '战略决策大盘', icon: LayoutDashboard },
  { to: '/radar', title: '竞品时序监控', icon: Radar },
  { to: '/voc', title: '多模态评论洞察', icon: MessageSquareText },
  { to: '/reformulation', title: '工厂级改款决策', icon: Factory },
  { to: '/financial', title: '逆向财务与风控', icon: ShieldCheck },
]

const route = useRoute()
</script>

<template>
  <Sidebar collapsible="icon">
    <SidebarHeader>
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton size="lg" as-child>
            <RouterLink to="/dashboard">
              <div class="grid flex-1 text-left leading-tight">
                <span class="truncate text-sm font-semibold">InsightX</span>
                <span class="truncate text-xs text-muted-foreground">跨境电商 AI 决策</span>
              </div>
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarHeader>
    <SidebarContent>
      <SidebarGroup>
        <SidebarGroupLabel>主导航</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem v-for="item in items" :key="item.to">
              <SidebarMenuButton
                as-child
                :data-active="route.path.startsWith(item.to)"
                :tooltip="item.title"
              >
                <RouterLink :to="item.to">
                  <component :is="item.icon" />
                  <span>{{ item.title }}</span>
                </RouterLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>
    <SidebarFooter>
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton size="lg">
            <Avatar class="size-8">
              <AvatarFallback class="text-xs">控</AvatarFallback>
            </Avatar>
            <div class="grid flex-1 text-left leading-tight">
              <span class="truncate text-sm font-medium">受控账号</span>
              <span class="truncate text-xs text-muted-foreground">本地会话（占位）</span>
            </div>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarFooter>
    <SidebarRail />
  </Sidebar>
</template>
