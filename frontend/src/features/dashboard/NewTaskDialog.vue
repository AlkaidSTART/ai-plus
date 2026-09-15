<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  ChevronDown,
  ExternalLink,
  Loader2,
  Search,
  ShoppingBag,
  Trash2,
  X,
} from '@lucide/vue'
import { storeToRefs } from 'pinia'
import { toast } from 'vue-sonner'
import { Badge } from '@/components/ui/badge'
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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { useUiStore } from '@/stores/ui'
import { useCreateTask } from '@/composables/useTasks'
import {
  searchProducts,
  type ProductItem,
  type TaskCreateRequest,
} from '@/api/client'

const ui = useUiStore()
const { newTaskDialogOpen } = storeToRefs(ui)

const activeTab = ref<'asins' | 'keyword'>('asins')
const site = ref('amazon-us')
const timeWindow = ref<'1m' | '3m' | '6m'>('6m')

// --- Direct ASIN / URL Mode ---
const asinsInput = ref('')
const directAsins = ref<string[]>([])

function extractAsinsClient(text: string): string[] {
  if (!text) return []
  const found: string[] = []
  const seen = new Set<string>()

  const add = (asin: string) => {
    const clean = asin.toUpperCase().trim()
    if (/^[A-Za-z0-9]{10}$/.test(clean) && !seen.has(clean)) {
      seen.add(clean)
      found.push(clean)
    }
  }

  // 1. URLs with /dp/ or /product/
  const urlRegex = /(?:dp|product|d)\/([A-Za-z0-9]{10})(?=[/?&#\s"']|$)/gi
  let match: RegExpExecArray | null
  while ((match = urlRegex.exec(text)) !== null) {
    add(match[1])
  }

  // 2. URL query param asin=
  const paramRegex = /[?&]asin=([A-Za-z0-9]{10})(?=[&#\s"']|$)/gi
  while ((match = paramRegex.exec(text)) !== null) {
    add(match[1])
  }

  // 3. Plain tokens
  const tokens = text.split(/[\s,，;；\n\r]+/)
  for (const token of tokens) {
    add(token)
  }

  return found
}

// Watch asinsInput and update directAsins
watch(asinsInput, (newVal) => {
  directAsins.value = extractAsinsClient(newVal)
})

function removeDirectAsin(asinToRemove: string) {
  directAsins.value = directAsins.value.filter((a) => a !== asinToRemove)
  // Reflect in textarea
  asinsInput.value = directAsins.value.join('\n')
}

function clearDirect() {
  asinsInput.value = ''
  directAsins.value = []
}

// --- Keyword Search Mode ---
const keywordQuery = ref('')
const isSearching = ref(false)
const searchResults = ref<ProductItem[]>([])
const selectedSearchAsins = ref<string[]>([])

async function handleSearch() {
  const q = keywordQuery.value.trim()
  if (!q) {
    toast.error('请输入搜索关键词，例如：女性鞋子')
    return
  }

  isSearching.value = true
  try {
    const res = await searchProducts(q, 10)
    searchResults.value = res.products || []
    // Default select all matched products up to 10
    selectedSearchAsins.value = searchResults.value.map((p) => p.asin).slice(0, 10)
    if (searchResults.value.length === 0) {
      toast.info('未检索到匹配竞品，请更换关键词重试')
    } else {
      toast.success(`已检索到 ${searchResults.value.length} 款竞品商品`)
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : '搜索竞品失败'
    toast.error(message)
  } finally {
    isSearching.value = false
  }
}

function toggleProductSelection(asin: string) {
  if (selectedSearchAsins.value.includes(asin)) {
    selectedSearchAsins.value = selectedSearchAsins.value.filter((a) => a !== asin)
  } else {
    if (selectedSearchAsins.value.length >= 10) {
      toast.warning('单次最多选择 10 个竞品')
      return
    }
    selectedSearchAsins.value.push(asin)
  }
}

function toggleSelectAll() {
  if (selectedSearchAsins.value.length === searchResults.value.length) {
    selectedSearchAsins.value = []
  } else {
    selectedSearchAsins.value = searchResults.value.map((p) => p.asin).slice(0, 10)
  }
}

// --- Effective ASIN List for Task Creation ---
const effectiveAsins = computed(() => {
  if (activeTab.value === 'asins') {
    return directAsins.value
  }
  return selectedSearchAsins.value
})

const asinError = computed<string | null>(() => {
  if (activeTab.value === 'asins') {
    if (asinsInput.value.trim() && directAsins.value.length === 0) {
      return '未识别到有效 10 位 ASIN 或 Amazon 商品链接'
    }
    if (directAsins.value.length > 10) {
      return '单次诊断最多支持 10 个 ASIN（当前已超出）'
    }
    return null
  }

  // Keyword tab
  if (searchResults.value.length > 0 && selectedSearchAsins.value.length === 0) {
    return '请至少勾选 1 款待诊断竞品'
  }
  if (selectedSearchAsins.value.length > 10) {
    return '最多支持选择 10 个竞品'
  }
  return null
})

const canSubmit = computed(() => {
  return (
    effectiveAsins.value.length > 0 &&
    effectiveAsins.value.length <= 10 &&
    !asinError.value &&
    !isPending.value
  )
})

const { mutate: submitTask, isPending } = useCreateTask()

function handleSubmit() {
  if (!canSubmit.value) return

  const body: TaskCreateRequest = {
    asins: effectiveAsins.value,
    keyword: activeTab.value === 'keyword' ? keywordQuery.value.trim() : undefined,
    platform: 'amazon',
    marketplace: 'US',
    window: { preset: timeWindow.value },
  }

  submitTask(
    { body, idempotencyKey: crypto.randomUUID() },
    {
      onSuccess: (data) => {
        toast.success(`任务已创建：${data.items.length} 个竞品正在排队诊断`)
        newTaskDialogOpen.value = false
        // Reset state
        clearDirect()
        keywordQuery.value = ''
        searchResults.value = []
        selectedSearchAsins.value = []
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
    <DialogContent class="sm:max-w-xl max-h-[90vh] flex flex-col overflow-hidden">
      <DialogHeader>
        <DialogTitle class="text-base font-semibold">新建诊断任务</DialogTitle>
        <DialogDescription class="text-xs">
          支持直接粘贴 Amazon 商品 URL 自动提取 ASIN，或输入关键词智能匹配前 10 款竞品进行深度诊断。
        </DialogDescription>
      </DialogHeader>

      <div class="flex-1 overflow-y-auto space-y-4 pr-1 py-1">
        <!-- Tabs for Direct Input vs Keyword Search -->
        <Tabs v-model="activeTab" class="w-full">
          <TabsList class="grid w-full grid-cols-2">
            <TabsTrigger value="asins" class="text-xs">ASIN / 商品链接导入</TabsTrigger>
            <TabsTrigger value="keyword" class="text-xs">关键词搜索匹配</TabsTrigger>
          </TabsList>

          <!-- Tab 1: Direct ASIN or URL Input -->
          <TabsContent value="asins" class="space-y-3 pt-2">
            <div class="space-y-1.5">
              <div class="flex items-center justify-between">
                <Label for="asins-input" class="text-xs font-medium">
                  粘贴商品链接或 ASIN（单次 1-10 个）
                </Label>
                <button
                  v-if="directAsins.length"
                  type="button"
                  class="text-[11px] text-muted-foreground hover:text-destructive flex items-center gap-1 transition-colors"
                  @click="clearDirect"
                >
                  <Trash2 class="size-3" /> 清空
                </button>
              </div>
              <Textarea
                id="asins-input"
                v-model="asinsInput"
                rows="3"
                placeholder="支持直接粘贴商品详情页 URL 或 10 位 ASIN：
例如：https://www.amazon.com/dp/B0FFW9LG7S
或：B0FFW9LG7S, B0D5N57SHS"
                class="font-mono text-xs resize-none"
              />
            </div>

            <!-- Extracted ASIN Badges -->
            <div v-if="directAsins.length > 0" class="space-y-1.5 bg-muted/40 p-2.5 rounded-lg border border-border/60">
              <div class="flex items-center justify-between text-xs">
                <span class="font-medium text-foreground">
                  已识别 ASIN ({{ directAsins.length }} / 10)
                </span>
                <span v-if="directAsins.length <= 10" class="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">
                  格式有效
                </span>
              </div>
              <div class="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto pt-1">
                <Badge
                  v-for="asin in directAsins"
                  :key="asin"
                  variant="secondary"
                  class="gap-1 font-mono text-[11px] py-0.5 px-2"
                >
                  {{ asin }}
                  <button
                    type="button"
                    class="ml-0.5 hover:text-destructive rounded focus:outline-none"
                    @click="removeDirectAsin(asin)"
                  >
                    <X class="size-3" />
                  </button>
                </Badge>
              </div>
            </div>

            <p v-if="asinError" class="text-xs text-destructive font-medium">
              {{ asinError }}
            </p>
          </TabsContent>

          <!-- Tab 2: Keyword Search Mode -->
          <TabsContent value="keyword" class="space-y-3 pt-2">
            <div class="space-y-1.5">
              <Label for="keyword-search" class="text-xs font-medium">
                输入品类或竞品关键词（检索至多 10 款竞品）
              </Label>
              <div class="flex gap-2">
                <Input
                  id="keyword-search"
                  v-model="keywordQuery"
                  placeholder="例如：女性鞋子、women running shoes"
                  class="text-xs h-9"
                  @keydown.enter.prevent="handleSearch"
                />
                <Button
                  type="button"
                  size="sm"
                  class="h-9 shrink-0 gap-1 text-xs"
                  :disabled="isSearching || !keywordQuery.trim()"
                  @click="handleSearch"
                >
                  <Loader2 v-if="isSearching" class="size-3.5 animate-spin" />
                  <Search v-else class="size-3.5" />
                  搜索竞品
                </Button>
              </div>
            </div>

            <!-- Search Results Display -->
            <div v-if="searchResults.length > 0" class="space-y-2">
              <div class="flex items-center justify-between text-xs text-muted-foreground px-0.5">
                <span>
                  已检索 {{ searchResults.length }} 款商品，已勾选
                  <strong class="text-foreground">{{ selectedSearchAsins.length }}</strong> 款
                </span>
                <button
                  type="button"
                  class="text-primary hover:underline font-medium text-[11px]"
                  @click="toggleSelectAll"
                >
                  {{ selectedSearchAsins.length === searchResults.length ? '取消全选' : '全选前 10 款' }}
                </button>
              </div>

              <ScrollArea class="h-52 rounded-md border p-1 bg-muted/20">
                <div class="space-y-1.5">
                  <div
                    v-for="prod in searchResults"
                    :key="prod.asin"
                    class="flex items-start gap-2.5 p-2 rounded-md border text-xs transition-colors cursor-pointer"
                    :class="[
                      selectedSearchAsins.includes(prod.asin)
                        ? 'bg-primary/5 border-primary/40 shadow-xs'
                        : 'bg-background hover:bg-muted/50 border-border/60'
                    ]"
                    @click="toggleProductSelection(prod.asin)"
                  >
                    <!-- Checkbox -->
                    <input
                      type="checkbox"
                      :checked="selectedSearchAsins.includes(prod.asin)"
                      class="mt-1 size-3.5 rounded text-primary cursor-pointer accent-primary"
                      @click.stop="toggleProductSelection(prod.asin)"
                    />

                    <!-- Image or Placeholder -->
                    <div class="size-11 shrink-0 rounded border bg-muted flex items-center justify-center overflow-hidden">
                      <img
                        v-if="prod.image_url"
                        :src="prod.image_url"
                        :alt="prod.title"
                        class="size-full object-cover"
                        loading="lazy"
                      />
                      <ShoppingBag v-else class="size-5 text-muted-foreground" />
                    </div>

                    <!-- Details -->
                    <div class="flex-1 min-w-0 space-y-1">
                      <div class="flex items-center justify-between gap-1">
                        <Badge variant="outline" class="font-mono text-[10px] py-0 px-1.5 h-4">
                          {{ prod.asin }}
                        </Badge>
                        <span v-if="prod.price" class="font-semibold text-foreground text-[11px]">
                          {{ prod.price }}
                        </span>
                      </div>
                      <p class="font-medium text-foreground line-clamp-2 leading-tight text-[11px]">
                        {{ prod.title }}
                      </p>
                      <div class="flex items-center gap-2 text-[10px] text-muted-foreground">
                        <span v-if="prod.rating">★ {{ prod.rating.toFixed(1) }}</span>
                        <span v-if="prod.review_count">({{ prod.review_count.toLocaleString() }} 评价)</span>
                        <a
                          v-if="prod.url"
                          :href="prod.url"
                          target="_blank"
                          rel="noopener noreferrer"
                          class="hover:text-primary flex items-center gap-0.5 ml-auto"
                          @click.stop
                        >
                          查看 <ExternalLink class="size-2.5" />
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              </ScrollArea>
            </div>

            <p v-if="asinError" class="text-xs text-destructive font-medium">
              {{ asinError }}
            </p>
          </TabsContent>
        </Tabs>

        <!-- Common Options -->
        <div class="grid grid-cols-2 gap-3 pt-1 border-t">
          <div class="space-y-1.5">
            <Label class="text-xs font-medium">目标站点</Label>
            <Select v-model="site">
              <SelectTrigger class="h-8 text-xs"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="amazon-us" class="text-xs">Amazon US (美国站)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="space-y-1.5">
            <Label class="text-xs font-medium">评论诊断时间窗</Label>
            <Select v-model="timeWindow">
              <SelectTrigger class="h-8 text-xs"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="6m" class="text-xs">近 6 个月 (推荐)</SelectItem>
                <SelectItem value="3m" class="text-xs">近 3 个月</SelectItem>
                <SelectItem value="1m" class="text-xs">近 1 个月</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <Collapsible>
          <CollapsibleTrigger class="flex w-full items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
            <ChevronDown class="size-3.5" />
            财务约束指标配置（待开放）
          </CollapsibleTrigger>
          <CollapsibleContent class="pt-1.5">
            <p class="text-[11px] text-muted-foreground bg-muted/30 p-2 rounded border leading-relaxed">
              开模预算、MOQ、目标毛利率与回本周期等财务边界指标暂未开放配置；当前任务生成的双栏改进方案将统一按工程可行性与高频痛点进行综合裁决。
            </p>
          </CollapsibleContent>
        </Collapsible>
      </div>

      <DialogFooter class="pt-3 border-t flex items-center justify-between sm:justify-between">
        <div class="text-xs text-muted-foreground">
          已选定 <strong class="text-foreground">{{ effectiveAsins.length }}</strong> / 10 个竞品
        </div>
        <div class="flex gap-2">
          <Button variant="outline" size="sm" class="text-xs h-8" @click="newTaskDialogOpen = false">
            取消
          </Button>
          <Button
            size="sm"
            class="text-xs h-8"
            :disabled="!canSubmit"
            @click="handleSubmit"
          >
            <Loader2 v-if="isPending" class="size-3.5 animate-spin mr-1" />
            {{ isPending ? '提交中…' : '创建诊断任务' }}
          </Button>
        </div>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
