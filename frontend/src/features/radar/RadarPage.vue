<script setup lang="ts">
import { Globe, Inbox, TrendingUp } from '@lucide/vue'
import EmptyState from '@/components/EmptyState.vue'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

/** 竞品时序监控（PRD 信息架构 2）。P0 最小形态：任务批次/单 ASIN 状态；走势与跨平台为 P2。 */
</script>

<template>
  <div class="mx-auto w-full max-w-[1440px] space-y-6 p-4 lg:p-6">
    <div class="animate-enter">
      <h1 class="text-2xl font-semibold tracking-tight">竞品时序监控</h1>
      <p class="mt-1 text-sm text-muted-foreground">
        竞品列表、批次任务状态与异动监控；批次保留每个 ASIN 的独立状态与失败原因。
      </p>
    </div>

    <Tabs default-value="batches" class="animate-enter" :style="{ animationDelay: '60ms' }">
      <TabsList>
        <TabsTrigger value="batches">任务批次</TabsTrigger>
        <TabsTrigger value="bsr" disabled>
          BSR 走势
        </TabsTrigger>
        <TabsTrigger value="cross" disabled>
          跨平台矩阵
        </TabsTrigger>
      </TabsList>

      <TabsContent value="batches" class="animate-in fade-in duration-200">
        <Card>
          <CardHeader>
            <CardTitle class="text-base font-semibold">任务批次</CardTitle>
            <CardDescription>每批次 1-10 个 ASIN，独立状态不以「完成」掩盖部分失败。</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>任务 ID</TableHead>
                  <TableHead>ASIN 数</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>实际样本量</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead>失败原因</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell colspan="6" class="p-0">
                    <EmptyState :icon="Inbox" title="暂无任务批次" description="提交诊断任务后在此跟踪状态" />
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="bsr" class="animate-in fade-in duration-200">
        <EmptyState
          :icon="TrendingUp"
          title="暂未开放"
          description="BSR 与价格/Buy Box 波动监控暂未开放"
        />
      </TabsContent>
      <TabsContent value="cross" class="animate-in fade-in duration-200">
        <EmptyState
          :icon="Globe"
          title="暂未开放"
          description="TikTok/Temu 跨平台 SKU 映射矩阵暂未开放"
        />
      </TabsContent>
    </Tabs>
  </div>
</template>
