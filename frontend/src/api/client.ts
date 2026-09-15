/**
 * Thin fetch wrapper for the InsightX REST API.
 * Vite forwards `/api` to the backend in development.
 */
import type {
  EvidenceResponse,
  FinancialEvaluateRequest,
  FinancialEvaluateResponse,
  FinancialRuleInfo,
  HealthResponse,
  ListEvidenceParams,
  ListTasksParams,
  Page,
  ReportResponse,
  TaskCreatedResponse,
  TaskCreateRequest,
  TaskListItem,
  TaskSnapshot,
} from './types'

export * from './types'

export class ApiError extends Error {
  status: number
  code: string
  details?: unknown
  retryable: boolean
  requestId: string | null

  constructor(
    status: number,
    code: string,
    message: string,
    details?: unknown,
    retryable = false,
    requestId: string | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
    this.retryable = retryable
    this.requestId = requestId
  }

  get isReportNotReady(): boolean {
    return this.status === 409 && this.code === 'REPORT_NOT_READY'
  }
}

type JsonObject = Record<string, unknown>

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  const text = await res.text()

  let body: unknown = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
  }

  if (!res.ok) {
    const error = isJsonObject(body) && isJsonObject(body.error) ? body.error : {}
    throw new ApiError(
      res.status,
      typeof error.code === 'string' ? error.code : 'UNKNOWN',
      typeof error.message === 'string' ? error.message : res.statusText || '请求失败',
      error.details,
      error.retryable === true,
      typeof error.request_id === 'string' ? error.request_id : null,
    )
  }

  if (res.status === 204 || !text) return undefined as T
  if (isJsonObject(body) && body.code === 0 && 'data' in body) return body.data as T
  return body as T
}

function withQuery(path: string, values: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== '') params.set(key, String(value))
  }
  const query = params.toString()
  return query ? `${path}?${query}` : path
}

function jsonRequest(body: unknown): Pick<RequestInit, 'headers' | 'body'> {
  return {
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

// --- Endpoints ---

export function getHealth(signal?: AbortSignal) {
  return request<HealthResponse>('/api/v1/health', { signal })
}

export function createTask(
  body: TaskCreateRequest,
  idempotencyKey: string,
  signal?: AbortSignal,
) {
  return request<TaskCreatedResponse>('/api/v1/tasks', {
    method: 'POST',
    signal,
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify(body),
  })
}

export function listTasks(params: ListTasksParams = {}, signal?: AbortSignal) {
  return request<Page<TaskListItem>>(
    withQuery('/api/v1/tasks', {
      status: params.status,
      cursor: params.cursor,
      limit: params.limit,
    }),
    { signal },
  )
}

export function getTask(taskId: string, signal?: AbortSignal) {
  return request<TaskSnapshot>(`/api/v1/tasks/${encodeURIComponent(taskId)}`, { signal })
}

export function cancelTask(taskId: string, signal?: AbortSignal) {
  return request<TaskSnapshot>(`/api/v1/tasks/${encodeURIComponent(taskId)}/cancel`, {
    method: 'POST',
    signal,
  })
}

export function retryTask(
  taskId: string,
  itemIds: string[],
  idempotencyKey: string,
  signal?: AbortSignal,
) {
  return request<TaskCreatedResponse>(`/api/v1/tasks/${encodeURIComponent(taskId)}/retry`, {
    method: 'POST',
    signal,
    ...jsonRequest({ item_ids: itemIds }),
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
  })
}

export function getReport(taskId: string, itemId: string, signal?: AbortSignal) {
  return request<ReportResponse>(
    `/api/v1/tasks/${encodeURIComponent(taskId)}/items/${encodeURIComponent(itemId)}/report`,
    { signal },
  )
}

export function listEvidence(
  taskId: string,
  itemId: string,
  params: ListEvidenceParams = {},
  signal?: AbortSignal,
) {
  return request<Page<EvidenceResponse>>(
    withQuery(
      `/api/v1/tasks/${encodeURIComponent(taskId)}/items/${encodeURIComponent(itemId)}/evidence`,
      {
        claim_id: params.claim_id,
        source_type: params.source_type,
        cursor: params.cursor,
        limit: params.limit,
      },
    ),
    { signal },
  )
}

export function getFinancialRules(signal?: AbortSignal) {
  return request<FinancialRuleInfo>('/api/v1/financial/rules', { signal })
}

export function evaluateFinancial(
  body: FinancialEvaluateRequest,
  signal?: AbortSignal,
) {
  return request<FinancialEvaluateResponse>('/api/v1/financial/evaluate', {
    method: 'POST',
    signal,
    ...jsonRequest(body),
  })
}

export function getTaskItemFinancial(
  taskId: string,
  itemId: string,
  signal?: AbortSignal,
) {
  return request<FinancialEvaluateResponse>(
    `/api/v1/tasks/${encodeURIComponent(taskId)}/items/${encodeURIComponent(itemId)}/financial`,
    { signal },
  )
}

export function evaluateTaskItemFinancial(
  taskId: string,
  itemId: string,
  body: FinancialEvaluateRequest,
  signal?: AbortSignal,
) {
  return request<FinancialEvaluateResponse>(
    `/api/v1/tasks/${encodeURIComponent(taskId)}/items/${encodeURIComponent(itemId)}/financial`,
    {
      method: 'POST',
      signal,
      ...jsonRequest(body),
    },
  )
}

export async function exportTask(taskId: string, signal?: AbortSignal): Promise<Blob> {
  const res = await fetch(`/api/v1/tasks/${encodeURIComponent(taskId)}/export`, { signal })
  if (!res.ok) {
    const text = await res.text()
    let message = '导出工程任务书失败'
    try {
      const body = JSON.parse(text)
      if (body?.error?.message) {
        message = body.error.message
      }
    } catch {
      // fallback
    }
    throw new ApiError(res.status, 'EXPORT_FAILED', message)
  }
  return res.blob()
}


