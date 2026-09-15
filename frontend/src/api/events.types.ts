/**
 * SSE 任务事件类型。
 *
 * 当前与 `insightx.services.tasks.fetch_task_events` 返回的信封保持一致；
 * 正式 schema 生成后仍应从 `contracts/task-events.schema.json` 导入。
 */
import type { NodeStatus, TaskLifecycleStatus } from '@/types/domain'

/** 事件类型：批次/工作单元生命周期 + 节点进度 */
export type TaskEventType =
  | 'task.status_changed'
  | 'task_item.status_changed'
  | 'task_item.node_progress'

export type DataQuality = 'SUFFICIENT' | 'PARTIAL' | 'NO_DATA'

export interface TaskEventError {
  code: string
  message: string
  retryable: boolean
}

/** SSE 事件信封：ID 支持任务内排序、去重与游标回放 */
export interface TaskEvent<TPayload = unknown> {
  /** 事件结构版本 */
  version: 1
  /** 有序事件 ID（后端持久记录游标） */
  id: string
  type: TaskEventType
  task_id: string
  /** 单 ASIN 工作单元；批次级事件为空 */
  task_item_id: string | null
  /** ISO8601 时间 */
  time: string
  payload: TPayload
}

export interface NodeProgressPayload {
  node_id: string
  node_name: string
  status: NodeStatus
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
  skip_reason: string | null
  error: TaskEventError | null
}

export interface StatusChangedPayload {
  status: TaskLifecycleStatus
  data_quality?: DataQuality | null
  /** 失败/取消原因；成功为空 */
  reason?: string | null
  error?: TaskEventError | null
}
