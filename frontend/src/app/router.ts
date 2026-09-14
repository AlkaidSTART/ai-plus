import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

/**
 * 路由 = PRD 第四节信息架构的 5 个主导航模块。
 */
const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/dashboard' },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/features/dashboard/DashboardPage.vue'),
    meta: { title: '决策大盘' },
  },
  {
    path: '/radar',
    name: 'radar',
    component: () => import('@/features/radar/RadarPage.vue'),
    meta: { title: '竞品雷达' },
  },
  {
    path: '/voc',
    name: 'voc',
    component: () => import('@/features/voc/VocPage.vue'),
    meta: { title: '评论洞察' },
  },
  {
    path: '/reformulation',
    name: 'reformulation',
    component: () => import('@/features/reformulation/ReformulationPage.vue'),
    meta: { title: '改款决策' },
  },
  {
    path: '/financial',
    name: 'financial',
    component: () => import('@/features/financial/FinancialPage.vue'),
    meta: { title: '财务风控' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/features/not-found/NotFoundPage.vue'),
    meta: { title: '页面不存在' },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
