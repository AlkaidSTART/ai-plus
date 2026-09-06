import type {
  Alert,
  BacktestResult,
  Cluster,
  CrossPlatformMapping,
  DashboardOverview,
  FinancialDecision,
  FinancialSimulateRequest,
  FinancialSimulateResult,
  Product,
  Proposal,
  ProposalEvidence,
  Recommendation,
  Review,
  Task,
  TaskStep,
  VisualEvidence,
} from '../types'

/** 本地 SVG 占位图（data URI，离线可用；不同 seed 生成不同渐变色） */
export function img(seed: number, w = 480, h = 360): string {
  const hue = (seed * 47) % 360
  const hue2 = (hue + 40) % 360
  const r = Math.min(w, h)
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">` +
    `<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">` +
    `<stop offset="0" stop-color="hsl(${hue} 72% 64%)"/>` +
    `<stop offset="1" stop-color="hsl(${hue2} 78% 46%)"/>` +
    `</linearGradient></defs>` +
    `<rect width="100%" height="100%" fill="url(#g)"/>` +
    `<circle cx="${Math.round(w * 0.78)}" cy="${Math.round(h * 0.22)}" r="${Math.round(r * 0.2)}" fill="rgba(255,255,255,0.18)"/>` +
    `<circle cx="${Math.round(w * 0.18)}" cy="${Math.round(h * 0.82)}" r="${Math.round(r * 0.26)}" fill="rgba(255,255,255,0.12)"/>` +
    `<text x="50%" y="54%" text-anchor="middle" font-family="Arial, sans-serif" font-size="${Math.round(r * 0.09)}" font-weight="bold" fill="rgba(255,255,255,0.94)">InsightX</text>` +
    `<text x="50%" y="66%" text-anchor="middle" font-family="Arial, sans-serif" font-size="${Math.round(r * 0.055)}" fill="rgba(255,255,255,0.72)">#${seed}</text>` +
    `</svg>`
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

/* ---------------- 竞品 ---------------- */

export const mockProducts: Product[] = [
  {
    product_id: '0d1f3a5e-0001',
    asin: 'B0C1234ABC',
    platform: 'amazon',
    marketplace: 'US',
    title: 'LED Desk Lamp Pro 护眼台灯',
    category: 'Home & Kitchen',
    current_price: 29.99,
    currency: 'USD',
    main_image_url: img(101),
    review_count: 318,
    avg_rating: 4.1,
    bsr: 1240,
    bsr_category: '#1 in Desk Lamps',
    length_cm: 30,
    width_cm: 20,
    height_cm: 12,
    weight_kg: 1.2,
    created_at: '2026-06-01T08:00:00Z',
    updated_at: '2026-09-05T06:00:00Z',
  },
  {
    product_id: '0d1f3a5e-0002',
    asin: 'B0D88X2YWZ',
    platform: 'amazon',
    marketplace: 'US',
    title: 'Ultrasonic Humidifier 超声波加湿器 2.5L',
    category: 'Home & Kitchen',
    current_price: 39.5,
    currency: 'USD',
    main_image_url: img(102),
    review_count: 256,
    avg_rating: 3.9,
    bsr: 2310,
    bsr_category: '#3 in Humidifiers',
    length_cm: 18,
    width_cm: 18,
    height_cm: 25,
    weight_kg: 1.05,
    created_at: '2026-06-10T08:00:00Z',
    updated_at: '2026-09-05T06:00:00Z',
  },
  {
    product_id: '0d1f3a5e-0003',
    asin: 'B0E5XQ2MNP',
    platform: 'amazon',
    marketplace: 'DE',
    title: 'Faltbare LED-Schreibtischlampe 折叠台灯',
    category: 'Home & Kitchen',
    current_price: 34.99,
    currency: 'EUR',
    main_image_url: img(103),
    review_count: 142,
    avg_rating: 3.5,
    bsr: 890,
    bsr_category: '#2 in Schreibtischlampen',
    length_cm: 32,
    width_cm: 18,
    height_cm: 10,
    weight_kg: 1.1,
    created_at: '2026-07-02T08:00:00Z',
    updated_at: '2026-09-05T06:00:00Z',
  },
  {
    product_id: '0d1f3a5e-0004',
    asin: 'B0F7KZ9PQC',
    platform: 'amazon',
    marketplace: 'US',
    title: '20000mAh Magnetic Power Bank 磁吸充电宝',
    category: 'Electronics',
    current_price: 45.99,
    currency: 'USD',
    main_image_url: img(104),
    review_count: 521,
    avg_rating: 4.4,
    bsr: 512,
    bsr_category: '#5 in Power Banks',
    length_cm: 11,
    width_cm: 7,
    height_cm: 2.2,
    weight_kg: 0.34,
    created_at: '2026-06-20T08:00:00Z',
    updated_at: '2026-09-05T06:00:00Z',
  },
  {
    product_id: '0d1f3a5e-0005',
    asin: 'B0G2WTR7KD',
    platform: 'amazon',
    marketplace: 'JP',
    title: 'ポータブル扇風機 便携小风扇 USB',
    category: 'Home & Kitchen',
    current_price: 22.99,
    currency: 'USD',
    main_image_url: img(105),
    review_count: 189,
    avg_rating: 3.7,
    bsr: 1420,
    bsr_category: '#4 in 扇風機',
    length_cm: 20,
    width_cm: 9,
    height_cm: 9,
    weight_kg: 0.42,
    created_at: '2026-07-15T08:00:00Z',
    updated_at: '2026-09-05T06:00:00Z',
  },
  {
    product_id: '0d1f3a5e-0006',
    asin: 'B0H3XK5VFB',
    platform: 'amazon',
    marketplace: 'US',
    title: 'Cordless Handheld Vacuum 无线手持吸尘器',
    category: 'Home & Kitchen',
    current_price: 59.99,
    currency: 'USD',
    main_image_url: img(106),
    review_count: 402,
    avg_rating: 4.0,
    bsr: 780,
    bsr_category: '#2 in Handheld Vacuums',
    length_cm: 45,
    width_cm: 15,
    height_cm: 15,
    weight_kg: 1.6,
    created_at: '2026-06-25T08:00:00Z',
    updated_at: '2026-09-05T06:00:00Z',
  },
]

/* ---------------- 评论 ---------------- */

export const mockReviews: Review[] = [
  {
    review_id: 'rev_88c2a1',
    rating: 1.0,
    review_date: '2026-03-12',
    language: 'de',
    title: 'Griff nach einer Woche gebrochen',
    content: 'Der Griff ist nach einer Woche gebrochen. Das Material fühlt sich sehr billig an, das Gelenk wackelt bereits.',
    translated_content: '把手一周后就断了。材质感觉很廉价，转轴已经在摇晃。',
    verified_purchase: true,
    helpful_votes: 12,
    image_urls: [img(201), img(202)],
    cluster_ids: ['clu_01'],
  },
  {
    review_id: 'rev_88c2a2',
    rating: 2.0,
    review_date: '2026-04-02',
    language: 'en',
    title: 'Handle cracked within a month',
    content: 'The ABS handle cracked at the base after daily use. Stress concentration at the joint.',
    translated_content: 'ABS 把手在日常使用一个月后在根部开裂，连接处存在应力集中。',
    verified_purchase: true,
    helpful_votes: 8,
    image_urls: [img(203)],
    cluster_ids: ['clu_01'],
  },
  {
    review_id: 'rev_88c2a3',
    rating: 1.0,
    review_date: '2026-04-18',
    language: 'en',
    title: 'Flickering after 2 weeks',
    content: 'The LED starts flickering after two weeks of use. The dimmer switch feels loose and inconsistent.',
    translated_content: 'LED 使用两周后开始闪烁，调光开关松垮、不线性。',
    verified_purchase: true,
    helpful_votes: 15,
    image_urls: [],
    cluster_ids: ['clu_02'],
  },
  {
    review_id: 'rev_88c2a4',
    rating: 1.0,
    review_date: '2026-05-06',
    language: 'en',
    title: 'Damaged in transit, box crushed',
    content: 'Box arrived completely crushed. The lamp head was scratched and the packaging foam did nothing.',
    translated_content: '外箱到货时完全压扁。灯头被刮花，包装泡沫毫无缓冲作用。',
    verified_purchase: true,
    helpful_votes: 6,
    image_urls: [img(204), img(205)],
    cluster_ids: ['clu_03'],
  },
  {
    review_id: 'rev_88c2a5',
    rating: 2.0,
    review_date: '2026-05-21',
    language: 'ja',
    title: '説明書が分かりにくい',
    content: '組み立て説明書が分かりにくく、ネジの向きを間違えた。専用の六角レンチが入っていない。',
    translated_content: '组装说明书晦涩难懂，螺丝方向装错了。而且没有附带专用六角扳手。',
    verified_purchase: true,
    helpful_votes: 4,
    image_urls: [],
    cluster_ids: ['clu_05'],
  },
  {
    review_id: 'rev_88c2a6',
    rating: 1.0,
    review_date: '2026-06-09',
    language: 'de',
    title: 'Gelenk bricht nach 3 Wochen',
    content: 'Das Scharnier bricht nach 3 Wochen, die Höhenverstellung klemmt und knackt.',
    translated_content: '转轴三周后断裂，高度调节卡滞且有异响。',
    verified_purchase: true,
    helpful_votes: 9,
    image_urls: [img(206)],
    cluster_ids: ['clu_01'],
  },
  {
    review_id: 'rev_88c2a7',
    rating: 3.0,
    review_date: '2026-06-22',
    language: 'es',
    title: 'Buen diseño, mala calidad del cable',
    content: 'El diseño es bonito pero el cable de alimentación se calienta demasiado y el conector es frágil.',
    translated_content: '设计漂亮但电源线过热，接头很脆弱。',
    verified_purchase: true,
    helpful_votes: 3,
    image_urls: [],
    cluster_ids: ['clu_04'],
  },
  {
    review_id: 'rev_88c2a8',
    rating: 2.0,
    review_date: '2026-07-03',
    language: 'en',
    title: 'Base wobbles on desk',
    content: 'The base is too light, wobbles on the desk, and the rubber pad peels off after a week.',
    translated_content: '底座太轻，桌面放不稳，防滑垫一周后就脱落了。',
    verified_purchase: true,
    helpful_votes: 5,
    image_urls: [img(207)],
    cluster_ids: ['clu_04'],
  },
  {
    review_id: 'rev_88c2a9',
    rating: 1.0,
    review_date: '2026-07-14',
    language: 'en',
    title: 'Color differs from listing photos',
    content: 'The "warm white" mode looks yellow-green, totally different from the listing photos. Definite color difference.',
    translated_content: '“暖白”档位偏黄绿，与主图完全不同，明显色差。',
    verified_purchase: true,
    helpful_votes: 11,
    image_urls: [img(208)],
    cluster_ids: ['clu_06'],
  },
  {
    review_id: 'rev_88c2b0',
    rating: 2.0,
    review_date: '2026-07-28',
    language: 'en',
    title: 'USB-C port loose',
    content: 'The USB-C port is loose, the charging cable falls out easily. Wiring inside seems rushed.',
    translated_content: 'USB-C 接口松动，充电线容易脱落，内部走线很随意。',
    verified_purchase: true,
    helpful_votes: 7,
    image_urls: [],
    cluster_ids: ['clu_04'],
  },
]

/* ---------------- 痛点聚类 ---------------- */

export const mockClusters: Cluster[] = [
  {
    cluster_id: 'clu_01',
    cluster_name: '把手/转轴易断裂',
    issue_type: 'product_defect',
    frequency: 128,
    frequency_ratio: 0.34,
    severity_score: 4.6,
    severity_level: 'critical',
    keywords: ['broke', 'handle', 'crack', 'Gelenk', 'Griff'],
    sample_quotes: [
      {
        review_id: 'rev_88c2a1',
        language: 'de',
        content: 'Der Griff ist nach einer Woche gebrochen...',
        translated_content: '把手一周后就断了……',
        rating: 1.0,
      },
      {
        review_id: 'rev_88c2a2',
        language: 'en',
        content: 'The ABS handle cracked at the base after daily use.',
        translated_content: 'ABS 把手在日常使用后在根部开裂。',
        rating: 2.0,
      },
    ],
    sample_image_ids: ['img_a1', 'img_a2'],
  },
  {
    cluster_id: 'clu_02',
    cluster_name: 'LED 频闪与调光失灵',
    issue_type: 'function_defect',
    frequency: 76,
    frequency_ratio: 0.2,
    severity_score: 4.1,
    severity_level: 'critical',
    keywords: ['flicker', 'dimmer', 'LED'],
    sample_quotes: [
      {
        review_id: 'rev_88c2a3',
        language: 'en',
        content: 'The LED starts flickering after two weeks of use.',
        translated_content: 'LED 使用两周后开始闪烁。',
        rating: 1.0,
      },
    ],
    sample_image_ids: [],
  },
  {
    cluster_id: 'clu_03',
    cluster_name: '运输破损与包装缓冲不足',
    issue_type: 'packaging_delivery',
    frequency: 54,
    frequency_ratio: 0.14,
    severity_score: 3.8,
    severity_level: 'moderate',
    keywords: ['crushed', 'damaged', 'box', 'transit'],
    sample_quotes: [
      {
        review_id: 'rev_88c2a4',
        language: 'en',
        content: 'Box arrived completely crushed...',
        translated_content: '外箱到货时完全压扁……',
        rating: 1.0,
      },
    ],
    sample_image_ids: ['img_a3'],
  },
  {
    cluster_id: 'clu_04',
    cluster_name: '结构松动与接口脆弱',
    issue_type: 'function_defect',
    frequency: 43,
    frequency_ratio: 0.11,
    severity_score: 3.2,
    severity_level: 'moderate',
    keywords: ['wobble', 'loose', 'port', 'cable'],
    sample_quotes: [
      {
        review_id: 'rev_88c2a8',
        language: 'en',
        content: 'The base is too light, wobbles on the desk...',
        translated_content: '底座太轻，桌面放不稳……',
        rating: 2.0,
      },
    ],
    sample_image_ids: [],
  },
  {
    cluster_id: 'clu_05',
    cluster_name: '说明书与配件不齐全',
    issue_type: 'manual',
    frequency: 31,
    frequency_ratio: 0.08,
    severity_score: 2.8,
    severity_level: 'moderate',
    keywords: ['manual', '説明書', 'hex key', 'screw'],
    sample_quotes: [
      {
        review_id: 'rev_88c2a5',
        language: 'ja',
        content: '組み立て説明書が分かりにくく...',
        translated_content: '组装说明书晦涩难懂……',
        rating: 2.0,
      },
    ],
    sample_image_ids: [],
  },
  {
    cluster_id: 'clu_06',
    cluster_name: '色差与光色偏差',
    issue_type: 'product_defect',
    frequency: 28,
    frequency_ratio: 0.07,
    severity_score: 2.6,
    severity_level: 'moderate',
    keywords: ['color', 'difference', 'warm white'],
    sample_quotes: [
      {
        review_id: 'rev_88c2a9',
        language: 'en',
        content: 'The "warm white" mode looks yellow-green...',
        translated_content: '“暖白”档位偏黄绿……',
        rating: 1.0,
      },
    ],
    sample_image_ids: ['img_a4'],
  },
]

/* ---------------- 取证 ---------------- */

export const mockEvidences: VisualEvidence[] = [
  {
    image_id: 'img_a1',
    review_id: 'rev_88c2a1',
    storage_url: img(301, 640, 480),
    defect_category: 'craft_flaw',
    description: '把手根部应力集中处断裂，断口平整，疑为模具公差或材质强度不足',
    confidence: 0.92,
    bbox: [120, 80, 420, 360],
    cluster_ids: ['clu_01'],
  },
  {
    image_id: 'img_a2',
    review_id: 'rev_88c2a6',
    storage_url: img(302, 640, 480),
    defect_category: 'craft_flaw',
    description: '转轴关节处开裂，轴孔壁厚不足，存在拔模斜度缺失',
    confidence: 0.88,
    bbox: [200, 150, 380, 330],
    cluster_ids: ['clu_01'],
  },
  {
    image_id: 'img_a3',
    review_id: 'rev_88c2a4',
    storage_url: img(303, 640, 480),
    defect_category: 'broken_package',
    description: '外箱角部塌陷，泡沫缓冲层过薄导致灯头刮花',
    confidence: 0.95,
    bbox: [60, 40, 300, 260],
    cluster_ids: ['clu_03'],
  },
  {
    image_id: 'img_a4',
    review_id: 'rev_88c2a9',
    storage_url: img(304, 640, 480),
    defect_category: 'color_difference',
    description: '暖白档位实测色温偏黄绿，与 listing 主图存在明显色差',
    confidence: 0.81,
    bbox: [180, 120, 460, 400],
    cluster_ids: ['clu_06'],
  },
  {
    image_id: 'img_a5',
    review_id: 'rev_88c2a2',
    storage_url: img(305, 640, 480),
    defect_category: 'craft_flaw',
    description: '把手根部裂纹沿应力线扩展，ABS 材料韧性不足',
    confidence: 0.9,
    bbox: [140, 90, 400, 350],
    cluster_ids: ['clu_01'],
  },
]

/* ---------------- 双栏改款 ---------------- */

export const mockProposals: Proposal[] = [
  {
    proposal_id: 'prp_5b7e01',
    task_id: 'tsk_9f2c81a4',
    track_type: 'BODY_OPTIMIZATION',
    title: '替换把手材质为阻燃 PC 并增加防呆卡扣',
    description:
      '针对 34% 断裂差评，将 ABS 把手替换为玻纤增强 PC，卡扣处增加 0.5mm 防呆结构，拔模斜度修正至 2°，消除根部应力集中。',
    cost_estimation_usd: 8500,
    mold_opening_required: true,
    mold_cycle_days: 60,
    estimated_roi: 2.4,
    defect_rate_reduction: 0.62,
    status: 'PASSED',
    veto_reason: null,
    fallback_applied: false,
    source_cluster_ids: ['clu_01'],
    evidence_review_count: 42,
    evidence_image_count: 8,
    created_at: '2026-09-05T08:01:40Z',
  },
  {
    proposal_id: 'prp_5b7e02',
    task_id: 'tsk_9f2c81a4',
    track_type: 'BODY_OPTIMIZATION',
    title: '驱动板改款：恒流驱动 + 无频闪调光模块',
    description:
      'LED 频闪投诉 20%，升级恒流 PWM 驱动方案，调光档位改为线性旋钮，杜绝低频闪动。',
    cost_estimation_usd: 12000,
    mold_opening_required: true,
    mold_cycle_days: 45,
    estimated_roi: 1.8,
    defect_rate_reduction: 0.55,
    status: 'PASSED',
    veto_reason: null,
    fallback_applied: false,
    source_cluster_ids: ['clu_02'],
    evidence_review_count: 31,
    evidence_image_count: 2,
    created_at: '2026-09-05T08:01:45Z',
  },
  {
    proposal_id: 'prp_5b7e03',
    task_id: 'tsk_9f2c81a4',
    track_type: 'BODY_OPTIMIZATION',
    title: '底座加重 + 防滑垫一体注塑',
    description:
      '底座重量增加 40%，防滑垫改为 TPE 一体注塑，消除桌面晃动与垫片脱落问题。',
    cost_estimation_usd: 15000,
    mold_opening_required: true,
    mold_cycle_days: 70,
    estimated_roi: 1.2,
    defect_rate_reduction: 0.48,
    status: 'VETOED',
    veto_reason: '开模回收期长达 14 个月，已超出该品类 6 个月生命周期，建议走免开模替代方案',
    fallback_applied: true,
    source_cluster_ids: ['clu_04'],
    evidence_review_count: 18,
    evidence_image_count: 1,
    created_at: '2026-09-05T08:02:10Z',
  },
  {
    proposal_id: 'prp_5b7e04',
    task_id: 'tsk_9f2c81a4',
    track_type: 'PACKAGING_FULFILLMENT',
    title: '外箱尺寸降阶 + 蜂窝纸板缓冲升级',
    description:
      '外箱从 30×20×12cm 压缩至 26×18×9cm，缓冲换蜂窝纸板，灯头区加防护垫块，破损率预期下降 70%。',
    cost_estimation_usd: 2000,
    mold_opening_required: false,
    mold_cycle_days: 0,
    estimated_roi: 3.1,
    defect_rate_reduction: 0.7,
    status: 'PASSED',
    veto_reason: null,
    fallback_applied: false,
    source_cluster_ids: ['clu_03'],
    evidence_review_count: 24,
    evidence_image_count: 5,
    created_at: '2026-09-05T08:02:20Z',
    package_size_old_cm: [30, 20, 12],
    package_size_new_cm: [26, 18, 9],
    volumetric_weight_old_kg: 1.44,
    volumetric_weight_new_kg: 0.84,
    fba_tier_old: 'Large Standard',
    fba_tier_new: 'Small Standard',
    fulfillment_saving_usd_per_unit: 1.35,
  },
  {
    proposal_id: 'prp_5b7e05',
    task_id: 'tsk_9f2c81a4',
    track_type: 'PACKAGING_FULFILLMENT',
    title: '多语言快速指南 + 随机附赠六角扳手',
    description:
      '重做 5 语种图文说明书（德/日/西/法/英），附赠磁吸六角扳手，降低组装差评率。',
    cost_estimation_usd: 800,
    mold_opening_required: false,
    mold_cycle_days: 0,
    estimated_roi: 4.2,
    defect_rate_reduction: 0.35,
    status: 'PASSED',
    veto_reason: null,
    fallback_applied: false,
    source_cluster_ids: ['clu_05'],
    evidence_review_count: 12,
    evidence_image_count: 0,
    created_at: '2026-09-05T08:02:30Z',
  },
]

export const mockProposalEvidence: Record<string, ProposalEvidence> = {
  prp_5b7e01: {
    proposal_id: 'prp_5b7e01',
    total: 2,
    reviews: [
      {
        review_id: 'rev_88c2a1',
        rating: 1.0,
        review_date: '2026-03-12',
        language: 'de',
        content: 'Der Griff ist nach einer Woche gebrochen. Das Material fühlt sich sehr billig an, das Gelenk wackelt bereits.',
        translated_content: '把手一周后就断了。材质感觉很廉价，转轴已经在摇晃。',
        highlight_keywords: ['gebrochen', 'Griff'],
        images: [
          { image_id: 'img_a1', storage_url: img(301, 320, 240), defect_category: 'craft_flaw', confidence: 0.92 },
        ],
      },
      {
        review_id: 'rev_88c2a2',
        rating: 2.0,
        review_date: '2026-04-02',
        language: 'en',
        content: 'The ABS handle cracked at the base after daily use. Stress concentration at the joint.',
        translated_content: 'ABS 把手在日常使用一个月后在根部开裂，连接处存在应力集中。',
        highlight_keywords: ['cracked', 'handle'],
        images: [
          { image_id: 'img_a5', storage_url: img(305, 320, 240), defect_category: 'craft_flaw', confidence: 0.9 },
        ],
      },
    ],
  },
  prp_5b7e04: {
    proposal_id: 'prp_5b7e04',
    total: 1,
    reviews: [
      {
        review_id: 'rev_88c2a4',
        rating: 1.0,
        review_date: '2026-05-06',
        language: 'en',
        content: 'Box arrived completely crushed. The lamp head was scratched and the packaging foam did nothing.',
        translated_content: '外箱到货时完全压扁。灯头被刮花，包装泡沫毫无缓冲作用。',
        highlight_keywords: ['crushed', 'packaging'],
        images: [
          { image_id: 'img_a3', storage_url: img(303, 320, 240), defect_category: 'broken_package', confidence: 0.95 },
        ],
      },
    ],
  },
}

/* ---------------- 任务 ---------------- */

export const mockTasks: Task[] = [
  {
    task_id: 'tsk_9f2c81a4',
    asin: 'B0C1234ABC',
    product_id: '0d1f3a5e-0001',
    platform: 'amazon',
    marketplace: 'US',
    status: 'COMPLETED',
    current_node: 'COMPLETED',
    progress: 100,
    retry_count: 1,
    financial_constraint: {
      mold_cost_usd: 8000,
      moq: 1000,
      current_gross_margin: 0.32,
      expected_price_usd: 29.99,
      unit_cost_increase_usd: 1.8,
      expected_payback_months: 6,
      sea_freight_usd_per_cbm: 180,
    },
    summary: {
      review_count: 318,
      cluster_count: 6,
      proposal_count: 5,
      veto_status: 'PASSED',
      backtest_score: null,
    },
    error_message: null,
    created_at: '2026-09-05T08:00:00Z',
    started_at: '2026-09-05T08:00:03Z',
    finished_at: '2026-09-05T08:00:52Z',
  },
  {
    task_id: 'tsk_3f7d92bc',
    asin: 'B0D88X2YWZ',
    product_id: '0d1f3a5e-0002',
    platform: 'amazon',
    marketplace: 'US',
    status: 'RUNNING',
    current_node: 'semantic_cluster',
    progress: 58,
    retry_count: 0,
    financial_constraint: {
      mold_cost_usd: 12000,
      moq: 800,
      current_gross_margin: 0.28,
      expected_price_usd: 39.5,
      unit_cost_increase_usd: 2.2,
      expected_payback_months: 8,
      sea_freight_usd_per_cbm: 180,
    },
    summary: { review_count: 256, cluster_count: 3, proposal_count: 0, veto_status: 'PENDING', backtest_score: null },
    error_message: null,
    created_at: '2026-09-05T09:12:00Z',
    started_at: '2026-09-05T09:12:05Z',
    finished_at: null,
  },
  {
    task_id: 'tsk_7a1e03fd',
    asin: 'B0E5XQ2MNP',
    product_id: '0d1f3a5e-0003',
    platform: 'amazon',
    marketplace: 'DE',
    status: 'FAILED',
    current_node: 'FETCHING_DATA',
    progress: 12,
    retry_count: 2,
    financial_constraint: {
      mold_cost_usd: 8000,
      moq: 1000,
      current_gross_margin: 0.3,
      expected_price_usd: 34.99,
      unit_cost_increase_usd: 1.5,
      expected_payback_months: 6,
      sea_freight_usd_per_cbm: 200,
    },
    summary: null,
    error_message: '亚马逊反爬限频触发，指数退避重试 3 次仍失败',
    created_at: '2026-09-05T09:20:00Z',
    started_at: '2026-09-05T09:20:03Z',
    finished_at: '2026-09-05T09:20:40Z',
  },
  {
    task_id: 'tsk_c4d8e9f0',
    asin: 'B0F7KZ9PQC',
    product_id: '0d1f3a5e-0004',
    platform: 'amazon',
    marketplace: 'US',
    status: 'PENDING',
    current_node: 'QUEUED',
    progress: 0,
    retry_count: 0,
    financial_constraint: {
      mold_cost_usd: 5000,
      moq: 2000,
      current_gross_margin: 0.4,
      expected_price_usd: 45.99,
      unit_cost_increase_usd: 1.2,
      expected_payback_months: 5,
      sea_freight_usd_per_cbm: 180,
    },
    summary: null,
    error_message: null,
    created_at: '2026-09-05T09:30:00Z',
    started_at: null,
    finished_at: null,
  },
]

/* ---------------- 大盘 ---------------- */

export const mockOverview: DashboardOverview = {
  monitored_product_count: 12,
  running_task_count: 2,
  pain_point_cluster_count: 23,
  fba_saving_pool_usd: 42800.0,
  veto_triggered_count: 3,
  avg_rating: 4.1,
  negative_review_rate: 0.18,
}

export const mockRecommendations: Recommendation[] = [
  {
    task_id: 'tsk_9f2c81a4',
    product_id: '0d1f3a5e-0001',
    asin: 'B0C1234ABC',
    title: 'LED Desk Lamp Pro 护眼台灯',
    main_image_url: img(101),
    estimated_roi: 2.4,
    return_rate_reduction: 0.35,
    veto_status: 'PASSED',
    finished_at: '2026-09-04T22:10:00Z',
  },
  {
    task_id: 'tsk_8b2c5d7e',
    product_id: '0d1f3a5e-0006',
    asin: 'B0H3XK5VFB',
    title: 'Cordless Handheld Vacuum 无线手持吸尘器',
    main_image_url: img(106),
    estimated_roi: 1.9,
    return_rate_reduction: 0.28,
    veto_status: 'PASSED',
    finished_at: '2026-09-03T15:30:00Z',
  },
  {
    task_id: 'tsk_6a9b2c3d',
    product_id: '0d1f3a5e-0002',
    asin: 'B0D88X2YWZ',
    title: 'Ultrasonic Humidifier 超声波加湿器',
    main_image_url: img(102),
    estimated_roi: 0.8,
    return_rate_reduction: 0.12,
    veto_status: 'VETOED',
    finished_at: '2026-09-02T10:05:00Z',
  },
]

/* ---------------- 财务 ---------------- */

/** 财务模拟计算（与后端算法约定保持一致，前端沙盒复算） */
export function simulateFinancial(req: FinancialSimulateRequest): FinancialSimulateResult {
  const vwOld = (req.package_size_old_cm[0] * req.package_size_old_cm[1] * req.package_size_old_cm[2]) / 5000
  const vwNew = (req.package_size_new_cm[0] * req.package_size_new_cm[1] * req.package_size_new_cm[2]) / 5000
  const fulfillOld = fbaFee(vwOld)
  const fulfillNew = fbaFee(vwNew)
  const savingPerUnit = fulfillOld - fulfillNew

  const price = req.expected_price_usd
  const grossPerUnit = price * req.current_gross_margin
  const costDeltaPerUnit = req.unit_cost_increase_usd
  const monthlyProfitDelta =
    (savingPerUnit - costDeltaPerUnit) * (req.moq / (req.expected_payback_months || 6)) +
    (req.moq / (req.expected_payback_months || 6)) * grossPerUnit * req.expected_return_rate_reduction
  const totalCost = req.mold_cost_usd + req.moq * costDeltaPerUnit
  const paybackMonths = monthlyProfitDelta > 0 ? totalCost / monthlyProfitDelta : 999
  const roi = totalCost > 0 ? (monthlyProfitDelta * 12) / totalCost : 0

  const vetoReasons: string[] = []
  if (req.mold_cost_usd > 8000 && req.product_lifecycle_days < 180) {
    vetoReasons.push('预计开模改造周期 > 90 天且预期品类生命周期 < 180 天，存在错失窗口期风险')
  }
  if (costDeltaPerUnit > grossPerUnit * 0.35) {
    vetoReasons.push('单位改进成本增加额超过当前毛利额 35%，且无法提价，强制否决')
  }
  if (paybackMonths > req.expected_payback_months) {
    vetoReasons.push(`预计回本周期 ${paybackMonths.toFixed(1)} 个月，超出期望 ${req.expected_payback_months} 个月`)
  }
  const vetoed = vetoReasons.length > 0

  const fallbackSuggestions = vetoed
    ? ['免开模小改：仅替换关键受力件材质', '仅优化包装缓冲与尺寸降阶', '先小批量试销验证后再开模']
    : []

  const curve = [0.1, req.expected_return_rate_reduction, 0.6].map((r) => {
    const profit = (savingPerUnit - costDeltaPerUnit) * (req.moq / (req.expected_payback_months || 6)) +
      (req.moq / (req.expected_payback_months || 6)) * grossPerUnit * r
    return { return_rate_reduction: r, payback_months: profit > 0 ? totalCost / profit : 999 }
  })

  return {
    volumetric_weight_old_kg: vwOld,
    volumetric_weight_new_kg: vwNew,
    fba_tier_old: fbaTier(vwOld),
    fba_tier_new: fbaTier(vwNew),
    fulfillment_saving_usd_per_unit: Number(savingPerUnit.toFixed(2)),
    monthly_profit_delta_usd: Number(monthlyProfitDelta.toFixed(2)),
    payback_months: Number(paybackMonths.toFixed(1)),
    roi: Number(roi.toFixed(2)),
    veto_status: vetoed ? 'VETOED' : 'PASSED',
    veto_reasons: vetoReasons,
    fallback_suggestions: fallbackSuggestions,
    payback_curve: curve.map((p) => ({ ...p, payback_months: Number(p.payback_months.toFixed(1)) })),
  }
}

function fbaFee(volumetricWeightKg: number): number {
  // 简化 FBA 费用阶梯（USD）
  if (volumetricWeightKg <= 0.5) return 3.19
  if (volumetricWeightKg <= 1) return 4.05
  if (volumetricWeightKg <= 1.5) return 4.54
  if (volumetricWeightKg <= 2) return 5.2
  return 6.1
}

function fbaTier(volumetricWeightKg: number): string {
  if (volumetricWeightKg <= 0.5) return 'Small Standard'
  if (volumetricWeightKg <= 1) return 'Medium Standard'
  return 'Large Standard'
}

export const mockFinancialDecision: FinancialDecision = {
  task_id: 'tsk_9f2c81a4',
  veto_status: 'PASSED',
  checked_proposals: 5,
  vetoed_proposal_ids: ['prp_5b7e03'],
  veto_reasons: ['开模回收期长达 14 个月，已超出该品类 6 个月生命周期'],
  fallback_applied: true,
  retry_count: 1,
  financial_constraint: {
    mold_cost_usd: 8000,
    moq: 1000,
    current_gross_margin: 0.32,
    expected_price_usd: 29.99,
    unit_cost_increase_usd: 1.8,
    expected_payback_months: 6,
    sea_freight_usd_per_cbm: 180,
  },
}

/* ---------------- 价格历史 ---------------- */

export function buildPriceHistory(days = 90, basePrice = 29.99, seed = 7): { ts: string; price: number; bsr: number; buy_box_price: number; has_coupon: boolean }[] {
  const points: { ts: string; price: number; bsr: number; buy_box_price: number; has_coupon: boolean }[] = []
  const now = Date.now()
  const dayMs = 86_400_000
  let price = basePrice
  let bsr = 1240
  for (let i = days; i >= 0; i--) {
    // 简单伪随机游走
    const wobble = Math.sin((i + seed) * 0.7) * 0.6 + Math.sin(i * 1.3 + seed) * 0.4
    price = Math.max(19.99, Number((price + wobble * 0.12).toFixed(2)))
    bsr = Math.max(400, Math.round(bsr + Math.sin(i * 0.5 + seed) * 18))
    points.push({
      ts: new Date(now - i * dayMs).toISOString(),
      price,
      bsr,
      buy_box_price: Number((price - (i % 9 === 0 ? 2.5 : 0)).toFixed(2)),
      has_coupon: i % 14 === 0,
    })
  }
  return points
}

/* ---------------- 扩展 ---------------- */

export const mockAlerts: Alert[] = [
  {
    alert_id: 'alr_01',
    type: 'price_movement',
    severity: 'high',
    title: '竞品 B0C1234ABC 降价 12%',
    message: '目标竞品 2 小时内降价 $3.4，可能发起促销对冲',
    related_product_id: '0d1f3a5e-0001',
    related_task_id: null,
    is_read: false,
    created_at: '2026-09-05T07:30:00Z',
  },
  {
    alert_id: 'alr_02',
    type: 'veto',
    severity: 'high',
    title: '风控熔断：底座改款被否决',
    message: '开模回收期 14 个月超出品类生命周期，已生成免开模替代方案',
    related_product_id: '0d1f3a5e-0001',
    related_task_id: 'tsk_9f2c81a4',
    is_read: false,
    created_at: '2026-09-05T08:02:00Z',
  },
  {
    alert_id: 'alr_03',
    type: 'supply_chain',
    severity: 'medium',
    title: 'ABS 粒子价格周环比 +6%',
    message: '华东市场 ABS 粒子报价上涨，建议关注替代材质锁定远期订单',
    related_product_id: null,
    related_task_id: null,
    is_read: true,
    created_at: '2026-09-04T03:00:00Z',
  },
]

export const mockCrossPlatform: CrossPlatformMapping[] = [
  {
    product_id: '0d1f3a5e-0001',
    asin: 'B0C1234ABC',
    amazon_price_usd: 29.99,
    matches: [
      { platform: 'temu', external_sku: 'TM-88213', title: 'LED 台灯 折叠款', price_usd: 12.9, match_score: 0.91, commission_usd: 0.9, fulfillment_usd: 2.1 },
      { platform: 'tiktok', external_sku: 'TK-5518', title: '折叠护眼台灯', price_usd: 16.99, match_score: 0.86, commission_usd: 1.5, fulfillment_usd: 2.8 },
    ],
    max_price_gap_usd: 17.09,
  },
]

export const mockBacktest: BacktestResult = {
  backtest_id: 'bt_77aa01',
  task_id: 'tsk_9f2c81a4',
  slice_date: '2026-03-01',
  status: 'COMPLETED',
  accuracy_score: 0.78,
  cluster_verdicts: [
    { cluster_id: 'clu_01', cluster_name: '把手易断裂', hit: true, actual_trend: '同品类 2026 Q2 断裂类差评上升 22%' },
    { cluster_id: 'clu_02', cluster_name: 'LED 频闪', hit: true, actual_trend: '2026 Q2 频闪投诉成为头部痛点' },
    { cluster_id: 'clu_03', cluster_name: '运输破损', hit: false, actual_trend: '同期破损投诉占比下降，判断保守' },
  ],
}

/* ---------------- SSE 任务事件流模拟 ---------------- */

export interface StepSpec {
  step: TaskStep
  durationMs: number
  message: string
  extra?: Record<string, unknown>
}

export function buildStepSpecs(taskId: string): StepSpec[] {
  return [
    { step: 'QUEUED', durationMs: 500, message: '任务已入队，等待调度器分配' },
    { step: 'FETCHING_DATA', durationMs: 2400, message: 'Playwright 抓取 Amazon 评论与买家实拍图', extra: { reviews_fetched: 320 } },
    { step: 'VISION_AUDIT', durationMs: 2200, message: 'Claude Vision 完成 18 张买家实拍图质检', extra: { images_audited: 18 } },
    { step: 'SEMANTIC_CLUSTER', durationMs: 2000, message: 'bge-m3 向量化 320 条多语言评论并聚类', extra: { clusters: 6 } },
    { step: 'DUAL_DECISION', durationMs: 2000, message: 'LangGraph 生成双栏改款工程清单', extra: { proposals: 5 } },
    { step: 'FINANCIAL_VETO', durationMs: 1500, message: '财务否决引擎审核 5 条提案，1 条触发熔断', extra: { vetoed: 1 } },
    { step: 'EVIDENCE_TRACE', durationMs: 1000, message: '证据链反向索引校验完成，42 条评论绑定成功' },
    { step: 'COMPLETED', durationMs: 300, message: '任务完成，已可查看聚合报告', extra: { task_id: taskId } },
  ]
}

/** 各步骤对应的进度区间（docs/api.md §4.3） */
export function stepProgress(step: TaskStep): number {
  const map: Record<TaskStep, number> = {
    QUEUED: 5,
    FETCHING_DATA: 25,
    VISION_AUDIT: 45,
    SEMANTIC_CLUSTER: 65,
    DUAL_DECISION: 85,
    FINANCIAL_VETO: 92,
    EVIDENCE_TRACE: 96,
    BACKTEST_EVAL: 99,
    COMPLETED: 100,
    FAILED: 0,
  }
  return map[step]
}
