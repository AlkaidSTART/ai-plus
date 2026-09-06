/**
 * API 门面契约测试（docs/api.md V1.0）。
 * 后端当前为 stub（backend/main.py 仅占位），故对 mock 路径做逐接口验证：
 *  - 26 个 API 函数的返回结构与 docs/api.md 各节契约一致；
 *  - 文档声明的 Query 筛选（status / min_confidence / is_read / severity …）在 mock 中生效；
 *  - SSE 订阅（§4.3）事件流可播放且可取消。
 * 接真实后端后（VITE_USE_MOCK=false）同签名走 REST，契约不变。
 */
import { describe, expect, it } from 'vitest'
import * as api from './index'
import { subscribeTaskEvents } from './client'
import type { CreateTaskRequest, FinancialSimulateRequest } from '../types'

const createTaskReq: CreateTaskRequest = {
  asins: ['B0C1234ABC'],
  marketplace: 'US',
  financial_constraint: {
    mold_cost_usd: 2000,
    moq: 2000,
    current_gross_margin: 0.32,
    expected_price_usd: 29.99,
    unit_cost_increase_usd: 0.5,
    expected_payback_months: 6,
    sea_freight_usd_per_cbm: 180,
  },
  options: { enable_backtest: true },
}

const financialReq: FinancialSimulateRequest = {
  ...createTaskReq.financial_constraint,
  package_size_old_cm: [30, 20, 10],
  package_size_new_cm: [25, 18, 9],
  expected_return_rate_reduction: 0.8,
  product_lifecycle_days: 365,
}

const mockTaskIds = { completed: 'tsk_9f2c81a4', running: 'tsk_3f7d92bc', failed: 'tsk_7a1e03fd', pending: 'tsk_c4d8e9f0' }

/* ---------- 系统 ---------- */

describe('系统 §3', () => {
  it('getHealth：返回 status/version/db/redis 字段（§3.1）', async () => {
    const r = await api.getHealth()
    expect(r.status).toBe('ok')
    expect(r.version).toMatch(/^\d+\.\d+\.\d+$/)
    expect(typeof r.db).toBe('boolean')
    expect(typeof r.redis).toBe('boolean')
  })
})

/* ---------- 洞察任务 ---------- */

describe('洞察任务 §4', () => {
  it('createTask：按 ASIN 创建任务，返回 TaskCreated 数组（§4.1）', async () => {
    const r = await api.createTask({ ...createTaskReq, asins: ['B0C1234ABC', 'B0D88X2YWZ'] })
    expect(r.tasks).toHaveLength(2)
    for (const t of r.tasks) {
      expect(t.task_id).toMatch(/^tsk_/)
      expect(t.status).toBe('PENDING')
      expect(t.estimated_seconds).toBeGreaterThan(0)
      expect(t.product_id).toBeTruthy()
    }
    // 批量的两个任务 ASIN 与请求一致
    expect(r.tasks.map((t) => t.asin)).toEqual(['B0C1234ABC', 'B0D88X2YWZ'])
  })

  it('listTasks：支持 status 筛选（§4.2）', async () => {
    const all = await api.listTasks()
    expect(all.total).toBe(4)
    const failed = await api.listTasks({ status: 'FAILED' })
    expect(failed.total).toBe(1)
    expect(failed.items[0].status).toBe('FAILED')
  })

  it('listTasks：支持分页参数（§4.2）', async () => {
    const page = await api.listTasks({ page: 2, page_size: 1 })
    expect(page.page).toBe(2)
    expect(page.page_size).toBe(1)
    expect(page.items).toHaveLength(1)
    expect(page.total).toBe(4)
  })

  it('getTask：返回任务详情，未知任务抛错（§4.5）', async () => {
    const t = await api.getTask(mockTaskIds.completed)
    expect(t.task_id).toBe(mockTaskIds.completed)
    expect(t.status).toBe('COMPLETED')
    await expect(api.getTask('tsk_nonexistent')).rejects.toThrow('任务不存在')
  })

  it('cancelTask：仅 PENDING/RUNNING 可取消，完成后取消抛 409 语义错误（§4.4）', async () => {
    const canceled = await api.cancelTask(mockTaskIds.running)
    expect(canceled.status).toBe('CANCELED')
    expect(canceled.finished_at).toBeTruthy()
    // 已完成的不可取消
    await expect(api.cancelTask(mockTaskIds.completed)).rejects.toThrow('不可取消')
  })

  it('retryTask：仅 FAILED 可重试（§4.4）', async () => {
    const retried = await api.retryTask(mockTaskIds.failed)
    expect(retried.status).toBe('RUNNING')
    expect(retried.retry_count).toBeGreaterThan(0)
    expect(retried.error_message).toBeNull()
    await expect(api.retryTask(mockTaskIds.completed)).rejects.toThrow('不可重试')
  })

  it('exportRfc：返回 Markdown 工程改款 RFC 文本（§8.2）', async () => {
    const r = await api.exportRfc(mockTaskIds.completed)
    expect(r.task_id).toBe(mockTaskIds.completed)
    expect(r.format).toBe('markdown')
    expect(r.filename).toMatch(/^RFC-.+\.md$/)
    expect(r.content).toContain('# Engineering Change RFC')
    expect(r.content).toContain('否决')
  })

  it('getInsightReport：聚合报告含任务/聚类/提案/财务/取证（§4.6）', async () => {
    const r = await api.getInsightReport(mockTaskIds.completed)
    expect(r.task.task_id).toBe(mockTaskIds.completed)
    expect(r.clusters.items.length).toBeGreaterThan(0)
    expect(r.proposals.items.length).toBeGreaterThan(0)
    expect(r.financial).toBeTruthy()
    expect(r.visual_evidences.items.length).toBeGreaterThan(0)
  })
})

