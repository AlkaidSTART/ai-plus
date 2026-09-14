<script setup lang="ts">
import { Inbox, Sparkles } from '@lucide/vue'
import EmptyState from '@/components/EmptyState.vue'
import KpiCard from '@/components/KpiCard.vue'
import SseTimeline from '@/components/SseTimeline.vue'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { useUiStore } from '@/stores/ui'

/**
 * 战略决策大盘（PRD 5.1）。
 * 后端就绪前全部区块为空态；KPI 为采样口径，财务熔断 P0 恒「未评估」。
 */
const ui = useUiStore()
</script>

<template>
  <div class="mx-auto w-full max-w-[1440px] space-y-6 p-4 lg:p-6">
    <div class="flex animate-enter items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">决策大盘</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          聚合监控品类的全局体检状态；指标均为采样口径，时间窗以任务为准。
        </p>
      </div>
      <Button size="sm" @click="ui.newTaskDialogOpen = true">新建诊断任务</Button>
    </div>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiCard label="本批监控竞品" :value="null" note="提交诊断任务后统计" :delay-ms="0" />
      <KpiCard label="实际样本量" :value="null" note="为实际采集样本，非商品总体" :delay-ms="60" />
      <KpiCard label="有证据痛点数" :value="null" note="最多 5 类，不足不补齐" :delay-ms="120" />
      <KpiCard label="财务熔断" not-evaluated note="当前不执行财务否决" :delay-ms="180" />
    </div>

    <div class="grid gap-6 xl:grid-cols-3">
      <Card class="animate-enter xl:col-span-2" :style="{ animationDelay: '180ms' }">
        <CardHeader>
          <CardTitle class="text-base font-semibold">Agent 执行流</CardTitle>
          <CardDescription>
            SSE 展示真实节点与每个 ASIN 状态，区分跳过/无数据/失败/取消；断线后按游标回放。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <SseTimeline :nodes="[]" />
        </CardContent>
      </Card>

      <Card class="animate-enter" :style="{ animationDelay: '240ms' }">
        <CardHeader>
          <CardTitle class="text-base font-semibold">高潜改款项目推荐</CardTitle>
          <CardDescription>仅展示有支撑数据的结果，不足 Top 3 不补齐。</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            :icon="Sparkles"
            title="暂无推荐"
            description="完成诊断任务并获得有证据的报告后，此处展示推荐项目"
          />
        </CardContent>
      </Card>
    </div>

    <Card class="animate-enter" :style="{ animationDelay: '300ms' }">
      <CardHeader>
        <CardTitle class="text-base font-semibold">最近任务</CardTitle>
        <CardDescription>批次任务与单 ASIN 工作单元状态（含部分失败原因）。</CardDescription>
      </CardHeader>
      <CardContent>
        <EmptyState
          :icon="Inbox"
          title="暂无任务"
          description="点击右上角「新建诊断任务」提交 1-10 个 Amazon US ASIN"
        />
      </CardContent>
    </Card>
  </div>
</template>
