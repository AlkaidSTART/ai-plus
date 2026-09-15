import { onBeforeUnmount, ref, watch, type Ref } from 'vue'
import type { TaskEvent } from '@/api/events.types'

export interface UseTaskEventsOptions {
  /** 事件处理：调用方负责更新页面状态或 Query cache；本组合式函数按 `event.id` 去重。 */
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
 * 当前接入后端持久事件端点；事件 JSON 字段使用后端 snake_case DTO。
 */
export function useTaskEvents(taskId: Ref<string | null>, options: UseTaskEventsOptions) {
  const connected = ref(false)
  const lastEventId = ref<string | null>(options.lastEventId?.value ?? null)
  let source: EventSource | null = null
  let sourceTaskId: string | null = null

  const eventTypes: TaskEvent['type'][] = [
    'task.status_changed',
    'task_item.status_changed',
    'task_item.node_progress',
  ]

  function close(): void {
    source?.close()
    source = null
    sourceTaskId = null
    connected.value = false
  }

  function cursorIsNewer(eventId: string): boolean {
    if (!lastEventId.value) return true
    if (!/^\d+$/.test(eventId) || !/^\d+$/.test(lastEventId.value)) {
      return eventId !== lastEventId.value
    }
    return BigInt(eventId) > BigInt(lastEventId.value)
  }

  function handleMessage(message: MessageEvent<string>): void {
    let event: TaskEvent
    try {
      event = JSON.parse(message.data) as TaskEvent
    } catch {
      return
    }
    if (!cursorIsNewer(event.id)) return

    lastEventId.value = message.lastEventId || event.id
    options.onEvent(event)

    if (
      event.type === 'task.status_changed' &&
      ['COMPLETED', 'FAILED', 'CANCELED'].includes(
        (event.payload as { status?: string }).status ?? '',
      )
    ) {
      close()
    }
  }

  function connect(): void {
    const id = taskId.value
    if (!id || source) return
    if (sourceTaskId !== id) {
      lastEventId.value = options.lastEventId?.value ?? null
    }

    const path = `/api/v1/tasks/${encodeURIComponent(id)}/events`
    const url = lastEventId.value
      ? `${path}?after=${encodeURIComponent(lastEventId.value)}`
      : path
    source = new EventSource(url)
    sourceTaskId = id

    source.onopen = () => {
      connected.value = true
    }

    source.onerror = () => {
      // EventSource 自动重连；浏览器会携带 Last-Event-ID，后端按游标回放
      connected.value = false
    }

    for (const eventType of eventTypes) {
      source.addEventListener(eventType, (event) => {
        handleMessage(event as MessageEvent<string>)
      })
    }
  }

  watch(taskId, close)
  onBeforeUnmount(close)

  return { connected, lastEventId, connect, close }
}