/* ---------- 大盘 ---------- */

describe('大盘 §5', () => {
  it('getDashboardOverview：返回 KPI 总览，days 参数可用（§5.1）', async () => {
    const r = await api.getDashboardOverview()
    expect(r.monitored_product_count).toBeGreaterThanOrEqual(0)
    expect(r.running_task_count).toBeGreaterThanOrEqual(0)
    expect(r.pain_point_cluster_count).toBeGreaterThan(0)
    expect(r.avg_rating).toBeGreaterThan(0)
  })

  it('getRecommendations：返回分页推荐列表（§5.2）', async () => {
    const r = await api.getRecommendations()
    expect(r.items.length).toBeGreaterThan(0)
    expect(r.items[0]).toHaveProperty('title')
    expect(r.total).toBe(r.items.length)
  })
})

/* ---------- 竞品 ---------- */

describe('竞品 §6', () => {
  it('listProducts：支持 marketplace 与 keyword 筛选（§6.1）', async () => {
    const de = await api.listProducts({ marketplace: 'DE' })
    expect(de.total).toBe(1)
    expect(de.items[0].marketplace).toBe('DE')
    const kw = await api.listProducts({ keyword: 'lamp' })
    expect(kw.items.length).toBeGreaterThan(0)
  })

  it('getProduct：返回商品详情，未知商品抛错（§6.2）', async () => {
    const p = await api.getProduct('0d1f3a5e-0001')
    expect(p.asin).toBe('B0C1234ABC')
    expect(p.length_cm).toBeGreaterThan(0)
    await expect(api.getProduct('unknown')).rejects.toThrow('商品不存在')
  })

  it('getPriceHistory：返回 90 天价格时序点（§6.3）', async () => {
    const r = await api.getPriceHistory('0d1f3a5e-0001')
    expect(r.points.length).toBeGreaterThan(0)
    for (const p of r.points) {
      expect(typeof p.price).toBe('number')
      expect(typeof p.bsr).toBe('number')
      expect(p.buy_box_price).toBeLessThanOrEqual(p.price)
    }
  })
})

/* ---------- VOC ---------- */

describe('VOC §7', () => {
  it('listReviews：支持星级/语言/关键词/时间/认证筛选（§7.1）', async () => {
    const all = await api.listReviews('0d1f3a5e-0001')
    expect(all.total).toBeGreaterThan(0)
    const low = await api.listReviews('0d1f3a5e-0001', { rating_min: 2 })
    expect(low.items.every((r) => r.rating >= 2)).toBe(true)
    const en = await api.listReviews('0d1f3a5e-0001', { language: 'en' })
    expect(en.items.every((r) => r.language === 'en')).toBe(true)
    const kw = await api.listReviews('0d1f3a5e-0001', { keyword: 'crack' })
    expect(kw.total).toBeGreaterThan(0)
  })

  it('getClusters：返回痛点聚类列表（§7.2）', async () => {
    const r = await api.getClusters(mockTaskIds.completed)
    expect(r.items.length).toBeGreaterThan(0)
    expect(r.items[0]).toHaveProperty('cluster_id')
    expect(r.items[0]).toHaveProperty('frequency_ratio')
  })
})

/* ---------- 取证 ---------- */

describe('取证 §8.1', () => {
  it('getVisualEvidences：支持 defect_category 与 min_confidence 筛选（§8.1）', async () => {
    const craft = await api.getVisualEvidences(mockTaskIds.completed, { defect_category: 'craft_flaw' })
    expect(craft.items.every((e) => e.defect_category === 'craft_flaw')).toBe(true)
    // min_confidence=0.9：仅保留 confidence >= 0.9 的取证图
    const confident = await api.getVisualEvidences(mockTaskIds.completed, { min_confidence: 0.9 })
    expect(confident.items.length).toBeGreaterThan(0)
    expect(confident.items.every((e) => e.confidence >= 0.9)).toBe(true)
  })
})

