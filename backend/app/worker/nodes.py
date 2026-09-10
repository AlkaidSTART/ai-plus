"""P0 七个执行节点（技术方案 §5.1）。步骤 2 之前全部为 stub，禁止静默返回假产物。"""

from typing import Any

NODE_ORDER: tuple[str, ...] = (
    "ingestion",
    "normalization",
    "embedding",
    "clustering",
    "proposal",
    "evidence_validation",
    "publish",
)


async def run_node(node: str, item_id: str, attempt: int) -> dict[str, Any]:
    raise NotImplementedError(f"节点 {node}（item={item_id}, attempt={attempt}）在步骤 2 实现")
