/**
 * 领域概念类型（前端展示层）。
 * 与后端正式 DTO 对齐前，仅表达 PRD 6.2 的状态维度；字段以后端契约为准。
 */

/** 任务/工作单元生命周期 */
export type TaskLifecycleStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELED'

/** 痛点严重度 */
export type Severity = 'CRITICAL' | 'MODERATE' | 'MINOR'

/** 财务裁决（P0 恒为 NOT_EVALUATED） */
export type FinancialState = 'NOT_EVALUATED' | 'PASSED' | 'VETOED'

/** SSE 节点执行状态（真实节点，不伪造固定步骤） */
export type NodeStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'SKIPPED' | 'FAILED' | 'CANCELED'
