# 阶段 05：采集清洗与数据快照

## 目标与前置条件

把一个已验证 ASIN 的真实来源数据变成不可变、可核对的商品/评论快照，再覆盖 1–10 ASIN 的分项隔离。

依赖 [阶段 02](../02-数据来源与模型验证/plan.md) 的来源与数据口径、[阶段 04](../04-Worker与事件闭环/plan.md) 的执行和事件机制。读取 `docs/技术方案.md` §4–5、`docs/api.md` §4–5、现有 ORM，不重新选择未验证供应方。

## 文件范围

已有：`backend/app/worker/nodes.py`、`worker/graph.py`（阶段 04 产物）、`db/models.py`、配置和必要迁移。

拟新增：`backend/app/services/ingestion.py`、`normalization.py`、`backend/tests/test_ingestion.py`、`test_normalization.py`、`test_snapshots.py`。供应方逻辑仅封装当前选定来源，是否分文件按真实复杂度决定。

## 实施步骤

- [ ] 从任务读取租户、商品、已解析窗口和来源配置；不接受评论/模型返回值改变 tenant、item 或授权范围。
- [ ] 对接已验证的商品与评论接口，保存来源原始 ID、观测时间、原始文本、星级、语言、评论日期与来源 URL，保留未知字段为 null。
- [ ] 校验 child/parent 关系、品类和站点，来源不存在/异品类作为分项错误，不能当零评论成功。
- [ ] 按授权范围处理分页、限流、超时和取消边界，重试复用阶段 04 机制；不能无限翻页或无限计费。批次中一个 ASIN 失败不回滚其他 ASIN 的已提交结果。
- [ ] 评论采用来源 ID 与内容版本存储；同来源评论修改时创建新版本，不改旧原文。快照只选该来源评论的一个版本，跨任务复用不能污染已发布报告。
- [ ] 清洗规范化但保留原文：去重、无效文本排除及原因可追踪；“broken”等短有效缺陷保留。原始计数包含去重前条目，必要的排除记录/分布不得丢失。
- [ ] 保存 source_query、window、product_snapshot、cleaning_version、content_hash 和 coverage；任何新结构用增量迁移，不能修改已经固定的旧迁移。
- [ ] 确保 raw_count = valid_count + excluded_count，negative_count 为有效 1–3 星子集；有效去重评论形成星级、语言、月份分布，缺失原因和 sampling_mode 不缺省。
- [ ] 数据复用键含 tenant、商品/站点、窗口、来源查询、清洗版本与有效期；新窗口/来源/版本必须失效，同键缓存不能跨租户使用。
- [ ] 合法无样本形成 INSUFFICIENT 中间结果并跳过 embedding/clustering/proposal，最终发布由阶段 07 完成；来源失败必须保持 FAILED，不伪装不足报告。
- [ ] 将 ingestion/normalization 真实节点接入执行图，数据写入、状态和事件遵守租约/fencing/事务约定。

## 验证与验收

```bash
cd backend
uv run pytest -q tests/test_ingestion.py tests/test_normalization.py tests/test_snapshots.py
uv run pytest -q
```

- [ ] 测试覆盖分页重复、评论改版、短有效文本、空样本、授权失败、超时、取消和混合星级样本。
- [ ] 新采集不能改写旧快照/旧原文；缓存复用有命中与失效测试，跨 tenant 不命中。
- [ ] 按快照逐项复核数量恒等式、各分布及来源链接；原始不足必须有限制说明。
- [ ] 在获准调用与预算内，运行一个真实 ASIN，再验证批准的批量样本；输出可追溯来源证据，离线 fixture 测试不代替这一步。
- [ ] 故障恢复不重复写评论版本或污染样本统计，旧租约的外部迟到响应不能覆盖新数据。

## 非目标与停止条件

不做向量、聚类、图像下载或建议生成，不强求每个 ASIN 达到固定样本数。来源字段缺失、条款不允许留存或预算不明时，记录阻塞并停止真实采集，不换成假来源。

## 交接

阶段 06 消费冻结的有效评论集合、原文与覆盖报告；明确哪些记录可分析，哪些已排除以及原因。传递的是具体 snapshot ID，不是可变的“当前商品全部评论”。
