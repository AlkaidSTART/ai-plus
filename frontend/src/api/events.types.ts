/**
 * SSE 任务事件类型 —— 草案，非正式契约。
 *
 * 正式结构以后端事件 DTO 导出的 `contracts/task-events.schema.json` 为准；
 * 契约生成后删除本文件并改从契约导入（docs/architecture.md 第 5.2 节）。
 */
import type { NodeStatus, TaskLifecycleStatus } from '@/types/domain'

/** 事件类型（草案）：批次/工作单元生命周期 + 节点进度 */
export type TaskEventType =
  | 'task.status_changed'
  | 'task_item.status_changed'
  | 'task_item.node_progress'

/** SSE 事件信封（草案）：ID 支持任务内排序、去重与游标回放 */
export interface TaskEvent<TPayload = unknown> {
  /** 事件结构版本 */
  version: 1
  /** 有序事件 ID（后端持久记录游标） */
  id: string
  type: TaskEventType
  taskId: string
  /** 单 ASIN 工作单元；批次级事件为空 */
  taskItemId?: string
  /** ISO8601 时间 */
  time: string
  payload: TPayload
}

export interface NodeProgressPayload {
  nodeId: string
  nodeName: string
  status: NodeStatus
  durationMs?: number | null
  note?: string | null
}

export interface StatusChangedPayload {
  status: TaskLifecycleStatus
  /** 失败/取消原因；成功为空 */
  reason?: string | null
}
