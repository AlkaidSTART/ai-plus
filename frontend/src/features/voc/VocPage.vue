<script setup lang="ts">
import { computed } from 'vue'
import { ImageOff, ListTree, MessageSquareQuote } from '@lucide/vue'
import EmptyState from '@/components/EmptyState.vue'
import VChart from '@/components/VChart.vue'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { useUiStore } from '@/stores/ui'
import { useTaskDetail, useTaskEvidence, useTaskList, useTaskReport } from '@/composables/useTasks'

/** 多模态评论洞察（PRD 5.2）。实拍画廊为 P1 能力，仅占位说明。 */
const ui = useUiStore()
const { data: taskPage } = useTaskList({ limit: 1 })
const latestTaskId = computed(() => taskPage.value?.items[0]?.task_id ?? null)
const { data: latestDetail } = useTaskDetail(latestTaskId)
const firstItemId = computed(() => latestDetail.value?.items[0]?.item_id ?? null)
const { data: report } = useTaskReport(latestTaskId, firstItemId)
const { data: evidencePage } = useTaskEvidence(latestTaskId, firstItemId)

const barOption = computed(() => {
  if (!report.value?.pain_points?.length) return null
  const labels = report.value.pain_points.map((p) => p.label)
  const freqs = report.value.pain_points.map((p) => p.actual_frequency ?? 0)
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: labels, axisLabel: { interval: 0, rotate: 15 } },
    yAxis: { type: 'value', name: '频次' },
    series: [{ type: 'bar', data: freqs, itemStyle: { color: '#3b82f6' } }],
  }
})

const radarOption = computed(() => {
  if (!report.value?.pain_points?.length) return null
  const indicator = report.value.pain_points.map((p) => ({
    name: p.label,
    max: 5,
  }))
  const values = report.value.pain_points.map((p) => p.severity_score ?? 1)
  return {
    tooltip: {},
    radar: { indicator },
    series: [
      {
        type: 'radar',
        data: [{ value: values, name: '严重度评分 (1-5)' }],
        areaStyle: { opacity: 0.2 },
      },
    ],
  }
})
</script>

<template>
  <div class="mx-auto w-full max-w-[1440px] space-y-6 p-4 lg:p-6">
    <div class="animate-enter">
      <h1 class="text-2xl font-semibold tracking-tight">评论洞察</h1>
      <p class="mt-1 text-sm text-muted-foreground">
        从多语言评论中聚类的高频痛点；最多展示 5 类有证据痛点，不足不补齐。
      </p>
    </div>

    <div class="flex animate-enter flex-wrap items-center gap-4" :style="{ animationDelay: '60ms' }">
      <div class="flex items-center gap-2">
        <Label class="text-sm text-muted-foreground">语言</Label>
        <Select v-model="ui.vocLanguage">
          <SelectTrigger class="w-32"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部语言</SelectItem>
            <SelectItem value="zh">中文</SelectItem>
            <SelectItem value="en">英语</SelectItem>
            <SelectItem value="de">德语</SelectItem>
            <SelectItem value="ja">日语</SelectItem>
            <SelectItem value="es">西语</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div class="flex items-center gap-2">
        <Label class="text-sm text-muted-foreground">星级</Label>
        <ToggleGroup v-model="ui.vocStars" type="multiple" variant="outline" size="sm">
          <ToggleGroupItem value="1">1 星</ToggleGroupItem>
          <ToggleGroupItem value="2">2 星</ToggleGroupItem>
          <ToggleGroupItem value="3">3 星</ToggleGroupItem>
        </ToggleGroup>
      </div>
    </div>

    <div class="grid gap-6 xl:grid-cols-5">
      <Card class="animate-enter xl:col-span-2" :style="{ animationDelay: '120ms' }">
        <CardHeader>
          <CardTitle class="text-base font-semibold">痛点聚类排行</CardTitle>
          <CardDescription>按严重度与频次排序，低支持结果将明确标识。</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            v-if="!report?.pain_points?.length"
            :icon="ListTree"
            title="暂无痛点聚类"
            description="完成诊断任务后展示有证据的痛点排行"
          />
          <div v-else class="space-y-3">
            <div
              v-for="(p, idx) in report.pain_points"
              :key="p.pain_point_id"
              class="rounded-lg border p-3 text-sm space-y-1 bg-card hover:border-primary/50 transition-colors"
            >
              <div class="flex items-center justify-between">
                <span class="font-medium text-sm flex items-center gap-2">
                  <span class="size-5 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-bold">
                    {{ idx + 1 }}
                  </span>
                  {{ p.label }}
                </span>
                <span
                  class="text-xs px-2 py-0.5 rounded-full font-medium"
                  :class="p.severity_level === 'CRITICAL' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'"
                >
                  {{ p.severity_level }} ({{ p.severity_score }}分)
                </span>
              </div>
              <p class="text-xs text-muted-foreground">{{ p.summary }}</p>
              <div class="text-[11px] text-muted-foreground flex justify-between pt-1 border-t mt-2">
                <span>频次：{{ p.actual_frequency }} 次</span>
                <span>依据证据数：{{ p.evidence_refs.length }} 条</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card class="animate-enter xl:col-span-3" :style="{ animationDelay: '180ms' }">
        <CardHeader>
          <CardTitle class="text-base font-semibold">痛点分布</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs default-value="bar">
            <TabsList>
              <TabsTrigger value="bar">柱状分布</TabsTrigger>
              <TabsTrigger value="radar">雷达对比</TabsTrigger>
              <TabsTrigger value="gallery" disabled>
                实拍画廊
              </TabsTrigger>
            </TabsList>
            <TabsContent value="bar" class="animate-in fade-in duration-200"><VChart :option="barOption" /></TabsContent>
            <TabsContent value="radar" class="animate-in fade-in duration-200"><VChart :option="radarOption" /></TabsContent>
            <TabsContent value="gallery" class="animate-in fade-in duration-200">
              <EmptyState
                :icon="ImageOff"
                title="暂未开放"
                description="实拍图缺陷取证能力暂未开放，当前不展示图片证据"
              />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>

    <Card class="animate-enter" :style="{ animationDelay: '240ms' }">
      <CardHeader>
        <CardTitle class="text-base font-semibold">评论原声</CardTitle>
        <CardDescription>支持多语言原声与翻译对照（当前语言：{{ ui.vocLanguage }}）。</CardDescription>
      </CardHeader>
      <CardContent>
        <EmptyState
          v-if="!evidencePage?.items?.length"
          :icon="MessageSquareQuote"
          title="暂无评论样本"
          description="任务采集的真实评论将在此可回查"
        />
        <div v-else class="space-y-3">
          <div
            v-for="ev in evidencePage.items"
            :key="ev.evidence_id"
            class="rounded-lg border p-4 space-y-2 bg-card text-sm"
          >
            <div class="flex items-center justify-between text-xs text-muted-foreground">
              <span class="font-medium text-foreground">买家真实评论 · {{ ev.source_ref }}</span>
              <span>⭐ {{ ev.metadata?.rating }} / 5 · {{ ev.published_at ? new Date(ev.published_at).toLocaleDateString() : '' }}</span>
            </div>
            <p class="italic text-foreground/90 bg-muted/30 p-2.5 rounded border-l-2 border-primary/60 font-serif">
              “{{ ev.excerpt }}”
            </p>
            <div class="text-[11px] text-muted-foreground flex justify-between">
              <span>来源：{{ ev.provenance?.source }} ({{ ev.provenance?.capture }})</span>
              <a :href="ev.source_url ?? undefined" target="_blank" class="text-primary hover:underline">查看对应商品</a>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
