export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: 'owner' | 'pm' | 'supply_chain';
  roleName: string;
  avatar?: string;
}

export type Marketplace = 'US' | 'DE' | 'JP' | 'UK';

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'vetoed';

export type AgentNode =
  | 'ingestion'
  | 'clustering'
  | 'vlm_inspection'
  | 'dual_column_proposal'
  | 'financial_veto';

export interface TaskNodeInfo {
  key: AgentNode;
  name: string;
  desc: string;
  status: 'idle' | 'running' | 'completed' | 'failed' | 'vetoed';
  durationMs?: number;
  outputSummary?: string;
}

export interface InsightTask {
  id: string;
  asin: string;
  productTitle: string;
  marketplace: Marketplace;
  brand: string;
  currentPrice: number;
  bsr: number;
  category: string;
  status: TaskStatus;
  progress: number;
  currentNode: AgentNode;
  nodes: TaskNodeInfo[];
  createdAt: string;
  completedAt?: string;
  reviewCount: number;
  negativeRate: number;
  vetoTriggered?: boolean;
}

export interface PainPointCluster {
  id: string;
  name: string;
  category: '结构强度' | '热工与材质' | '材质升级' | '规格公差' | '表面处理' | '包装与履约';
  frequency: number;
  severity: number; // 1 to 5
  shareRatio: number; // 0 to 1
  sampleQuote: string;
  translatedQuote: string;
  reviewIds: string[];
  photoCount: number;
}

export interface VisualEvidence {
  id: string;
  asin: string;
  title: string;
  imageUrl: string;
  defectType: string;
  confidence: number;
  damagedPart: string;
  rootCause: string;
  reviewRating: number;
  reviewDate: string;
  reviewText: string;
  bbox?: { x: number; y: number; w: number; h: number };
}

export interface PhysicalProposal {
  id: string;
  title: string;
  targetClusterId: string;
  targetClusterName: string;
  category: '材质升级' | '结构防呆' | '模具公差' | '散热设计';
  problemStatement: string;
  actionPlan: string;
  engineeringSpec: string;
  costDeltaUsd: number;
  leadTimeDays: number;
  evidenceCount: number;
  photoCount: number;
}

export interface PackagingProposal {
  id: string;
  title: string;
  targetClusterId: string;
  targetClusterName: string;
  category: '尺寸降阶 (Tier Down)' | '抗摔缓冲' | '防呆说明书' | '环保包材';
  problemStatement: string;
  actionPlan: string;
  engineeringSpec: string;
  fbaSavingsPerUnit: number;
  leadTimeDays: number;
  annualSavingsUsd: number;
  evidenceCount: number;
}

export interface FinancialSimulationResult {
  moldCostUsd: number;
  moq: number;
  unitPriceUsd: number;
  baseMargin: number; // 0-1
  targetPaybackMonths: number;
  fbaSavingsPerUnit: number;
  amortizedMoldPerUnit: number;
  projectedMargin: number;
  breakevenUnits: number;
  calculatedPaybackMonths: number;
  isVetoed: boolean;
  vetoReasons: string[];
  downgradeRecommendation: string;
  backtestAccuracy: number;
}
