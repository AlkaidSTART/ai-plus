<script setup lang="ts">
import { AlertCircle, CheckCircle2, ExternalLink, Loader2, RotateCw } from '@lucide/vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import StatusBadge from '@/components/StatusBadge.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useRetryTask, useTaskDetail } from '@/composables/useTasks'

const props = defineProps<{
  taskId: string
}>()

const router = useRouter()
const { data: taskDetail, isLoading, error } = useTaskDetail(() => props.taskId)
const retryMutation = useRetryTask()

async function handleRetryItem(itemId: string, asin: string) {
  try {
    const key = `retry-${props.taskId}-${itemId}-${Date.now()}`
    await retryMutation.mutateAsync({
      taskId: props.taskId,
      itemIds: [itemId],
      idempotencyKey: key,
    })
    toast.success(`已提交重试：ASIN ${asin}`)
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '重试提交失败'
    toast.error(msg)
  }
}

function handleViewReport(taskId: string, itemId: string) {
  void router.push({
    path: '/voc',
    query: { taskId, itemId },
  })
}
</script>

<template>
  <div class="rounded-lg border border-border/80 bg-muted/30 p-4">
    <div class="mb-3 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <span class="text-xs font-medium uppercase tracking-wider text-muted-foreground">批次项明细 (ASIN 独立执行视图)</span>
        <Badge variant="outline" class="text-[11px] text-muted-foreground">
          {{ taskDetail?.items?.length ?? 0 }} 个 ASIN
        </Badge>
      </div>
      <span class="text-xs text-muted-foreground">独立记录各 ASIN 执行状态与失败阻断原因</span>
    </div>

    <div v-if="isLoading" class="flex items-center justify-center py-6 text-sm text-muted-foreground">
      <Loader2 class="mr-2 h-4 w-4 animate-spin" />
      加载批次子项状态中...
    </div>

    <div v-else-if="error" class="rounded-md border border-destructive/20 bg-destructive/5 p-3 text-xs text-destructive">
      加载子项失败：{{ error.message }}
    </div>

    <div v-else-if="!taskDetail?.items?.length" class="py-4 text-center text-xs text-muted-foreground">
      此任务无子项记录
    </div>

    <div v-else class="overflow-x-auto rounded-md border bg-background">
      <Table>
        <TableHeader>
          <TableRow class="bg-muted/40 text-xs">
            <TableHead class="w-36">目标 ASIN</TableHead>
            <TableHead class="w-24">单项状态</TableHead>
            <TableHead class="w-32">执行节点 / 尝试</TableHead>
            <TableHead class="w-36">有效/原始样本量</TableHead>
            <TableHead class="w-24">数据质量</TableHead>
            <TableHead>失败原因与诊断</TableHead>
            <TableHead class="w-28 text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="item in taskDetail.items" :key="item.item_id" class="text-xs">
            <!-- ASIN -->
            <TableCell class="font-mono font-medium">
              <a
                :href="`https://www.amazon.com/dp/${item.asin}`"
                target="_blank"
                rel="noreferrer"
                class="inline-flex items-center gap-1 text-primary hover:underline"
              >
                {{ item.asin }}
                <ExternalLink class="h-3 w-3 text-muted-foreground" />
              </a>
            </TableCell>

            <!-- Status -->
            <TableCell>
              <StatusBadge :status="item.status" />
            </TableCell>

            <!-- Node / Attempt -->
            <TableCell class="text-muted-foreground">
              <div>{{ item.current_node ?? (item.status === 'COMPLETED' ? '已完成' : '—') }}</div>
              <div class="text-[11px] text-muted-foreground/70">尝试次数：{{ item.attempt }}</div>
            </TableCell>

            <!-- Sample count -->
            <TableCell>
              <template v-if="item.sample_metrics">
                <span class="font-medium text-foreground">{{ item.sample_metrics.valid_review_count }}</span>
                <span class="text-muted-foreground"> / {{ item.sample_metrics.raw_review_count }} 条</span>
              </template>
              <span v-else class="text-muted-foreground">—</span>
            </TableCell>

            <!-- Data Quality -->
            <TableCell>
              <Badge
                v-if="item.data_quality === 'SUFFICIENT'"
                variant="outline"
                class="border-emerald-200 bg-emerald-50 text-emerald-700"
              >
                充分
              </Badge>
              <Badge
                v-else-if="item.data_quality === 'PARTIAL'"
                variant="outline"
                class="border-amber-200 bg-amber-50 text-amber-700"
              >
                欠佳
              </Badge>
              <Badge
                v-else-if="item.data_quality === 'NO_DATA'"
                variant="outline"
                class="border-red-200 bg-red-50 text-red-700"
              >
                无数据
              </Badge>
              <span v-else class="text-muted-foreground">—</span>
            </TableCell>

            <!-- Failure reason / Diagnostics -->
            <TableCell>
              <div v-if="item.error" class="flex items-start gap-1.5 text-destructive">
                <AlertCircle class="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <div>
                  <span class="font-medium">[{{ item.error.code }}]</span>
                  <span class="ml-1">{{ item.error.message }}</span>
                  <span v-if="item.error.retryable" class="ml-1 text-[11px] text-amber-600">(支持重试)</span>
                </div>
              </div>
              <div v-else-if="item.status === 'FAILED'" class="flex items-center gap-1.5 text-destructive">
                <AlertCircle class="h-3.5 w-3.5 shrink-0" />
                <span>任务执行异常终止</span>
              </div>
              <div v-else-if="item.status === 'COMPLETED'" class="flex items-center gap-1.5 text-emerald-600">
                <CheckCircle2 class="h-3.5 w-3.5 shrink-0" />
                <span>数据已收敛，就绪</span>
              </div>
              <div v-else class="text-muted-foreground">
                正在按流水线节点抓取分析...
              </div>
            </TableCell>

            <!-- Actions -->
            <TableCell class="text-right">
              <div class="flex items-center justify-end gap-1">
                <Button
                  v-if="item.status === 'FAILED'"
                  size="sm"
                  variant="outline"
                  class="h-7 px-2 text-xs"
                  :disabled="retryMutation.isPending.value"
                  @click="handleRetryItem(item.item_id, item.asin)"
                >
                  <RotateCw
                    class="mr-1 h-3 w-3"
                    :class="{ 'animate-spin': retryMutation.isPending.value }"
                  />
                  重试
                </Button>
                <Button
                  v-if="item.report_available"
                  size="sm"
                  variant="ghost"
                  class="h-7 px-2 text-xs text-primary hover:text-primary"
                  @click="handleViewReport(props.taskId, item.item_id)"
                >
                  报告
                </Button>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>
  </div>
</template>
