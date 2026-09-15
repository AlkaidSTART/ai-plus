<script setup lang="ts">
import { BarChart, LineChart, RadarChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart3 } from '@lucide/vue'
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import EmptyState from '@/components/EmptyState.vue'

echarts.use([
  BarChart,
  LineChart,
  RadarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  CanvasRenderer,
])

/**
 * ECharts 薄封装：按需注册柱状/雷达；option 为 null 时渲染空态而非假数据。
 * 色板见 src/lib/chart.ts（CHART_COLORS）。
 */
const props = defineProps<{
  option: echarts.EChartsCoreOption | null
  heightClass?: string
}>()

const el = ref<HTMLElement | null>(null)
const chart = shallowRef<echarts.ECharts | null>(null)
let observer: ResizeObserver | null = null

onMounted(() => {
  if (!el.value) return
  chart.value = echarts.init(el.value)
  if (props.option) chart.value.setOption(props.option)
  observer = new ResizeObserver(() => chart.value?.resize())
  observer.observe(el.value)
})

watch(
  () => props.option,
  (option) => {
    if (option) chart.value?.setOption(option, { notMerge: true })
    else chart.value?.clear()
  },
)

onBeforeUnmount(() => {
  observer?.disconnect()
  chart.value?.dispose()
})
</script>

<template>
  <div class="relative w-full" :class="heightClass ?? 'h-80'">
    <div ref="el" class="h-full w-full" />
    <div
      v-if="!option"
      class="absolute inset-0 flex items-center justify-center bg-card/60"
    >
      <EmptyState
        :icon="BarChart3"
        title="暂无图表数据"
        description="数据不足时展示空态，不渲染假数据"
      />
    </div>
  </div>
</template>
