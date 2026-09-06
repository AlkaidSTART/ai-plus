<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AuthShell from '@/components/auth/AuthShell.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const form = reactive({ email: '', password: '', confirm: '' })
const error = ref('')
const submitting = ref(false)

/** 注册成功后回跳：仅允许站内功能页 */
function redirectTarget() {
  const r = route.query.redirect
  if (typeof r === 'string' && r.startsWith('/') && r !== '/login' && r !== '/register') return r
  return '/'
}

async function onSubmit() {
  if (submitting.value) return
  error.value = ''
  if (form.password !== form.confirm) {
    error.value = '两次输入的密码不一致'
    return
  }
  submitting.value = true
  // 模拟请求延迟，让提交动画可见
  await new Promise((resolve) => setTimeout(resolve, 450))
  try {
    const res = auth.register(form.email, form.password)
    if (!res.ok) {
      error.value = res.message
      return
    }
    // 注册成功自动登录并进入控制台
    auth.login(form.email, form.password)
    router.replace(redirectTarget())
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthShell title="注册账号" subtitle="创建一个演示账号，注册后自动登录进入控制台">
    <form
      class="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-2xl shadow-black/40 backdrop-blur"
      @submit.prevent="onSubmit"
    >
      <h2 class="text-base font-semibold text-white">创建账号</h2>
      <p class="mt-1 text-xs text-slate-400">
        已有账号？<RouterLink to="/login" class="text-indigo-400 transition-colors hover:text-indigo-300">
          返回登录
        </RouterLink>
      </p>

      <label class="mt-5 block text-sm font-medium text-slate-300" for="reg-email">邮箱</label>
      <input
        id="reg-email"
        v-model="form.email"
        type="email"
        autocomplete="email"
        placeholder="you@example.com"
        class="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-800 px-3.5 py-2.5 text-sm text-white placeholder-slate-500 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30"
      />

      <label class="mt-4 block text-sm font-medium text-slate-300" for="reg-password">密码</label>
      <input
        id="reg-password"
        v-model="form.password"
        type="password"
        autocomplete="new-password"
        placeholder="至少 6 位"
        class="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-800 px-3.5 py-2.5 text-sm text-white placeholder-slate-500 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30"
      />

      <label class="mt-4 block text-sm font-medium text-slate-300" for="reg-confirm">确认密码</label>
      <input
        id="reg-confirm"
        v-model="form.confirm"
        type="password"
        autocomplete="new-password"
        placeholder="再次输入密码"
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
        <span v-if="submitting">注册中…</span>
        <span v-else>注册并进入控制台</span>
      </button>

      <div class="mt-4 flex items-center gap-2 text-[11px] text-slate-500">
        <svg class="size-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"
          />
        </svg>
        演示环境：账号仅存浏览器本地（localStorage），请勿使用真实密码
      </div>
    </form>

    <template #footer>
      <RouterLink to="/login" class="text-xs text-slate-600 transition-colors hover:text-slate-400">
        ← 返回登录
      </RouterLink>
    </template>
  </AuthShell>
</template>
