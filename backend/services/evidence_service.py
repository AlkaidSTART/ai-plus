"""Evidence chain service: Proposal → Cluster → Review → ReviewImage.

每个 Proposal 的证据都必须能反查真实存在的 review_id / image_id；
不生成不存在的证据 ID。
"""

import logging

from agents.state import ClusterItem, EvidenceLinkItem, ProposalItem, VisualEvidence

logger = logging.getLogger(__name__)


class EvidenceService:
    def trace(
        self,
        proposals: list[ProposalItem],
        clusters: list[ClusterItem],
        evidences: list[VisualEvidence],
    ) -> list[EvidenceLinkItem]:
        by_cluster = {c["cluster_id"]: c for c in clusters}
        known_review_ids = {r for c in clusters for r in c.get("review_ids", [])}
        known_image_ids = {e["image_id"] for e in evidences} | {
            img for c in clusters for img in c.get("sample_image_ids", [])
        }

        links: list[EvidenceLinkItem] = []
        for proposal in proposals:
            review_ids: list[str] = []
            image_ids: list[str] = []
            for cluster_id in proposal.get("source_cluster_ids", []):
                cluster = by_cluster.get(cluster_id)
                if cluster is None:
                    logger.warning(
                        "evidence: proposal %s 引用了不存在的 cluster %s，已跳过",
                        proposal["proposal_id"], cluster_id,
                    )
                    continue
                review_ids.extend(rid for rid in cluster["review_ids"] if rid in known_review_ids)
                image_ids.extend(iid for iid in cluster.get("sample_image_ids", []) if iid in known_image_ids)

            proposal["evidence_review_count"] = len(set(review_ids))
            proposal["evidence_image_count"] = len(set(image_ids))
            for cluster_id in proposal.get("source_cluster_ids", []):
                if cluster_id in by_cluster:
                    links.append(
                        EvidenceLinkItem(
                            proposal_id=proposal["proposal_id"],
                            cluster_id=cluster_id,
                            review_ids=sorted(set(review_ids)),
                            image_ids=sorted(set(image_ids)),
                        )
                    )
        return links
