/**
 * API 门面：所有页面只依赖本模块。
 * mock 模式（默认）直接返回内存数据；接真实后端时将 USE_MOCK 关闭，
 * 各函数会走 client.ts 的 REST 请求，签名与 docs/api.md 保持一致。
 */
import type {
  Alert,
  BacktestResult,
  Cluster,
  CreateTaskRequest,
  CrossPlatformMapping,
  DashboardOverview,
  FinancialDecision,
  FinancialSimulateRequest,
  FinancialSimulateResult,
  InsightReport,
  PageData,
  PricePoint,
  Product,
  Proposal,
  ProposalEvidence,
  Recommendation,
  Review,
  Task,
  TaskCreated,
  VisualEvidence,
} from '../types'
// 页面需要直接引用的请求/返回类型一并导出
export type { CreateTaskRequest }
import { USE_MOCK, buildQuery, request } from './client'
import {
  buildPriceHistory,
  mockAlerts,
  mockBacktest,
  mockClusters,
  mockCrossPlatform,
  mockEvidences,
  mockFinancialDecision,
  mockOverview,
  mockProducts,
  mockProposalEvidence,
  mockProposals,
  mockRecommendations,
  mockReviews,
  mockTasks,
  simulateFinancial,
} from './mock'

function ok<T>(data: T, delay = 120): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), delay))
}

function paginate<T>(items: T[], page = 1, pageSize = 20): PageData<T> {
  const start = (page - 1) * pageSize
  return { items: items.slice(start, start + pageSize), total: items.length, page, page_size: pageSize }
}

/* ---------- 系统 ---------- */

export async function getHealth() {
  if (USE_MOCK) return ok({ status: 'ok', version: '0.1.0', db: true, redis: true })
  return request('/health')
}

/* ---------- 洞察任务 ---------- */

export async function createTask(req: CreateTaskRequest): Promise<{ tasks: TaskCreated[] }> {
  if (USE_MOCK) {
    const created: TaskCreated[] = req.asins.map((asin, i) => ({
      task_id: `tsk_${Math.random().toString(16).slice(2, 10)}`,
      asin,
      product_id: mockProducts[i % mockProducts.length].product_id,
      status: 'PENDING',
      cache_hit: false,
      estimated_seconds: 45,
      created_at: new Date().toISOString(),
    }))
    return ok({ tasks: created }, 400)
  }
  return request('/insight/tasks', { method: 'POST', body: JSON.stringify(req) })
}

export async function listTasks(params?: {
  status?: string
  asin?: string
  page?: number
  page_size?: number
}): Promise<PageData<Task>> {
  if (USE_MOCK) {
    let items = [...mockTasks]
    if (params?.status) items = items.filter((t) => t.status === params.status)
    if (params?.asin) items = items.filter((t) => t.asin.includes(params.asin!))
    return ok(paginate(items, params?.page, params?.page_size))
  }
  return request(`/insight/tasks${buildQuery(params ?? {})}`)
}

export async function getTask(taskId: string): Promise<Task> {
  if (USE_MOCK) {
    const task = mockTasks.find((t) => t.task_id === taskId)
    if (!task) throw new Error(`任务不存在: ${taskId}`)
    return ok(task)
  }
  return request(`/insight/tasks/${taskId}`)
}

/** 取消任务：仅 PENDING/RUNNING 可取消（api.md §4.4，冲突返回 40901） */
export async function cancelTask(taskId: string): Promise<Task> {
  if (USE_MOCK) {
    const task = mockTasks.find((t) => t.task_id === taskId)
    if (!task) throw new Error(`任务不存在: ${taskId}`)
    if (task.status !== 'PENDING' && task.status !== 'RUNNING') {
      throw new Error(`任务状态为 ${task.status}，不可取消`)
    }
    const updated: Task = { ...task, status: 'CANCELED', current_node: 'CANCELED', progress: task.progress, finished_at: new Date().toISOString() }
    Object.assign(task, updated)
    return ok(updated, 160)
  }
  return request(`/insight/tasks/${taskId}/cancel`, { method: 'POST' })
}

/** 重试失败任务：仅 FAILED 可重试（api.md §4.4） */
export async function retryTask(taskId: string): Promise<Task> {
  if (USE_MOCK) {
    const task = mockTasks.find((t) => t.task_id === taskId)
    if (!task) throw new Error(`任务不存在: ${taskId}`)
    if (task.status !== 'FAILED') throw new Error(`任务状态为 ${task.status}，不可重试`)
    const updated: Task = {
      ...task,
      status: 'RUNNING',
      current_node: 'FETCHING_DATA',
      progress: 8,
      retry_count: task.retry_count + 1,
      error_message: null,
      started_at: new Date().toISOString(),
      finished_at: null,
    }
    Object.assign(task, updated)
    return ok(updated, 160)
  }
  return request(`/insight/tasks/${taskId}/retry`, { method: 'POST' })
}

