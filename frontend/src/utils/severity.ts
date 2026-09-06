import type { SeverityLevel } from '../types'

/**
 * 严重度映射（docs/api.md §7.2）
 * >= 4.0 critical，>= 2.5 moderate，其余 minor
 */
export function mapSeverityLevel(score: number): SeverityLevel {
  if (score >= 4.0) return 'critical'
  if (score >= 2.5) return 'moderate'
  return 'minor'
}

export const SEVERITY_LABEL: Record<SeverityLevel, string> = {
  critical: 'Critical',
  moderate: 'Moderate',
  minor: 'Minor',
}

export const SEVERITY_CLASS: Record<SeverityLevel, string> = {
  critical: 'badge-critical',
  moderate: 'badge-moderate',
  minor: 'badge-minor',
}

/** 缺陷类别中文标签 */
export const DEFECT_LABEL: Record<string, string> = {
  color_difference: '色差',
  broken_package: '运输破损',
  craft_flaw: '工艺瑕疵',
  dimension_issue: '尺寸问题',
  other: '其他',
}

/** 痛点类型中文标签 */
export const ISSUE_TYPE_LABEL: Record<string, string> = {
  product_defect: '质量',
  function_defect: '功能',
  size_spec: '尺寸',
  accessory: '配件',
  manual: '说明书',
  packaging_delivery: '包装履约',
  other: '其他',
}

/** 任务步骤中文标签 */
export const STEP_LABEL: Record<string, string> = {
  QUEUED: '任务入队',
  FETCHING_DATA: '数据采集',
  VISION_AUDIT: 'VLM 取证',
  SEMANTIC_CLUSTER: '痛点聚类',
  DUAL_DECISION: '双栏改款',
  FINANCIAL_VETO: '财务否决',
  EVIDENCE_TRACE: '证据溯源',
  BACKTEST_EVAL: '历史回测',
  COMPLETED: '已完成',
  FAILED: '失败',
}
