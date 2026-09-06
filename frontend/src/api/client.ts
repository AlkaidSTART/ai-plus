import type { ApiEnvelope } from '../types'
import { buildStepSpecs, stepProgress } from './mock'

/** 是否使用 mock 数据（后端为 stub 时开启；接真实后端设 VITE_USE_MOCK=false） */
export const USE_MOCK = (import.meta.env.VITE_USE_MOCK ?? 'true') !== 'false'

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export class ApiError extends Error {
  code: number
  httpStatus: number

  constructor(message: string, code: number, httpStatus: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.httpStatus = httpStatus
  }
}

/** 统一请求包装：解信封、非 0 code 抛 ApiError */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  const body = (await res.json().catch(() => null)) as ApiEnvelope<T> | null
  if (!res.ok || !body) {
    throw new ApiError(body?.message ?? `HTTP ${res.status}`, body?.code ?? -1, res.status)
  }
  if (body.code !== 0) {
    throw new ApiError(body.message, body.code, res.status)
  }
  return body.data
}

/** URL 查询参数构造 */
export function buildQuery(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') search.set(k, String(v))
  }
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

/**
 * SSE 事件流订阅。
 * mock 模式下用 setInterval 播放预置步骤；真实模式下用 EventSource。
 * 返回取消函数。
 */
export function subscribeTaskEvents(
  taskId: string,
  onEvent: (step: string, progress: number, message: string, extra: Record<string, unknown>) => void,
  onDone: () => void,
): () => void {
  if (USE_MOCK) {
    return subscribeMockEvents(taskId, onEvent, onDone)
  }
  const es = new EventSource(`${API_BASE}/insight/tasks/${taskId}/events`)
  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data) as {
        step: string
        progress: number
        message: string
        extra: Record<string, unknown>
      }
      onEvent(data.step, data.progress, data.message, data.extra ?? {})
      if (data.step === 'COMPLETED' || data.step === 'FAILED') {
        es.close()
        onDone()
      }
    } catch {
      /* 忽略非 JSON 心跳 */
    }
  }
  es.onerror = () => {
    es.close()
    onDone()
  }
  return () => es.close()
}

function subscribeMockEvents(
  taskId: string,
  onEvent: (step: string, progress: number, message: string, extra: Record<string, unknown>) => void,
  onDone: () => void,
): () => void {
  const specs = buildStepSpecs(taskId)
  let index = 0
  let cancelled = false
  let timer: ReturnType<typeof setTimeout> | null = null

  const tick = () => {
    if (cancelled) return
    if (index >= specs.length) {
      onDone()
      return
    }
    const spec = specs[index]
    onEvent(spec.step, stepProgress(spec.step), spec.message, spec.extra ?? {})
    index += 1
    timer = setTimeout(tick, spec.durationMs)
  }
  timer = setTimeout(tick, 300)

  return () => {
    cancelled = true
    if (timer) clearTimeout(timer)
  }
}
