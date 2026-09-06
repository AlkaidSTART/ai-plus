<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTasksStore } from '@/stores/tasks'
import { useAuthStore } from '@/stores/auth'
import type { CreateTaskRequest } from '@/types'

const route = useRoute()
const router = useRouter()
const tasksStore = useTasksStore()
const auth = useAuthStore()

const sidebarOpen = ref(false)
const userMenuOpen = ref(false)

const userInitial = computed(() => (auth.displayName ? auth.displayName.charAt(0).toUpperCase() : 'U'))

function toggleUserMenu(e: MouseEvent) {
  e.stopPropagation()
  userMenuOpen.value = !userMenuOpen.value
}

function onDocClick() {
  userMenuOpen.value = false
}

function logout() {
  userMenuOpen.value = false
  auth.logout()
  router.replace('/login')
}

onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))

const navItems = [
  { path: '/', label: '战略决策大盘', icon: 'grid' },
  { path: '/products', label: '竞品时序监控', icon: 'trend' },
  { path: '/voc', label: '多模态评论洞察', icon: 'chat' },
  { path: '/reformulation', label: '工厂级改款决策', icon: 'cube' },
  { path: '/financial', label: '逆向财务与风控熔断', icon: 'shield' },
] as const

const pageTitle = computed(() => (route.meta.title as string) ?? 'InsightX')

const ICONS: Record<string, string> = {
  grid: 'M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z',
  trend: 'M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941',
  chat: 'M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z',
  cube: 'm21 7.5-9-5.25L3 7.5m18 0-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9',
  shield: 'M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z',
  bell: 'M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0',
  plus: 'M12 4.5v15m7.5-7.5h-15',
  x: 'M6 18 18 6M6 6l12 12',
}

/** 默认诊断任务请求（mock 演示） */
const DEFAULT_TASK_REQ: CreateTaskRequest = {
  asins: ['B0D2XYZ8KQ', 'B0C5JXM1Z2'],
  marketplace: 'US',
  review_window_months: 6,
  financial_constraint: {
    mold_cost_usd: 8500,
    moq: 2000,
    current_gross_margin: 0.22,
    expected_price_usd: 29.99,
    unit_cost_increase_usd: 0.85,
    expected_payback_months: 8,
    sea_freight_usd_per_cbm: 420,
  },
  options: { enable_vision_audit: true, enable_backtest: true },
}

const creating = ref(false)
async function startNewTask() {
  creating.value = true
  try {
    const ids = await tasksStore.createAndWatchTask(DEFAULT_TASK_REQ)
    if (ids.length) router.push('/voc')
  } finally {
    creating.value = false
  }
}

