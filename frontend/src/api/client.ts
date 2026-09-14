/**
 * Thin fetch wrapper for InsightX REST API.
 * Vite proxy forwards /api → backend; no base URL needed.
 */

export class ApiError extends Error {
  status: number
  code: string
  details?: unknown

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  const body = await res.json()
  if (!res.ok) {
    const err = body?.error ?? {}
    throw new ApiError(res.status, err.code ?? 'UNKNOWN', err.message ?? res.statusText, err.details)
  }
  return body.data as T
}

// --- Types (mirror backend schemas, minimal subset) ---

export interface TaskWindow {
  preset: '1m' | '3m' | '6m'
}

export interface TaskCreateRequest {
  asins: string[]
  platform: 'amazon'
  marketplace: 'US'
  window: TaskWindow
}

export interface TaskCreatedItem {
  item_id: string
  asin: string
  status: string
}

export interface TaskCreatedResponse {
  task_id: string
  status: string
  reused: boolean
  parent_task_id: string | null
  created_at: string
  items: TaskCreatedItem[]
}

export interface TaskListItem {
  task_id: string
  status: string
  platform: string
  marketplace: string
  window: TaskWindow
  created_at: string
  updated_at: string
  total_items: number
  completed_items: number
  failed_items: number
  canceled_items: number
  last_event_id: string | null
}

export interface Page<T> {
  items: T[]
  next_cursor: string | null
}

// ponytail: full TaskSnapshot type omitted — add when detail page exists

// --- Endpoints ---

export function createTask(body: TaskCreateRequest, idempotencyKey: string) {
  return request<TaskCreatedResponse>('/api/v1/tasks', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify(body),
  })
}

export function listTasks(params?: { status?: string; cursor?: string; limit?: number }) {
  const qs = new URLSearchParams()
  if (params?.status) qs.set('status', params.status)
  if (params?.cursor) qs.set('cursor', params.cursor)
  if (params?.limit) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return request<Page<TaskListItem>>(`/api/v1/tasks${query ? `?${query}` : ''}`)
}

export function getTask(taskId: string) {
  return request<unknown>(`/api/v1/tasks/${encodeURIComponent(taskId)}`)
}

export function cancelTask(taskId: string) {
  return request<unknown>(`/api/v1/tasks/${encodeURIComponent(taskId)}/cancel`, { method: 'POST' })
}
