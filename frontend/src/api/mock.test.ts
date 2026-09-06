import { describe, expect, it } from 'vitest'
import {
  buildPriceHistory,
  buildStepSpecs,
  img,
  simulateFinancial,
  stepProgress,
} from './mock'
import type { FinancialSimulateRequest } from '../types'

/** 一份"预期通过"的财务模拟请求（回本周期 < 期望值） */
const passingReq: FinancialSimulateRequest = {
  mold_cost_usd: 2000,
  moq: 2000,
  current_gross_margin: 0.32,
  expected_price_usd: 29.99,
  unit_cost_increase_usd: 0.5,
  expected_payback_months: 6,
  sea_freight_usd_per_cbm: 180,
  package_size_old_cm: [30, 20, 10],
  package_size_new_cm: [25, 18, 9],
  expected_return_rate_reduction: 0.8,
  product_lifecycle_days: 365,
}

describe('simulateFinancial', () => {
  it('体积重按 (L*W*H)/5000 计算并给出正确的 FBA 档位与单件节省', () => {
    const r = simulateFinancial(passingReq)
    expect(r.volumetric_weight_old_kg).toBeCloseTo(1.2, 5)
    expect(r.volumetric_weight_new_kg).toBeCloseTo(0.81, 5)
    // 1.2kg → Large Standard(4.54) / 0.81kg → Medium Standard(4.05)
    expect(r.fba_tier_old).toBe('Large Standard')
    expect(r.fba_tier_new).toBe('Medium Standard')
    expect(r.fulfillment_saving_usd_per_unit).toBeCloseTo(0.49, 2)
  })

  it('财务条件健康时返回 PASSED 且无否决理由', () => {
    const r = simulateFinancial(passingReq)
    expect(r.veto_status).toBe('PASSED')
    expect(r.veto_reasons).toHaveLength(0)
    expect(r.fallback_suggestions).toHaveLength(0)
    expect(r.payback_curve).toHaveLength(3)
  })

  it('开模成本 > 8000 且生命周期 < 180 天时触发窗口期风险否决', () => {
    const r = simulateFinancial({ ...passingReq, mold_cost_usd: 9000, product_lifecycle_days: 120 })
    expect(r.veto_status).toBe('VETOED')
    expect(r.veto_reasons.join()).toContain('窗口期')
    expect(r.fallback_suggestions.length).toBeGreaterThan(0)
  })

  it('单位改进成本超过毛利额 35% 时强制否决', () => {
    // 毛利 = 29.99 * 0.32 = 9.5968，35% ≈ 3.36
    const r = simulateFinancial({ ...passingReq, unit_cost_increase_usd: 4 })
    expect(r.veto_status).toBe('VETOED')
    expect(r.veto_reasons.join()).toContain('35%')
  })

  it('回本周期超出期望时否决并给出具体月份', () => {
    // 提高开模成本拉长回收期（保持生命周期 365 天，避免窗口期规则干扰）
    const r = simulateFinancial({ ...passingReq, mold_cost_usd: 15000 })
    expect(r.veto_status).toBe('VETOED')
    expect(r.veto_reasons.join()).toContain('回本周期')
  })

  it('veto_status 为 VETOED 时始终附带免开模替代建议', () => {
    const r = simulateFinancial({ ...passingReq, mold_cost_usd: 9000, product_lifecycle_days: 120 })
    expect(r.veto_status).toBe('VETOED')
    expect(r.fallback_suggestions[0]).toContain('免开模')
  })
})

describe('buildPriceHistory', () => {
  it('默认生成 91 个点（days=90 含当天），字段齐全', () => {
    const pts = buildPriceHistory()
    expect(pts).toHaveLength(91)
    expect(pts[0]).toHaveProperty('ts')
    expect(pts[0]).toHaveProperty('price')
    expect(pts[0]).toHaveProperty('bsr')
    expect(pts[0]).toHaveProperty('buy_box_price')
    expect(pts[0]).toHaveProperty('has_coupon')
  })

  it('点数 = days + 1，且按时间升序（旧在前新在后）', () => {
    const pts = buildPriceHistory(30)
    expect(pts).toHaveLength(31)
    expect(new Date(pts[pts.length - 1].ts).getTime()).toBeGreaterThan(new Date(pts[0].ts).getTime())
  })

  it('价格与 BSR 始终在业务下限之上', () => {
    const pts = buildPriceHistory(200)
    for (const p of pts) {
      expect(p.price).toBeGreaterThanOrEqual(19.99)
      expect(p.bsr).toBeGreaterThanOrEqual(400)
      expect(p.buy_box_price).toBeLessThanOrEqual(p.price)
    }
  })

  it('指定基础价格时生成序列从该价格附近出发', () => {
    const pts = buildPriceHistory(3, 50, 1)
    // 首点为 i=3 时刻，随后向 i=0 推进；序列价格均围绕 50 波动且不低于下限
    expect(pts.length).toBe(4)
    expect(pts.every((p) => p.price >= 19.99)).toBe(true)
  })
})

describe('buildStepSpecs', () => {
  it('按 docs/api.md §4.3 生成 8 步流程，末步为 COMPLETED', () => {
    const specs = buildStepSpecs('tsk_test')
    expect(specs).toHaveLength(8)
    expect(specs[0].step).toBe('QUEUED')
    expect(specs[specs.length - 1].step).toBe('COMPLETED')
    expect(specs[specs.length - 1].extra?.task_id).toBe('tsk_test')
  })

  it('抓取/质检步骤附带 fetch 统计信息', () => {
    const specs = buildStepSpecs('tsk_test')
    const fetching = specs.find((s) => s.step === 'FETCHING_DATA')
    expect(fetching?.extra?.reviews_fetched).toBe(320)
  })
})

describe('stepProgress', () => {
  it('进度区间与 docs/api.md 一致', () => {
    expect(stepProgress('QUEUED')).toBe(5)
    expect(stepProgress('FETCHING_DATA')).toBe(25)
    expect(stepProgress('VISION_AUDIT')).toBe(45)
    expect(stepProgress('SEMANTIC_CLUSTER')).toBe(65)
    expect(stepProgress('DUAL_DECISION')).toBe(85)
    expect(stepProgress('FINANCIAL_VETO')).toBe(92)
    expect(stepProgress('EVIDENCE_TRACE')).toBe(96)
    expect(stepProgress('BACKTEST_EVAL')).toBe(99)
    expect(stepProgress('COMPLETED')).toBe(100)
    expect(stepProgress('FAILED')).toBe(0)
  })
})

describe('img', () => {
  it('生成稳定本地 SVG 占位图（data URI）', () => {
    expect(img(101)).toMatch(/^data:image\/svg\+xml;charset=utf-8,/)
    expect(img(101)).toBe(img(101))
    expect(img(7, 200, 100)).not.toBe(img(8, 200, 100))
  })
})
