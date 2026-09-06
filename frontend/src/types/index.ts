/**
 * InsightX 前端类型定义
 * 字段与 docs/api.md 接口契约保持一致
 */

export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
}

export interface PageData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/* ---------- 洞察任务 ---------- */

export type TaskStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELED'

export type TaskStep =
  | 'QUEUED'
  | 'FETCHING_DATA'
  | 'VISION_AUDIT'
  | 'SEMANTIC_CLUSTER'
  | 'DUAL_DECISION'
  | 'FINANCIAL_VETO'
  | 'EVIDENCE_TRACE'
  | 'BACKTEST_EVAL'
  | 'COMPLETED'
  | 'FAILED'

export const TASK_STEPS: TaskStep[] = [
  'QUEUED',
  'FETCHING_DATA',
  'VISION_AUDIT',
  'SEMANTIC_CLUSTER',
  'DUAL_DECISION',
  'FINANCIAL_VETO',
  'EVIDENCE_TRACE',
  'BACKTEST_EVAL',
]

export interface FinancialConstraint {
  mold_cost_usd: number
  moq: number
  current_gross_margin: number
  expected_price_usd: number
  unit_cost_increase_usd: number
  expected_payback_months: number
  sea_freight_usd_per_cbm: number
}

export interface CreateTaskRequest {
  asins: string[]
  amazon_url?: string | null
  platform?: string
  marketplace?: string
  review_window_months?: number
  max_reviews?: number
  financial_constraint: FinancialConstraint
  options?: {
    enable_vision_audit?: boolean
    enable_backtest?: boolean
  }
}

export interface TaskSummary {
  review_count: number
  cluster_count: number
  proposal_count: number
  veto_status: 'PENDING' | 'PASSED' | 'VETOED'
  backtest_score: number | null
}

