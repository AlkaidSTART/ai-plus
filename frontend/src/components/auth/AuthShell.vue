<script setup lang="ts">
withDefaults(
  defineProps<{
    /** 表单标题 */
    title: string
    /** 标题下的一行说明 */
    subtitle: string
  }>(),
  {},
)
</script>

<template>
  <div class="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950 px-4">
    <!-- 背景光晕（缓慢漂移） -->
    <div class="pointer-events-none absolute inset-0" aria-hidden="true">
      <div class="glow glow-1" />
      <div class="glow glow-2" />
    </div>

    <div class="relative w-full max-w-md">
      <!-- 返回落地页首页 -->
      <div class="auth-item absolute -top-10 left-0" style="--d: 0.02s">
        <a
          href="/"
          class="inline-flex items-center gap-1.5 text-xs text-slate-500 transition-colors hover:text-slate-300"
        >
          <svg class="size-3.5" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
          </svg>
          返回首页
        </a>
      </div>

      <!-- Logo 区（点击返回首页） -->
      <a
        href="/"
        class="auth-item mb-8 flex flex-col items-center gap-3 text-center transition-opacity hover:opacity-85"
        style="--d: 0.04s"
        title="返回首页"
      >
        <div class="grid size-12 place-items-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 text-lg font-bold text-white shadow-lg shadow-indigo-500/25">
          IX
        </div>
        <div>
          <h1 class="text-xl font-bold text-white">InsightX</h1>
          <p class="mt-1 text-sm text-slate-400">AI 跨境产品洞察 · 动态决策控制台</p>
        </div>
      </a>

      <!-- 表单卡片 -->
      <div class="auth-item" style="--d: 0.14s">
        <slot />
      </div>

      <!-- 页脚（返回 / 切换链接） -->
      <div class="auth-item mt-6 text-center" style="--d: 0.24s">
        <slot name="footer" />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 内容错落入场：依次淡入上浮 */
.auth-item {
  opacity: 0;
  animation: auth-in 0.55s cubic-bezier(0.22, 1, 0.36, 1) var(--d, 0s) forwards;
}
@keyframes auth-in {
  from {
    opacity: 0;
    transform: translateY(18px) scale(0.985);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* 背景光晕 */
.glow {
  position: absolute;
  border-radius: 9999px;
  filter: blur(3.5rem);
  will-change: transform;
}
.glow-1 {
  top: -8rem;
  left: 50%;
  width: 42rem;
  height: 24rem;
  transform: translateX(-50%);
  background: rgba(99, 102, 241, 0.22);
  animation: drift-1 16s ease-in-out infinite alternate;
}
.glow-2 {
  right: -6rem;
  bottom: -8rem;
  width: 24rem;
  height: 20rem;
  background: rgba(6, 182, 212, 0.12);
  animation: drift-2 20s ease-in-out infinite alternate;
}
@keyframes drift-1 {
  from {
    transform: translateX(-55%) translateY(0);
  }
  to {
    transform: translateX(-45%) translateY(24px);
  }
}
@keyframes drift-2 {
  from {
    transform: translate(0, 0) scale(1);
  }
  to {
    transform: translate(-32px, -26px) scale(1.08);
  }
}
</style>
