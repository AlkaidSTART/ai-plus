import { onBeforeUnmount, ref, type Ref } from 'vue'
import type { TaskEvent } from '@/api/events.types'

export interface UseTaskEventsOptions {
  /**
   * 事件处理：调用方负责按 `event.id` 去重并更新 Query cache。
   * 事件类型为草案（见 events.types.ts 文件头）。
   */
  onEvent: (event: TaskEvent) => void
  /** 连接建立时已知的最后事件 ID，用于断线/首次恢复时的游标回放衔接 */
  lastEventId?: Ref<string | null>
}

/**
 * 任务事件 SSE 订阅（每页至多一条连接）。
 *
 * - 历史回放由后端实现：携带 `Last-Event-ID` 重建连接，读取持久事件游标；
 * - 终态（COMPLETED/FAILED/CANCELED）与组件卸载时关闭连接；
 * - 关闭页面/断开连接不取消任务（取消走 REST 显式提交）。
 *
 * 当前为结构占位：后端契约与事件 schema 就绪前不发起真实连接。
 */
export function useTaskEvents(taskId: Ref<string | null>, options: UseTaskEventsOptions) {
  const connected = ref(false)
  const lastEventId = ref<string | null>(options.lastEventId?.value ?? null)
  let source: EventSource | null = null

  function close(): void {
    source?.close()
    source = null
    connected.value = false
  }

  function connect(): void {
    if (!taskId.value || source) return
    // 草案地址，正式路径以 contracts/openapi.json 为准
    const url = `/api/v1/tasks/${encodeURIComponent(taskId.value)}/events`
    source = new EventSource(url)
    connected.value = true

    source.onmessage = (message) => {
      if (message.lastEventId) lastEventId.value = message.lastEventId
      let event: TaskEvent
      try {
        event = JSON.parse(message.data) as TaskEvent
      } catch {
        return // 忽略无法解析的事件，等待 schema 校验接入
      }
      options.onEvent(event)
      if (
        event.type === 'task.status_changed' &&
        ['COMPLETED', 'FAILED', 'CANCELED'].includes(
          (event.payload as { status?: string }).status ?? '',
        )
      ) {
        close() // 终态关闭，避免常驻连接
      }
    }

    source.onerror = () => {
      // EventSource 自动重连；浏览器会携带 Last-Event-ID，后端按游标回放
      connected.value = false
    }
  }

  onBeforeUnmount(close)

  return { connected, lastEventId, connect, close }
}