export interface Task {
  task_id: string
  asin: string
  product_id: string
  platform: string
  marketplace: string
  status: TaskStatus
  current_node: string
  progress: number
  retry_count: number
  financial_constraint: FinancialConstraint
  summary: TaskSummary | null
  error_message: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface TaskCreated {
  task_id: string
  asin: string
  product_id: string
  status: TaskStatus
  cache_hit: boolean
  estimated_seconds: number
  created_at: string
}

export interface TaskEvent {
  task_id: string
  step: TaskStep
  progress: number
  message: string
  extra: Record<string, unknown>
  timestamp: string
}

export interface InsightReport {
  task: Task
  clusters: PageData<Cluster>
  proposals: PageData<Proposal>
  financial: FinancialDecision | null
  visual_evidences: PageData<VisualEvidence>
}

/* ---------- 大盘 ---------- */

export interface DashboardOverview {
  monitored_product_count: number
  running_task_count: number
  pain_point_cluster_count: number
  fba_saving_pool_usd: number
  veto_triggered_count: number
  avg_rating: number
  negative_review_rate: number
}

export interface Recommendation {
  task_id: string
  product_id: string
  asin: string
  title: string
  main_image_url: string
  estimated_roi: number
  return_rate_reduction: number
  veto_status: 'PASSED' | 'VETOED'
  finished_at: string
}

/* ---------- 竞品 ---------- */

export interface Product {
  product_id: string
  asin: string
  platform: string
  marketplace: string
  title: string
  category: string
  current_price: number
  currency: string
  main_image_url: string
  review_count: number
  avg_rating: number
  bsr: number
  bsr_category?: string
  length_cm?: number
  width_cm?: number
  height_cm?: number
  weight_kg?: number
  created_at?: string
  updated_at: string
}

export interface PricePoint {
  ts: string
  price: number
  bsr: number
  buy_box_price: number
  has_coupon: boolean
}

/* ---------- VOC ---------- */

export interface Review {
  review_id: string
  rating: number
  review_date: string
  language: string
  title: string
  content: string
  translated_content: string
  verified_purchase: boolean
  helpful_votes: number
  image_urls: string[]
  cluster_ids: string[]
}

export type IssueType =
  | 'product_defect'
  | 'function_defect'
  | 'size_spec'
  | 'accessory'
  | 'manual'
  | 'packaging_delivery'
  | 'other'

export type SeverityLevel = 'critical' | 'moderate' | 'minor'

export interface ClusterQuote {
  review_id: string
  language: string
  content: string
  translated_content: string
  rating: number
}

export interface Cluster {
  cluster_id: string
  cluster_name: string
  issue_type: IssueType
  frequency: number
  frequency_ratio: number
  severity_score: number
  severity_level: SeverityLevel
  keywords: string[]
  sample_quotes: ClusterQuote[]
  sample_image_ids: string[]
}

/* ---------- 取证 ---------- */

export type DefectCategory =
  | 'color_difference'
  | 'broken_package'
  | 'craft_flaw'
  | 'dimension_issue'
  | 'other'

export interface VisualEvidence {
  image_id: string
  review_id: string
  storage_url: string
  defect_category: DefectCategory
  description: string
  confidence: number
  bbox: [number, number, number, number]
  cluster_ids: string[]
}

/* ---------- 改款决策 ---------- */

export type TrackType = 'BODY_OPTIMIZATION' | 'PACKAGING_FULFILLMENT'
export type ProposalStatus = 'PASSED' | 'VETOED'

export interface Proposal {
  proposal_id: string
  task_id: string
  track_type: TrackType
  title: string
  description: string
  cost_estimation_usd: number
  mold_opening_required: boolean
  mold_cycle_days: number
  estimated_roi: number
  defect_rate_reduction: number
  status: ProposalStatus
  veto_reason: string | null
  fallback_applied: boolean
  source_cluster_ids: string[]
  evidence_review_count: number
  evidence_image_count: number
  created_at: string
  /* 包装履约轨专属字段 */
  package_size_old_cm?: [number, number, number]
  package_size_new_cm?: [number, number, number]
  volumetric_weight_old_kg?: number
  volumetric_weight_new_kg?: number
  fba_tier_old?: string
  fba_tier_new?: string
  fulfillment_saving_usd_per_unit?: number
}

export interface EvidenceImage {
  image_id: string
  storage_url: string
  defect_category: DefectCategory
  confidence: number
}

export interface ProposalEvidenceReview {
  review_id: string
  rating: number
  review_date: string
  language: string
  content: string
  translated_content: string
  highlight_keywords: string[]
  images: EvidenceImage[]
}

export interface ProposalEvidence {
  proposal_id: string
  total: number
  reviews: ProposalEvidenceReview[]
}

/* ---------- 财务风控 ---------- */

export interface FinancialSimulateRequest {
  mold_cost_usd: number
  moq: number
  current_gross_margin: number
  expected_price_usd: number
  unit_cost_increase_usd: number
  expected_payback_months: number
  sea_freight_usd_per_cbm: number
  package_size_old_cm: [number, number, number]
  package_size_new_cm: [number, number, number]
  expected_return_rate_reduction: number
  product_lifecycle_days: number
}

export interface PaybackPoint {
  return_rate_reduction: number
  payback_months: number
}

export interface FinancialSimulateResult {
  volumetric_weight_old_kg: number
  volumetric_weight_new_kg: number
  fba_tier_old: string
  fba_tier_new: string
  fulfillment_saving_usd_per_unit: number
  monthly_profit_delta_usd: number
  payback_months: number
  roi: number
  veto_status: 'PASSED' | 'VETOED'
  veto_reasons: string[]
  fallback_suggestions: string[]
  payback_curve: PaybackPoint[]
}

export interface FinancialDecision {
  task_id: string
  veto_status: 'PASSED' | 'VETOED'
  checked_proposals: number
  vetoed_proposal_ids: string[]
  veto_reasons: string[]
  fallback_applied: boolean
  retry_count: number
  financial_constraint: FinancialConstraint
}

/* ---------- 扩展（P2 预留） ---------- */

export interface Alert {
  alert_id: string
  type: 'price_movement' | 'buy_box' | 'supply_chain' | 'veto'
  severity: 'high' | 'medium' | 'low'
  title: string
  message: string
  related_product_id: string | null
  related_task_id: string | null
  is_read: boolean
  created_at: string
}

export interface CrossPlatformMapping {
  product_id: string
  asin: string
  amazon_price_usd: number
  matches: {
    platform: string
    external_sku: string
    title: string
    price_usd: number
    match_score: number
    commission_usd: number
    fulfillment_usd: number
  }[]
  max_price_gap_usd: number
}

export interface BacktestResult {
  backtest_id: string
  task_id: string
  slice_date: string
  status: string
  accuracy_score: number
  cluster_verdicts: {
    cluster_id: string
    cluster_name: string
    hit: boolean
    actual_trend: string
  }[]
}
