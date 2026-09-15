/**
 * InsightX REST wire contracts.
 *
 * Keep this file in lockstep with `backend/src/insightx/schemas.py`.
 * Field names intentionally remain snake_case because these are network DTOs.
 */

export type TaskStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELED'
export type DataQuality = 'SUFFICIENT' | 'PARTIAL' | 'NO_DATA'
export type FinancialState = 'NOT_EVALUATED' | 'PASSED' | 'VETOED'
export type NodeStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'SKIPPED' | 'FAILED' | 'CANCELED'
export type EvidenceSourceType = 'REVIEW_TEXT' | 'CLEANED_FRAGMENT' | 'METADATA'
export type ProposalColumn =
  | 'PRODUCT_OPTIMIZATION'
  | 'PACKAGING_FULFILLMENT_OPTIMIZATION'

export interface HealthResponse {
  status: 'ok' | 'degraded'
  version: string
  db: boolean
  redis: boolean
}

export interface TaskWindow {
  preset: '1m' | '3m' | '6m'
}

export interface TaskCreateRequest {
  asins: string[]
  platform: 'amazon'
  marketplace: 'US'
  window: TaskWindow
}

export interface RetryTaskRequest {
  item_ids: string[]
}

export interface TaskCreatedItem {
  item_id: string
  asin: string
  status: TaskStatus
}

export interface TaskCreatedResponse {
  task_id: string
  status: TaskStatus
  reused: boolean
  parent_task_id: string | null
  created_at: string
  items: TaskCreatedItem[]
}

export interface TaskListItem {
  task_id: string
  status: TaskStatus
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

export interface TaskError {
  code: string
  message: string
  retryable: boolean
}

export interface SampleMetrics {
  raw_review_count: number
  valid_review_count: number
  excluded_review_count: number
  average_rating: number | null
  negative_review_ratio: number | null
  pain_point_count_with_evidence: number
  window: Record<string, unknown>
  methodology: string
  missing_reasons: string[]
}

export interface NodeProgress {
  node_id: string
  node_name: string
  status: NodeStatus
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
  skip_reason: string | null
  error: TaskError | null
}

export interface TaskItemSnapshot {
  item_id: string
  asin: string
  status: TaskStatus
  current_node: string | null
  attempt: number
  data_quality: DataQuality | null
  sample_metrics: SampleMetrics | null
  nodes: NodeProgress[]
  error: TaskError | null
  report_available: boolean
}

export interface TaskProgress {
  total_items: number
  finished_items: number
}

export interface TaskSnapshot extends TaskListItem {
  parent_task_id: string | null
  cancel_requested_at: string | null
  finished_at: string | null
  items: TaskItemSnapshot[]
  progress: TaskProgress
}

export interface ReportPainPoint {
  pain_point_id: string
  label: string
  actual_frequency: number
  frequency_methodology: string
  severity_score: number
  severity_rationale: string
  severity_level: 'CRITICAL' | 'MODERATE' | 'MINOR'
  summary: string
  evidence_refs: string[]
  typical_evidence_refs: string[]
}

export interface ReportProposal {
  proposal_id: string
  column: ProposalColumn
  title: string
  change_description: string
  pain_point_ids: string[]
  snapshot_ref: string
  evidence_refs: string[]
}

export interface ReportWarning {
  code: string
  message: string
  related_item_id?: string | null
  evidence_refs?: string[] | null
}

export interface ReportResponse {
  report_id: string
  task_id: string
  item_id: string
  asin: string
  data_quality: DataQuality
  sample_metrics: SampleMetrics
  generated_at: string
  financial_state: FinancialState
  pain_points: ReportPainPoint[]
  proposals: ReportProposal[]
  warnings: ReportWarning[]
  model_metadata: Record<string, unknown>
}

export interface EvidenceResponse {
  evidence_id: string
  source_type: EvidenceSourceType
  source_ref: string
  excerpt: string
  source_url: string | null
  published_at: string | null
  metadata: Record<string, unknown>
  provenance: Record<string, unknown>
}

export interface Page<T> {
  items: T[]
  next_cursor: string | null
}

export interface ListTasksParams {
  status?: TaskStatus
  cursor?: string
  limit?: number
}

export interface ListEvidenceParams {
  claim_id?: string
  source_type?: EvidenceSourceType
  cursor?: string
  limit?: number
}

export function isTerminalTaskStatus(status: TaskStatus | null | undefined): boolean {
  return status === 'COMPLETED' || status === 'FAILED' || status === 'CANCELED'
}

export interface FinancialEvaluateRequest {
  mold_cost?: number | null
  sample_cost?: number | null
  moq?: number | null
  unit_product_cost?: number | null
  expected_sales_price?: number | null
  shipping_cost_per_unit?: number | null
  monthly_estimated_sales?: number | null
  target_payback_months?: number
  category_half_life_months?: number
  max_cash_budget?: number | null
  currency?: 'USD'
  rule_version?: string
  task_id?: string | null
  item_id?: string | null
}

export interface FinancialMetrics {
  fixed_costs: number
  variable_cost_per_unit: number
  unit_contribution_margin: number
  gross_margin_rate: number
  initial_batch_cash: number
  amortized_mold_cost_per_unit: number
  mold_cost_ratio: number
  monthly_contribution: number
  break_even_units: number | null
  payback_months: number
  estimated_12m_roi: number
}

export interface BreakEvenPoint {
  month: number
  cumulative_units: number
  cumulative_revenue: number
  cumulative_cost: number
  net_cashflow: number
  is_break_even: boolean
}

export interface SensitivityPoint {
  sales_change_percent: number
  price_change_percent: number
  payback_months: number
  is_vetoed: boolean
}

export interface AlternativeSuggestion {
  suggestion_id: string
  title: string
  description: string
  estimated_impact: string
  suggested_params: Partial<FinancialEvaluateRequest>
}

export interface FinancialEvaluateResponse {
  financial_state: FinancialState
  circuit_breaker_triggered: boolean
  rule_version: string
  currency: string
  evaluated_at: string
  reasons: string[]
  triggered_rules: string[]
  metrics: FinancialMetrics | null
  break_even_timeline: BreakEvenPoint[]
  sensitivity_matrix: SensitivityPoint[]
  alternative_suggestions: AlternativeSuggestion[]
  applied_assumptions: Record<string, unknown>
}

export interface FinancialRuleItem {
  code: string
  name: string
  description: string
  threshold: string
}

export interface FinancialRuleInfo {
  rule_version: string
  rules: FinancialRuleItem[]
}

