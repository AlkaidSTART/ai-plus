<script setup lang="ts">
/**
 * PipelineDemo —— Vue island 演示组件（由 Astro 以 client:load 挂载）
 * 模拟 InsightX 单次"竞品诊断任务"的 8 步 LangGraph 管线推进动画。
 */
import { ref } from 'vue'

interface Step {
  id: string
  label: string
  message: string
  durationMs: number
  extra?: string
}

const STEPS: Step[] = [
  { id: 'QUEUED', label: '任务入队', message: '任务已提交，等待调度器分配', durationMs: 400 },
  { id: 'FETCHING_DATA', label: '评论采集', message: 'Playwright 抓取 Amazon 评论与买家实拍图', durationMs: 900, extra: '320 条评论' },
  { id: 'VISION_AUDIT', label: '视觉取证', message: 'Claude Vision 质检买家实拍图，定位物理缺陷', durationMs: 900, extra: '18 张实拍图' },
  { id: 'SEMANTIC_CLUSTER', label: '痛点聚类', message: 'bge-m3 向量化多语言评论并聚类', durationMs: 800, extra: '6 个核心痛点' },
  { id: 'DUAL_DECISION', label: '双栏改款', message: 'LangGraph 生成本体 / 包装双栏工程清单', durationMs: 800, extra: '5 条提案' },
  { id: 'FINANCIAL_VETO', label: '财务熔断', message: '开模成本 / MOQ / 回本周期逆向校验', durationMs: 600, extra: '1 条触发否决' },
  { id: 'EVIDENCE_TRACE', label: '证据溯源', message: '每条建议绑定原始评论与图片证据链', durationMs: 500, extra: '42 条绑定成功' },
  { id: 'COMPLETED', label: '任务完成', message: '报告已生成，可查看聚合洞察', durationMs: 300, extra: '✓' },
]

const running = ref(false)
const done = ref(false)
const currentIdx = ref(-1)
const progress = ref(0)
const message = ref('点击按钮，启动一次完整的竞品诊断管线演示')

let timers: number[] = []

function run() {
  // 清理上一次的定时器
  timers.forEach((t) => window.clearTimeout(t))
  timers = []
  running.value = true
  done.value = false
  currentIdx.value = -1
  progress.value = 0
  message.value = '正在提交任务…'

  STEPS.forEach((step, i) => {
    const t = window.setTimeout(() => {
      currentIdx.value = i
      progress.value = Math.round(((i + 1) / STEPS.length) * 100)
      message.value = `${step.label}：${step.message}${step.extra ? `（${step.extra}）` : ''}`
      if (i === STEPS.length - 1) {
        running.value = false
        done.value = true
      }
    }, STEPS.slice(0, i).reduce((acc, s) => acc + s.durationMs, 0))
    timers.push(t)
  })
}
</script>

<template>
  <div class="pipeline">
    <div class="pipeline-head">
      <span class="pipeline-badge">LangGraph Agent 管线</span>
      <span class="pipeline-status" :class="{ running }">
        <span class="dot" :class="{ 'dot-running': running }" />
        {{ running ? '任务运行中…' : done ? '任务完成' : '待机' }}
      </span>
    </div>

    <ol class="pipeline-steps">
      <li v-for="(s, i) in STEPS" :key="s.id" class="step" :class="{ active: i === currentIdx, past: i < currentIdx, pending: i > currentIdx }">
        <span class="step-dot">{{ i < currentIdx ? '✓' : i + 1 }}</span>
        <div class="step-body">
          <div class="step-row">
            <span class="step-label">{{ s.label }}</span>
            <span class="step-extra">{{ i < currentIdx ? s.extra : '' }}</span>
          </div>
          <p class="step-msg">{{ s.message }}</p>
        </div>
      </li>
    </ol>

    <div class="pipeline-progress">
      <div class="progress-track">
        <div class="progress-bar" :style="{ width: progress + '%' }" />
      </div>
      <span class="progress-text">{{ progress }}%</span>
    </div>

    <p class="pipeline-message">{{ message }}</p>

    <button class="pipeline-btn" :disabled="running" @click="run">
      {{ running ? '运行中…' : done ? '重新演示' : '运行诊断任务' }}
    </button>
  </div>
</template>

<style scoped>
.pipeline {
  font-family: ui-sans-serif, system-ui, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 20px 40px -20px rgb(2 6 23 / 0.25);
}
.pipeline-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.pipeline-badge {
  font-size: 12px;
  font-weight: 600;
  color: #0e7490;
  background: #cffafe;
  border-radius: 9999px;
  padding: 4px 12px;
}
.pipeline-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #475569;
}
.pipeline-status.running {
  color: #0369a1;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  background: #94a3b8;
}
.dot-running {
  background: #0ea5e9;
  animation: pulse 1s ease-in-out infinite;
}
@keyframes pulse {
  50% {
    opacity: 0.35;
  }
}
.pipeline-steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 4px;
}
.step {
  display: flex;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  transition: background 0.2s;
}
.step.active {
  background: #f0f9ff;
}
.step.past .step-dot {
  background: #10b981;
  color: #fff;
}
.step-dot {
  flex: none;
  width: 24px;
  height: 24px;
  border-radius: 9999px;
  background: #e2e8f0;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.step.active .step-dot {
  background: #0284c7;
  color: #fff;
}
.step-body {
  min-width: 0;
}
.step-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.step-label {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}
.step.active .step-label {
  color: #0369a1;
}
.step.pending .step-label {
  color: #94a3b8;
}
.step-extra {
  font-size: 11px;
  color: #10b981;
  background: #ecfdf5;
  border-radius: 9999px;
  padding: 2px 8px;
}
.step-msg {
  margin: 2px 0 0;
  font-size: 12px;
  color: #64748b;
}
.pipeline-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
}
.progress-track {
  flex: 1;
  height: 8px;
  border-radius: 9999px;
  background: #e2e8f0;
  overflow: hidden;
}
.progress-bar {
  height: 100%;
  border-radius: 9999px;
  background: linear-gradient(90deg, #0ea5e9, #6366f1);
  transition: width 0.4s ease;
}
.progress-text {
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
  min-width: 36px;
  text-align: right;
}
.pipeline-message {
  margin: 10px 0 14px;
  font-size: 13px;
  color: #334155;
  min-height: 20px;
}
.pipeline-btn {
  width: 100%;
  border: none;
  border-radius: 12px;
  background: linear-gradient(90deg, #0284c7, #4f46e5);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  padding: 12px 16px;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.1s;
}
.pipeline-btn:hover:not(:disabled) {
  opacity: 0.92;
}
.pipeline-btn:active:not(:disabled) {
  transform: scale(0.99);
}
.pipeline-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