function go(path: string) {
  sidebarOpen.value = false
  router.push(path)
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 text-slate-800">
    <!-- 移动端遮罩 -->
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 z-30 bg-black/40 lg:hidden"
      @click="sidebarOpen = false"
    />

    <!-- 侧边栏 -->
    <aside
      class="fixed inset-y-0 left-0 z-40 flex w-60 flex-col bg-slate-900 text-slate-300 transition-transform lg:translate-x-0"
      :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full'"
    >
      <div class="flex h-16 items-center gap-2 px-5">
        <div class="grid size-8 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 font-bold text-white">
          IX
        </div>
        <div class="leading-tight">
          <div class="text-sm font-semibold text-white">InsightX</div>
          <div class="text-[10px] tracking-widest text-slate-400">AI 跨境产品洞察</div>
        </div>
      </div>

      <nav class="mt-2 flex-1 space-y-1 px-3">
        <button
          v-for="item in navItems"
          :key="item.path"
          class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors"
          :class="route.path === item.path ? 'bg-indigo-600 text-white' : 'hover:bg-slate-800 hover:text-white'"
          @click="go(item.path)"
        >
          <svg class="size-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" :d="ICONS[item.icon]" />
          </svg>
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <div class="border-t border-slate-800 p-4 text-xs text-slate-500">
        <div class="mb-2 flex items-center gap-2">
          <div class="grid size-6 place-items-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 text-[10px] font-bold text-white">
            {{ userInitial }}
          </div>
          <span class="font-medium text-slate-400">{{ auth.email || auth.displayName }}</span>
        </div>
        <div class="mb-1 font-medium text-slate-400">Mock 数据模式</div>
        <p>后端未就绪，当前展示内存模拟数据。<br />联调时切换 <code class="text-indigo-400">VITE_USE_MOCK=false</code>。</p>
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="lg:pl-60">
      <!-- 顶栏 -->
      <header class="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-6">
        <div class="flex items-center gap-3">
          <button class="rounded-lg p-2 hover:bg-slate-100 lg:hidden" aria-label="打开导航" @click="sidebarOpen = true">
            <svg class="size-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
          <h1 class="text-base font-semibold sm:text-lg">{{ pageTitle }}</h1>
        </div>

        <div class="flex items-center gap-2">
          <button
            class="relative rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-800"
            title="风控告警"
            @click="go('/financial')"
          >
            <svg class="size-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" :d="ICONS.bell" />
            </svg>
            <span class="absolute right-1.5 top-1.5 size-2 rounded-full bg-rose-500" />
          </button>
          <button
            class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:opacity-60"
            :disabled="creating || tasksStore.flowActive"
            @click="startNewTask"
          >
            <svg class="size-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" :d="ICONS.plus" />
            </svg>
            <span class="hidden sm:inline">新诊断任务</span>
            <span class="sm:hidden">新任务</span>
          </button>

          <!-- 用户菜单 -->
          <div class="relative">
            <button
              class="flex items-center gap-2 rounded-lg p-1 pr-2 hover:bg-slate-100"
              :title="auth.email"
              aria-label="用户菜单"
              @click="toggleUserMenu"
            >
              <div class="grid size-8 place-items-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 text-sm font-bold text-white">
                {{ userInitial }}
              </div>
              <svg class="size-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
              </svg>
            </button>

            <Transition name="fade-up">
              <div
                v-if="userMenuOpen"
                class="absolute right-0 top-12 z-50 w-52 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg"
              >
                <div class="border-b border-slate-100 px-4 py-3">
                  <div class="text-sm font-semibold text-slate-800">{{ auth.email || auth.displayName }}</div>
                  <div class="mt-0.5 text-xs text-slate-400">InsightX 控制台 · Mock 登录</div>
                </div>
                <button
                  class="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-rose-600 hover:bg-rose-50"
                  @click="logout"
                >
                  <svg class="size-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
                  </svg>
                  退出登录
                </button>
              </div>
            </Transition>
          </div>
        </div>
      </header>

      <!-- 内容区 -->
      <main class="p-4 sm:p-6">
        <slot />
      </main>
    </div>

    <!-- 任务流抽屉 -->
    <Transition name="slide">
      <div
        v-if="tasksStore.flowSteps.length"
        class="fixed inset-y-0 right-0 z-40 flex w-80 flex-col border-l border-slate-200 bg-white shadow-xl"
      >
        <div class="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <div>
            <div class="text-sm font-semibold">诊断任务执行流</div>
            <div class="text-xs text-slate-500" :class="tasksStore.flowActive ? 'text-indigo-600' : 'text-emerald-600'">
              {{ tasksStore.flowActive ? '执行中…' : '已完成' }}
            </div>
          </div>
          <button class="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100" @click="tasksStore.flowSteps = []">
            <svg class="size-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" :d="ICONS.x" />
            </svg>
          </button>
        </div>

        <div class="flex-1 space-y-4 overflow-y-auto p-4">
          <div v-for="(s, i) in tasksStore.flowSteps" :key="i" class="relative pl-6">
            <div class="absolute left-1.5 top-1 size-3 rounded-full border-2 border-white bg-indigo-500 ring-2 ring-indigo-200" />
            <div v-if="i < tasksStore.flowSteps.length - 1" class="absolute bottom-0 left-[7px] top-5 w-px bg-slate-200" />
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-slate-700">{{ s.label }}</span>
              <span class="text-xs text-slate-400">{{ s.time }}</span>
            </div>
            <div class="mt-1 text-xs text-slate-500">{{ s.message }}</div>
            <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
              <div
                class="h-full rounded-full bg-indigo-500 transition-all duration-500"
                :style="{ width: `${s.progress}%` }"
              />
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}
</style>
