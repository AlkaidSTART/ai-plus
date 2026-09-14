<script setup lang="ts">
import { Link2 } from '@lucide/vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'

/**
 * 双栏改款建议卡。工程数值仅在输入及评估依据齐全时由后端给出；
 * value 为 null 时展示「未评估」，不让模型补造（PRD 5.3）。
 */
export interface ProposalMetric {
  label: string
  value: string | null
}

defineProps<{
  title: string
  description: string
  painPoints?: string[]
  metrics?: ProposalMetric[]
  evidenceCount?: number | null
}>()

const emit = defineEmits<{ 'view-evidence': [] }>()
</script>

<template>
  <Card>
    <CardHeader class="pb-2">
      <CardTitle class="text-sm font-medium">{{ title }}</CardTitle>
    </CardHeader>
    <CardContent class="space-y-3">
      <p class="text-sm">{{ description }}</p>
      <div v-if="painPoints?.length" class="flex flex-wrap gap-1.5">
        <Badge v-for="p in painPoints" :key="p" variant="secondary" class="text-xs">{{ p }}</Badge>
      </div>
      <dl v-if="metrics?.length" class="grid grid-cols-2 gap-x-4 gap-y-2">
        <div v-for="m in metrics" :key="m.label">
          <dt class="text-xs text-muted-foreground">{{ m.label }}</dt>
          <dd v-if="m.value != null" class="text-sm tabular-nums">{{ m.value }}</dd>
          <dd v-else>
            <Badge variant="outline" class="border-dashed border-slate-300 bg-transparent text-xs text-slate-500">
              未评估
            </Badge>
          </dd>
        </div>
      </dl>
    </CardContent>
    <CardFooter class="flex items-center justify-between">
      <span class="text-xs text-muted-foreground">
        {{ evidenceCount != null ? `基于 ${evidenceCount} 条证据` : '证据数量待后端报告提供' }}
      </span>
      <Button variant="ghost" size="sm" @click="emit('view-evidence')">
        <Link2 />
        查看证据链
      </Button>
    </CardFooter>
  </Card>
</template>
