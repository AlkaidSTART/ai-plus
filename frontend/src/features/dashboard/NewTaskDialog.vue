<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronDown } from '@lucide/vue'
import { storeToRefs } from 'pinia'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useUiStore } from '@/stores/ui'
import { useCreateTask } from '@/composables/useTasks'
import type { TaskCreateRequest } from '@/api/client'

const ui = useUiStore()
const { newTaskDialogOpen } = storeToRefs(ui)

const asinsInput = ref('')
const site = ref('amazon-us')
const timeWindow = ref<'1m' | '3m' | '6m'>('6m')

const { mutate: submitTask, isPending } = useCreateTask()

const asinList = computed(() =>
  asinsInput.value
    .split(/[\s,，;；]+/)
    .map((s) => s.trim())
    .filter(Boolean),
)

const asinError = computed<string | null>(() => {
  if (asinList.value.length === 0) return null
  if (asinList.value.length > 10) return '单次提交支持 1-10 个竞品 ASIN'
  const invalid = asinList.value.filter((a) => !/^[A-Za-z0-9]{10}$/.test(a))
  return invalid.length ? `无效 ASIN：${invalid.join('、')}（标准 10 位）` : null
})

const canSubmit = computed(() => asinList.value.length > 0 && !asinError.value && !isPending.value)

function handleSubmit() {
  if (!canSubmit.value) return
  const body: TaskCreateRequest = {
    asins: asinList.value,
    platform: 'amazon',
    marketplace: 'US',
    window: { preset: timeWindow.value },
  }
  submitTask(
    { body, idempotencyKey: crypto.randomUUID() },
    {
      onSuccess: (data) => {
        toast.success(`任务已创建：${data.items.length} 个 ASIN`)
        newTaskDialogOpen.value = false
        asinsInput.value = ''
      },
      onError: (err) => {
        toast.error(`提交失败：${err.message}`)
      },
    },
  )
}
</script>

<template>
  <Dialog v-model:open="newTaskDialogOpen">
    <DialogContent class="sm:max-w-lg">
      <DialogHeader>
        <DialogTitle>新建诊断任务</DialogTitle>
        <DialogDescription>
          提交 1-10 个 Amazon US 竞品 ASIN 与诊断时间窗；任务为异步执行，进度经 SSE 展示真实节点状态。
        </DialogDescription>
      </DialogHeader>

      <div class="space-y-4">
        <div class="space-y-2">
          <Label for="asins">竞品 ASIN（1-10 个，逗号/空格/换行分隔）</Label>
          <Textarea
            id="asins"
            v-model="asinsInput"
            rows="3"
            placeholder="例如：B0EXAMPLE1, B0EXAMPLE2"
            class="font-mono text-sm"
          />
          <p v-if="asinError" class="text-xs text-destructive">{{ asinError }}</p>
          <p v-else-if="asinList.length" class="text-xs text-muted-foreground">
            已识别 {{ asinList.length }} 个 ASIN
          </p>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <Label>站点</Label>
            <Select v-model="site">
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="amazon-us">Amazon US</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="space-y-2">
            <Label>评论时间窗</Label>
            <Select v-model="timeWindow">
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="6m">近 6 个月</SelectItem>
                <SelectItem value="3m">近 3 个月</SelectItem>
                <SelectItem value="1m">近 1 个月</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <Collapsible>
          <CollapsibleTrigger class="flex w-full items-center gap-1 text-sm text-muted-foreground">
            <ChevronDown class="size-4" />
            财务约束输入（当前不可填）
          </CollapsibleTrigger>
          <CollapsibleContent class="pt-2">
            <p class="text-xs text-muted-foreground">
              开模预算、MOQ、毛利率与回本周期等财务输入暂未开放；当前任务的财务裁决恒为「未评估」。
            </p>
          </CollapsibleContent>
        </Collapsible>
      </div>

      <DialogFooter>
        <Button variant="outline" @click="newTaskDialogOpen = false">取消</Button>
        <Button :disabled="!canSubmit" @click="handleSubmit">
          {{ isPending ? '提交中…' : '提交任务' }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
