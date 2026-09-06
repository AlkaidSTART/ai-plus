import { createRouter, createWebHistory, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// 部署形态：独立部署（base '/'）用 history；GitHub Pages 子路径部署（base '/ai-plus/'）用 hash，避免刷新 404
const base = import.meta.env.VITE_BASE ?? '/'
const history = base === '/' ? createWebHistory(base) : createWebHashHistory(base)

const router = createRouter({
  history,
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { title: '登录', public: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { title: '注册', public: true },
    },
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { title: '战略决策大盘' },
    },
    {
      path: '/products',
      name: 'products',
      component: () => import('@/views/ProductsView.vue'),
      meta: { title: '竞品时序监控' },
    },
    {
      path: '/voc',
      name: 'voc',
      component: () => import('@/views/VocView.vue'),
      meta: { title: '多模态评论洞察' },
    },
    {
      path: '/reformulation',
      name: 'reformulation',
      component: () => import('@/views/ReformulationView.vue'),
      meta: { title: '工厂级改款决策' },
    },
    {
      path: '/financial',
      name: 'financial',
      component: () => import('@/views/FinancialView.vue'),
      meta: { title: '逆向财务与风控熔断' },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

/** 登录态守卫：未登录访问功能页 → /login；已登录访问 /login → 大盘 */
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if ((to.name === 'login' || to.name === 'register') && auth.isAuthenticated) {
    return { name: 'dashboard' }
  }
})

router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  document.title = title ? `${title} · InsightX` : 'InsightX'
})

export default router
