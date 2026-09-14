<script setup lang="ts">
import { ShieldAlert } from '@lucide/vue'
import EmptyState from '@/components/EmptyState.vue'
import FinancialStateBadge from '@/components/FinancialStateBadge.vue'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

/**
 * 逆向财务与风控熔断（PRD 5.4，P1）。
 * P0 不执行财务否决：本页为阶段说明页，裁决恒为 NOT_EVALUATED。
 */
</script>

<template>
  <div class="mx-auto w-full max-w-[1440px] space-y-6 p-4 lg:p-6">
    <div class="animate-enter">
      <h1 class="text-2xl font-semibold tracking-tight">财务风控</h1>
      <p class="mt-1 text-sm text-muted-foreground">
        把控商业合理性，防止盲目开模与高危立项。
      </p>
    </div>

    <Alert class="animate-enter" :style="{ animationDelay: '60ms' }">
      <ShieldAlert />
      <AlertTitle class="flex items-center gap-2">
        当前状态
        <FinancialStateBadge state="NOT_EVALUATED" />
      </AlertTitle>
      <AlertDescription>
        当前不执行财务否决：未运行财务步骤或缺失开模成本、MOQ、毛利率等必要输入时，
        裁决恒为「未评估」，不等于通过或 0 收益。
      </AlertDescription>
    </Alert>

    <Card class="animate-enter" :style="{ animationDelay: '120ms' }">
      <CardHeader>
        <CardTitle class="text-base font-semibold">暂未开放</CardTitle>
        <CardDescription>
          开放后将提供：财务参数调节（开模预算/打样成本/MOQ/预期售价/海运单价）、
          确定性公式计算的盈亏平衡与敏感度曲线、可复算理由的熔断决议（PASSED / VETOED）。
          裁决由版本化确定性公式给出，不由模型口头说明改判。
        </CardDescription>
      </CardHeader>
      <CardContent>
        <EmptyState
          :icon="ShieldAlert"
          title="财务测算器未开放"
          description="当前版本支持文本诊断闭环，财务风控能力暂未开放"
        />
      </CardContent>
    </Card>
  </div>
</template>