/** 导出工程改款 RFC（api.md §8.2 P2）：mock 模式返回 Markdown 文档文本 */
export async function exportRfc(taskId: string): Promise<{ task_id: string; format: string; filename: string; content: string }> {
  if (USE_MOCK) {
    const task = mockTasks.find((t) => t.task_id === taskId) ?? mockTasks[0]
    const proposals = mockProposals.filter((p) => p.task_id === task.task_id)
    const lines = [
      `# Engineering Change RFC — ${task.asin}（${task.marketplace}）`,
      `- 任务 ID: ${task.task_id}`,
      `- 生成时间: ${new Date().toISOString()}`,
      `- 提案总数: ${proposals.length}，通过 ${proposals.filter((p) => p.status === 'PASSED').length} / 否决 ${proposals.filter((p) => p.status === 'VETOED').length}`,
      ``,
      ...proposals.map(
        (p) =>
          `## [${p.track_type === 'BODY_OPTIMIZATION' ? '本体优化' : '包装履约'}] ${p.title}\n` +
          `- 状态: ${p.status}${p.veto_reason ? `（否决原因: ${p.veto_reason}）` : ''}\n` +
          `- 成本估算: $${p.cost_estimation_usd}，ROI ${p.estimated_roi}，缺陷率降幅 ${(p.defect_rate_reduction * 100).toFixed(0)}%\n` +
          `- 依据聚类: ${p.source_cluster_ids.join(', ')}`,
      ),
    ]
    return ok({ task_id: task.task_id, format: 'markdown', filename: `RFC-${task.asin}.md`, content: lines.join('\n') }, 300)
  }
  return request(`/insight/tasks/${taskId}/export`, { method: 'POST' })
}

export async function getInsightReport(taskId: string): Promise<InsightReport> {
  if (USE_MOCK) {
    const task = mockTasks.find((t) => t.task_id === taskId) ?? mockTasks[0]
    return ok({
      task,
      clusters: paginate(mockClusters, 1, 10),
      proposals: paginate(mockProposals, 1, 10),
      financial: mockFinancialDecision,
      visual_evidences: paginate(mockEvidences, 1, 20),
    })
  }
  return request(`/insight/tasks/${taskId}/report`)
}

/* ---------- 大盘 ---------- */

export async function getDashboardOverview(): Promise<DashboardOverview> {
  if (USE_MOCK) return ok(mockOverview)
  return request('/dashboard/overview')
}

export async function getRecommendations(): Promise<PageData<Recommendation>> {
  if (USE_MOCK) return ok(paginate(mockRecommendations))
  return request('/dashboard/recommendations')
}

/* ---------- 竞品 ---------- */

export async function listProducts(params?: {
  platform?: string
  marketplace?: string
  keyword?: string
  page?: number
  page_size?: number
}): Promise<PageData<Product>> {
  if (USE_MOCK) {
    let items = [...mockProducts]
    if (params?.keyword) {
      const kw = params.keyword.toLowerCase()
      items = items.filter((p) => p.title.toLowerCase().includes(kw) || p.asin.toLowerCase().includes(kw))
    }
    return ok(paginate(items, params?.page, params?.page_size))
  }
  return request(`/products${buildQuery(params ?? {})}`)
}

export async function getProduct(productId: string): Promise<Product> {
  if (USE_MOCK) {
    const p = mockProducts.find((x) => x.product_id === productId)
    if (!p) throw new Error(`商品不存在: ${productId}`)
    return ok(p)
  }
  return request(`/products/${productId}`)
}

export async function getPriceHistory(productId: string): Promise<{ points: PricePoint[] }> {
  if (USE_MOCK) {
    const idx = mockProducts.findIndex((x) => x.product_id === productId)
    return ok({ points: buildPriceHistory(90, mockProducts[idx]?.current_price ?? 29.99, idx + 1) })
  }
  return request(`/products/${productId}/price-history`)
}

/* ---------- VOC ---------- */

