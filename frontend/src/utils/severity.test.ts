import { describe, expect, it } from 'vitest'
import { ISSUE_TYPE_LABEL, mapSeverityLevel, SEVERITY_LABEL, STEP_LABEL } from './severity'

describe('mapSeverityLevel（docs/api.md §7.2）', () => {
  it('>= 4.0 为 critical', () => {
    expect(mapSeverityLevel(4.0)).toBe('critical')
    expect(mapSeverityLevel(4.6)).toBe('critical')
  })

  it('>= 2.5 为 moderate', () => {
    expect(mapSeverityLevel(2.5)).toBe('moderate')
    expect(mapSeverityLevel(3.8)).toBe('moderate')
  })

  it('其余为 minor', () => {
    expect(mapSeverityLevel(2.4)).toBe('minor')
    expect(mapSeverityLevel(0)).toBe('minor')
  })

  it('严重度与标签映射完整', () => {
    expect(Object.keys(SEVERITY_LABEL).sort()).toEqual(['critical', 'minor', 'moderate'])
    expect(SEVERITY_LABEL.critical).toBe('Critical')
  })
})

describe('业务标签', () => {
  it('痛点类型包含质量/功能/包装履约', () => {
    expect(ISSUE_TYPE_LABEL.product_defect).toBe('质量')
    expect(ISSUE_TYPE_LABEL.packaging_delivery).toBe('包装履约')
  })

  it('任务步骤包含双栏改款与财务否决', () => {
    expect(STEP_LABEL.DUAL_DECISION).toBe('双栏改款')
    expect(STEP_LABEL.FINANCIAL_VETO).toBe('财务否决')
    expect(STEP_LABEL.EVIDENCE_TRACE).toBe('证据溯源')
  })
})
