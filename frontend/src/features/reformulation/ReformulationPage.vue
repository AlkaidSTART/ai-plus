<script setup lang="ts">
import { ref } from 'vue'
import { Download, Package, Wrench } from '@lucide/vue'
import EmptyState from '@/components/EmptyState.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'

/**
 * 工厂级双栏改款决策（PRD 5.3）。
 * 左栏产品本体 / 右栏包装履约；每条建议可打开证据链抽屉。
 * 工程数值缺失时展示「未评估」，不让模型补造。
 */
const evidenceOpen = ref(false)
</script>

<template>
  <div class="mx-auto w-full max-w-[1440px] space-y-6 p-4 lg:p-6">
    <div class="flex animate-enter items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">改款决策</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          面向工程与供应链的双栏落地清单；每条建议 100% 绑定原始评论证据。
        </p>
      </div>
      <Button variant="outline" disabled title="工程任务书导出为后续阶段能力">
        <Download />
        导出工程任务书
      </Button>
    </div>

    <div class="grid animate-enter grid-cols-1 gap-6 xl:grid-cols-2" :style="{ animationDelay: '60ms' }">
      <Card>
        <CardHeader>
          <div class="flex items-center justify-between">
            <CardTitle class="flex items-center gap-2 text-base font-semibold">
              <Wrench class="size-4" />
              产品物理本体优化
            </CardTitle>
            <Badge variant="secondary" class="tabular-nums">0</Badge>
          </div>
          <CardDescription>材质、结构、模具公差方向。</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            :icon="Wrench"
            title="暂无本体优化建议"
            description="无证据的结论不作为有效建议"
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div class="flex items-center justify-between">
            <CardTitle class="flex items-center gap-2 text-base font-semibold">
              <Package class="size-4" />
              包装与履约优化
            </CardTitle>
            <Badge variant="secondary" class="tabular-nums">0</Badge>
          </div>
          <CardDescription>包材抗震、尺寸降阶、组装说明方向。</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            :icon="Package"
            title="暂无包装履约建议"
            description="无证据的结论不作为有效建议"
          />
        </CardContent>
      </Card>
    </div>

    <p class="animate-enter text-xs text-muted-foreground" :style="{ animationDelay: '120ms' }">
      开模费用、改模周期、运费节省等工程数值仅在输入及评估依据齐全时展示，缺失时标记「未评估」。
    </p>

    <Sheet v-model:open="evidenceOpen">
      <SheetContent class="sm:max-w-xl">
        <SheetHeader>
          <SheetTitle>证据链</SheetTitle>
          <SheetDescription>
            支撑该建议的原始评论证据（Based on N Reviews）；支持文本反查，图片证据暂未开放。
          </SheetDescription>
        </SheetHeader>
        <EmptyState
          title="暂无证据"
          description="选择一条建议后，此处展示其引用的原始评论列表"
        />
      </SheetContent>
    </Sheet>
  </div>
</template>
