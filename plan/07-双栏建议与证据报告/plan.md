# 阶段 07：双栏建议与证据报告

## 目标与前置条件

闭合真实七节点文本链路，输出不可变报告、产品/包装建议及可核对证据，替换报告与证据接口的 501。

依赖 [阶段 04](../04-Worker与事件闭环/plan.md)、[阶段 06](../06-向量化与痛点聚类/plan.md)。先读 `docs/api.md` §5、`docs/技术方案.md` §4.2、§5；确认阶段 02 的指标空态和阶段 06 的未发布分析产物设计。

## 文件范围

已有：`backend/app/worker/nodes.py`、`worker/graph.py`、`api/routes/reports.py`、`api/schemas.py`、`db/models.py`。

拟新增：`backend/app/services/proposals.py`、`evidence.py`、`reports.py`、必要增量迁移、`backend/tests/test_proposals.py`、`test_evidence.py`、`test_reports.py`、`test_text_pipeline.py`。

## 实施步骤

- [ ] 以同一快照的簇和真实摘录构建模型输入；评论只作为不可信待分析数据，不授予执行工具或改变系统任务的能力。
- [ ] 输出 PRODUCT/PACKAGING 两类结构化建议，验证 title/action/target_cluster_ids/assumptions/verification_required 等字段。某栏无支持证据允许为空，不能填充幻觉。
- [ ] 每条建议必须指向当前分析范围的非空痛点集合；预期效果只能是有支持的定性建议，不得虚构精确收益、材料检测、公差或认证结果。
- [ ] 对格式和引用错误作有限修复；达到上限仍不合法则记录可诊断失败，不能过滤掉所有错误后悄悄标成功。
- [ ] 证据校验遍历 proposal → proposal_issues → cluster → cluster_members → fragment → review，验证同 tenant/task/item/report/snapshot 和原文位置；引用有效性要求全部通过。
- [ ] evidence_count 使用关联评论并集去重，与抽屉 total 一致；photo_count 在 P0 为 0，不能声称来源页面没有图片。
- [ ] 构建完整报告 payload：snapshot/product/coverage/metrics/clusters/proposals/provenance/limitations。按已确认采样口径计算样本指标，不能从仅低星采样推断整体平均星级或差评率；未定义潜力/FBA 指标为 null 并附原因。
- [ ] 合法无样本发布 INSUFFICIENT 报告，建议数组为空、模型节点跳过；来源失败仍无成功报告。P0 veto_status 固定 NOT_EVALUATED，不等于 PASSED。
- [ ] 发布事务中验证产物完整性、租约与取消标记，原子写不可变版本、分项完成、任务聚合与事件；报告 API 只能读已发布版本，不能暴露阶段 06 暂存结果。
- [ ] GET report 按契约区分执行中无报告 409、终态无报告 404、合法不足报告 200，严格校验 item 属于 task 和 tenant。
- [ ] GET evidence 要求 report_id 与 cluster_id/proposal_id 二选一；校验完整归属链，按稳定 reviewed_at/id 分页并定义 null 日期顺序，游标绑定过滤上下文。
- [ ] 返回原始来源、星级、时间和原文；未有译文为 null、P0 images 为空。P1 筛选参数未实现时返回 422，不静默忽略。
- [ ] 对齐 response schema 与实际 OpenAPI，业务查询不再残留 501；版本字段与报告内容一致。

## 验证与验收

```bash
cd backend
uv run pytest -q tests/test_proposals.py tests/test_evidence.py tests/test_reports.py tests/test_text_pipeline.py
uv run pytest -q
```

- [ ] 以一个已验证真实 ASIN 完成七节点闭环，再跑授权范围内批量任务；所有展示证据可反查真实来源。
- [ ] 同评论跨多个簇时建议计数仍等于评论并集，分页不改变 total；emoji/重复摘录位置保持正确。
- [ ] 跨租户、跨任务、跨 item、跨 report 的猜 ID/引用混用都被拒绝。
- [ ] 覆盖模型伪造引用、无证据单栏、合法空样本、采集失败、取消与发布竞态、恢复重放。
- [ ] 新分析不改旧报告；执行中半成品不会被查询成已发布结果；报告与 SSE 终态在事务后可见。

## 非目标与停止条件

不落实图片、真实财务、回测或前端界面；不新增 mock overview。任何无依据的指标或引用校验失败必须阻止发布或按已确认不足语义处理，不能用演示常量兜底。

## 交接

向阶段 08 提供真实任务/报告样本 ID、完整 API/OpenAPI、事件协议、错误样例及成本/限制证据，交付的是后端真实闭环而非“全产品已上线”。