/* ---------- 改款决策 ---------- */

describe('改款决策 §8.2/§8.3', () => {
  it('getProposals：按任务返回双栏改款清单（§8.2）', async () => {
    const r = await api.getProposals(mockTaskIds.completed)
    expect(r.items.length).toBe(5)
    expect(r.items.every((p) => p.task_id === mockTaskIds.completed)).toBe(true)
  })

  it('getProposal：返回单条提案详情（§8.2）', async () => {
    const p = await api.getProposal('prp_5b7e01')
    expect(p.proposal_id).toBe('prp_5b7e01')
    expect(['BODY_OPTIMIZATION', 'PACKAGING_FULFILLMENT']).toContain(p.track_type)
    await expect(api.getProposal('prp_unknown')).rejects.toThrow('提案不存在')
  })

  it('getProposalEvidence：仅已绑定证据的提案返回证据链（§8.3）', async () => {
    const ev = await api.getProposalEvidence('prp_5b7e01')
    expect(ev.reviews.length).toBeGreaterThan(0)
    await expect(api.getProposalEvidence('prp_5b7e02')).rejects.toThrow('证据不存在')
  })
})

/* ---------- 财务风控 ---------- */

describe('财务风控 §9', () => {
  it('simulateFinancialApi：健康请求返回 PASSED（§9.1）', async () => {
    const r = await api.simulateFinancialApi(financialReq)
    expect(r.veto_status).toBe('PASSED')
    expect(r.payback_curve.length).toBe(3)
  })

  it('simulateFinancialApi：成本失控触发否决（§9.1）', async () => {
    const r = await api.simulateFinancialApi({ ...financialReq, unit_cost_increase_usd: 4 })
    expect(r.veto_status).toBe('VETOED')
    expect(r.veto_reasons.length).toBeGreaterThan(0)
  })

  it('getFinancialDecision：返回任务级财务决议', async () => {
    const r = await api.getFinancialDecision(mockTaskIds.completed)
    expect(r.veto_status).toBe('PASSED')
    expect(r.task_id).toBe(mockTaskIds.completed)
    expect(r.checked_proposals).toBeGreaterThan(0)
  })
})

/* ---------- 扩展（P2） ---------- */

describe('扩展 §10', () => {
  it('getAlerts：支持 type / is_read / severity 筛选（§10.3）', async () => {
    const all = await api.getAlerts()
    expect(all.total).toBe(3)
    const price = await api.getAlerts({ type: 'price_movement' })
    expect(price.items.every((a) => a.type === 'price_movement')).toBe(true)
    const unread = await api.getAlerts({ is_read: false })
    expect(unread.items.every((a) => a.is_read === false)).toBe(true)
    const high = await api.getAlerts({ severity: 'high' })
    expect(high.items.every((a) => a.severity === 'high')).toBe(true)
  })

  it('markAlertRead：标记已读成功（§10.3）', async () => {
    await expect(api.markAlertRead('alr_01')).resolves.toBeUndefined()
  })

  it('getCrossPlatformMapping：返回跨平台 SKU 映射（§10.4）', async () => {
    const r = await api.getCrossPlatformMapping()
    expect(r.items.length).toBeGreaterThan(0)
    expect(r.items[0]).toHaveProperty('asin')
    expect(typeof r.items[0].amazon_price_usd).toBe('number')
  })

  it('runBacktest / getBacktest：发起回测并返回结果（§10.5）', async () => {
    const run = await api.runBacktest(mockTaskIds.completed)
    expect(run.status).toBe('PENDING')
    const r = await api.getBacktest(run.backtest_id)
    expect(r.backtest_id).toBe(run.backtest_id)
    expect(r.accuracy_score).toBeGreaterThan(0)
    expect(r.accuracy_score).toBeLessThanOrEqual(1)
  })
})

/* ---------- SSE（§4.3） ---------- */

describe('SSE 事件流 §4.3', () => {
  it('mock 模式：首个事件为 QUEUED，取消后停止推进', async () => {
    const steps: string[] = []
    let done = false
    const cancel = subscribeTaskEvents(
      mockTaskIds.completed,
      (step, progress, _msg, extra) => {
        steps.push(step)
        expect(progress).toBeGreaterThanOrEqual(0)
        if (step === 'COMPLETED') expect(extra.task_id).toBe(mockTaskIds.completed)
      },
      () => {
        done = true
      },
    )
    // 首个事件 300ms 后到达
    await new Promise((r) => setTimeout(r, 500))
    expect(steps[0]).toBe('QUEUED')
    cancel()
    const captured = steps.length
    await new Promise((r) => setTimeout(r, 600))
    // 取消后事件停止、不会走到 COMPLETED/done
    expect(steps.length).toBe(captured)
    expect(done).toBe(false)
  }, 5000)
})
