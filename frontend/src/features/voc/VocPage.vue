<script setup lang="ts">
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

/** 多模态评论洞察（PRD 5.2）。实拍画廊为 P1 能力，仅占位说明。 */
const ui = useUiStore()
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
            :icon="ListTree"
            title="暂无痛点聚类"
            description="完成诊断任务后展示有证据的痛点排行"
          />
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
            <TabsContent value="bar" class="animate-in fade-in duration-200"><VChart :option="null" /></TabsContent>
            <TabsContent value="radar" class="animate-in fade-in duration-200"><VChart :option="null" /></TabsContent>
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
          :icon="MessageSquareQuote"
          title="暂无评论样本"
          description="任务采集的真实评论将在此可回查"
        />
      </CardContent>
    </Card>
  </div>
</template>
