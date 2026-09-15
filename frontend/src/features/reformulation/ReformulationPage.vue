<script setup lang="ts">
import { computed, ref } from 'vue'
import { Download, ExternalLink, Package, Wrench } from '@lucide/vue'
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
import type { ReportProposal } from '@/api/client'
import { useTaskDetail, useTaskEvidence, useTaskList, useTaskReport } from '@/composables/useTasks'

/**
 * 工厂级双栏改款决策（PRD 5.3）。
 * 左栏产品本体 / 右栏包装履约；每条建议可打开证据链抽屉。
 * 工程数值缺失时展示「未评估」，不让模型补造。
 */
const { data: taskPage } = useTaskList({ limit: 1 })
const latestTaskId = computed(() => taskPage.value?.items[0]?.task_id ?? null)
const { data: latestDetail } = useTaskDetail(latestTaskId)
const firstItemId = computed(() => latestDetail.value?.items[0]?.item_id ?? null)
const { data: report } = useTaskReport(latestTaskId, firstItemId)
const { data: evidencePage } = useTaskEvidence(latestTaskId, firstItemId)

const productProposals = computed(
  () => report.value?.proposals?.filter((p) => p.column === 'PRODUCT_OPTIMIZATION') ?? [],
)
const packagingProposals = computed(
  () =>
    report.value?.proposals?.filter((p) => p.column === 'PACKAGING_FULFILLMENT_OPTIMIZATION') ?? [],
)

const selectedProposal = ref<ReportProposal | null>(null)
const evidenceOpen = ref(false)

function openEvidence(prop: ReportProposal) {
  selectedProposal.value = prop
  evidenceOpen.value = true
}

const activeEvidences = computed(() => {
  if (!selectedProposal.value || !evidencePage.value?.items) return []
  const refs = new Set(selectedProposal.value.evidence_refs)
  return evidencePage.value.items.filter((ev) => refs.has(ev.source_ref))
})
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
            <Badge variant="secondary" class="tabular-nums">{{ productProposals.length }}</Badge>
          </div>
          <CardDescription>材质、结构、模具公差方向。</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            v-if="!productProposals.length"
            :icon="Wrench"
            title="暂无本体优化建议"
            description="无证据的结论不作为有效建议"
          />
          <div v-else class="space-y-3">
            <div
              v-for="prop in productProposals"
              :key="prop.proposal_id"
              class="rounded-lg border p-4 space-y-2 bg-card hover:border-primary/50 transition-colors"
            >
              <div class="flex items-start justify-between gap-2">
                <h4 class="font-medium text-sm text-foreground">{{ prop.title }}</h4>
                <Button variant="ghost" size="xs" class="text-xs shrink-0 text-primary" @click="openEvidence(prop)">
                  查看证据 ({{ prop.evidence_refs.length }})
                </Button>
              </div>
              <p class="text-xs text-muted-foreground">{{ prop.change_description }}</p>
              <div class="text-[11px] text-muted-foreground flex gap-3 pt-1 border-t">
                <span>关联痛点：{{ prop.pain_point_ids.join(', ') }}</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div class="flex items-center justify-between">
            <CardTitle class="flex items-center gap-2 text-base font-semibold">
              <Package class="size-4" />
              包装与履约优化
            </CardTitle>
            <Badge variant="secondary" class="tabular-nums">{{ packagingProposals.length }}</Badge>
          </div>
          <CardDescription>包材抗震、尺寸降阶、组装说明方向。</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            v-if="!packagingProposals.length"
            :icon="Package"
            title="暂无包装履约建议"
            description="无证据的结论不作为有效建议"
          />
          <div v-else class="space-y-3">
            <div
              v-for="prop in packagingProposals"
              :key="prop.proposal_id"
              class="rounded-lg border p-4 space-y-2 bg-card hover:border-primary/50 transition-colors"
            >
              <div class="flex items-start justify-between gap-2">
                <h4 class="font-medium text-sm text-foreground">{{ prop.title }}</h4>
                <Button variant="ghost" size="xs" class="text-xs shrink-0 text-primary" @click="openEvidence(prop)">
                  查看证据 ({{ prop.evidence_refs.length }})
                </Button>
              </div>
              <p class="text-xs text-muted-foreground">{{ prop.change_description }}</p>
              <div class="text-[11px] text-muted-foreground flex gap-3 pt-1 border-t">
                <span>关联痛点：{{ prop.pain_point_ids.join(', ') }}</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <p class="animate-enter text-xs text-muted-foreground" :style="{ animationDelay: '120ms' }">
      开模费用、改模周期、运费节省等工程数值仅在输入及评估依据齐全时展示，缺失时标记「未评估」。
    </p>

    <Sheet v-model:open="evidenceOpen">
      <SheetContent class="sm:max-w-xl">
        <SheetHeader>
          <SheetTitle>证据链溯源</SheetTitle>
          <SheetDescription>
            支撑「{{ selectedProposal?.title }}」的原始买家评论（100% 来源真实文本）。
          </SheetDescription>
        </SheetHeader>
        <div class="mt-4 space-y-3">
          <EmptyState
            v-if="!activeEvidences.length"
            title="暂无直接证据"
            description="该建议引用证据正在整理中"
          />
          <div
            v-for="ev in activeEvidences"
            :key="ev.evidence_id"
            class="rounded-lg border p-4 space-y-2 bg-muted/20 text-sm"
          >
            <div class="flex items-center justify-between text-xs text-muted-foreground">
              <span class="font-medium text-foreground">真实评价 · {{ ev.source_ref }}</span>
              <span>⭐ {{ ev.metadata?.rating }} / 5</span>
            </div>
            <p class="italic text-foreground/90 bg-background p-2.5 rounded border font-serif">
              “{{ ev.excerpt }}”
            </p>
            <div class="text-[11px] text-muted-foreground flex justify-between">
              <span>{{ ev.provenance?.source }}</span>
              <a :href="ev.source_url ?? undefined" target="_blank" class="text-primary hover:underline flex items-center gap-1">
                商品详情 <ExternalLink class="size-3" />
              </a>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  </div>
</template>