export async function listReviews(
  productId: string,
  params?: { rating_min?: number; rating_max?: number; language?: string; keyword?: string; verified_only?: boolean; start_date?: string; end_date?: string; page?: number; page_size?: number },
): Promise<PageData<Review>> {
  if (USE_MOCK) {
    let items = [...mockReviews]
    if (params?.rating_min != null) items = items.filter((r) => r.rating >= params.rating_min!)
    if (params?.rating_max != null) items = items.filter((r) => r.rating <= params.rating_max!)
    if (params?.language) items = items.filter((r) => r.language === params.language)
    if (params?.keyword) {
      const kw = params.keyword.toLowerCase()
      items = items.filter(
        (r) => r.title.toLowerCase().includes(kw) || r.content.toLowerCase().includes(kw) || r.translated_content.toLowerCase().includes(kw),
      )
    }
    if (params?.verified_only) items = items.filter((r) => r.verified_purchase)
    if (params?.start_date) items = items.filter((r) => r.review_date >= params.start_date!)
    if (params?.end_date) items = items.filter((r) => r.review_date <= params.end_date!)
    return ok(paginate(items, params?.page, params?.page_size))
  }
  return request(`/products/${productId}/reviews${buildQuery(params ?? {})}`)
}

export async function getClusters(taskId: string): Promise<PageData<Cluster>> {
  if (USE_MOCK) return ok(paginate(mockClusters, 1, 10))
  return request(`/insight/tasks/${taskId}/clusters`)
}

/* ---------- 取证 ---------- */

export async function getVisualEvidences(
  taskId: string,
  params?: { defect_category?: string; min_confidence?: number; page?: number; page_size?: number },
): Promise<PageData<VisualEvidence>> {
  if (USE_MOCK) {
    let items = [...mockEvidences]
    if (params?.defect_category) items = items.filter((e) => e.defect_category === params.defect_category)
    return ok(paginate(items, params?.page, params?.page_size))
  }
  return request(`/insight/tasks/${taskId}/visual-evidences${buildQuery(params ?? {})}`)
}

/* ---------- 改款决策 ---------- */

export async function getProposals(taskId: string): Promise<PageData<Proposal>> {
  if (USE_MOCK) {
    // 提案自带 task_id，按任务过滤实现跨模块联动
    const items = mockProposals.filter((p) => p.task_id === taskId)
    return ok(paginate(items.length ? items : mockProposals, 1, 20))
  }
  return request(`/insight/tasks/${taskId}/proposals`)
}

export async function getProposal(proposalId: string): Promise<Proposal> {
  if (USE_MOCK) {
    const p = mockProposals.find((x) => x.proposal_id === proposalId)
    if (!p) throw new Error(`提案不存在: ${proposalId}`)
    return ok(p)
  }
  return request(`/proposals/${proposalId}`)
}

export async function getProposalEvidence(proposalId: string): Promise<ProposalEvidence> {
  if (USE_MOCK) {
    const ev = mockProposalEvidence[proposalId]
    if (!ev) throw new Error(`证据不存在: ${proposalId}`)
    return ok(ev, 200)
  }
  return request(`/proposals/${proposalId}/evidence`)
}

/* ---------- 财务风控 ---------- */

export async function simulateFinancialApi(req: FinancialSimulateRequest): Promise<FinancialSimulateResult> {
  if (USE_MOCK) return ok(simulateFinancial(req), 60)
  return request('/financial/simulate', { method: 'POST', body: JSON.stringify(req) })
}

export async function getFinancialDecision(taskId: string): Promise<FinancialDecision> {
  if (USE_MOCK) return ok(mockFinancialDecision)
  return request(`/insight/tasks/${taskId}/financial`)
}

/* ---------- 扩展（P2） ---------- */

export async function getAlerts(params?: { type?: string; is_read?: boolean; page?: number; page_size?: number }): Promise<PageData<Alert>> {
  if (USE_MOCK) {
    let items = [...mockAlerts]
    if (params?.type) items = items.filter((a) => a.type === params.type)
    return ok(paginate(items, params?.page, params?.page_size))
  }
  return request(`/alerts${buildQuery(params ?? {})}`)
}

export async function markAlertRead(alertId: string): Promise<void> {
  if (USE_MOCK) return ok(undefined)
  return request(`/alerts/${alertId}`, { method: 'PATCH', body: JSON.stringify({ is_read: true }) })
}

export async function getCrossPlatformMapping(): Promise<PageData<CrossPlatformMapping>> {
  if (USE_MOCK) return ok(paginate(mockCrossPlatform))
  return request('/cross-platform/mapping')
}

export async function runBacktest(taskId: string): Promise<{ backtest_id: string; status: string }> {
  if (USE_MOCK) return ok({ backtest_id: mockBacktest.backtest_id, status: 'PENDING' }, 200)
  return request('/backtest/run', { method: 'POST', body: JSON.stringify({ task_id: taskId }) })
}

export async function getBacktest(backtestId: string): Promise<BacktestResult> {
  if (USE_MOCK) return ok(mockBacktest)
  return request(`/backtest/${backtestId}`)
}
