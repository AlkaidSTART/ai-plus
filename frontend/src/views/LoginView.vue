<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AuthShell from '@/components/auth/AuthShell.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const form = reactive({ email: '', password: '' })
const error = ref('')
const submitting = ref(false)

/** 登录成功后回跳：仅允许站内功能页，避免回跳回登录 / 注册页 */
function redirectTarget() {
  const r = route.query.redirect
  if (typeof r === 'string' && r.startsWith('/') && r !== '/login' && r !== '/register') return r
  return '/'
}

async function onSubmit() {
  if (submitting.value) return
  error.value = ''
  submitting.value = true
  // 模拟请求延迟，让提交动画可见
  await new Promise((resolve) => setTimeout(resolve, 450))
  try {
    const res = auth.login(form.email, form.password)
    if (!res.ok) {
      error.value = res.message
      return
    }
    router.replace(redirectTarget())
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthShell title="登录控制台" subtitle="Mock 演示环境 · 使用注册的邮箱与密码登录">
    <form
      class="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-2xl shadow-black/40 backdrop-blur"
      @submit.prevent="onSubmit"
    >
      <h2 class="text-base font-semibold text-white">登录控制台</h2>
      <p class="mt-1 text-xs text-slate-400">
        首次使用请先
        <RouterLink to="/register" class="text-indigo-400 transition-colors hover:text-indigo-300">
          注册账号
        </RouterLink>
      </p>

      <label class="mt-5 block text-sm font-medium text-slate-300" for="email">邮箱</label>
      <input
        id="email"
        v-model="form.email"
        type="email"
        autocomplete="email"
        placeholder="you@example.com"
        class="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-800 px-3.5 py-2.5 text-sm text-white placeholder-slate-500 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30"
      />

      <label class="mt-4 block text-sm font-medium text-slate-300" for="password">密码</label>
      <input
        id="password"
        v-model="form.password"
        type="password"
        autocomplete="current-password"
        placeholder="请输入密码"
        class="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-800 px-3.5 py-2.5 text-sm text-white placeholder-slate-500 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30"
      />

      <Transition name="shake">
        <p v-if="error" class="error-banner mt-3">{{ error }}</p>
      </Transition>

      <button
        type="submit"
        :disabled="submitting"
        class="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-cyan-500 to-indigo-600 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/25 transition hover:opacity-90 disabled:opacity-70"
      >
        <svg
          v-if="submitting"
          class="size-4 animate-spin"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="2"
          stroke="currentColor"
        >
          <path stroke-linecap="round" d="M21 12a9 9 0 1 1-6.219-8.56" />
        </svg>
        <span v-if="submitting">登录中…</span>
        <span v-else>进入控制台</span>
      </button>

      <div class="mt-4 flex items-center gap-2 text-[11px] text-slate-500">
        <svg class="size-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
          />
        </svg>
        演示环境凭据仅存浏览器本地（localStorage），请勿使用真实密码
      </div>
    </form>

    <template #footer>
      <p class="text-xs text-slate-600">
        没有账号？
        <RouterLink to="/register" class="font-medium text-slate-400 transition-colors hover:text-slate-200">
          立即注册
        </RouterLink>
      </p>
    </template>
  </AuthShell>
</template>
