from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.adapters.base import ReviewAdapter
from app.models import (
    ProjectDescriptor,
    ProjectTask,
    ReviewItem,
    ReviewItemSummary,
    ReviewPatch,
)


TASK_ID = "graph-audit"
STATUSES = {"pending", "approved", "revised", "needs_followup"}
NODE_TYPES = {"risk_event", "vulnerability", "control", "impact"}
EDGE_TYPES = {"causes", "contributes_to", "mitigates", "indicates"}
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
SCHEMA_VERSION = "demo-graph-review-v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class DemoGraphAdapter(ReviewAdapter):
    """Synthetic node-edge review task that keeps graph rules in its adapter."""

    def __init__(self, path: Path | None = None) -> None:
        default_path = Path(__file__).resolve().parents[2] / "fixtures/demo_graphs.json"
        self.path = Path(path or default_path).resolve()
        if not self.path.exists():
            raise FileNotFoundError(f"demo graph fixture missing: {self.path}")
        self._load()

    @property
    def descriptor(self) -> ProjectDescriptor:
        return ProjectDescriptor(
            id="demo_graphs",
            name="示例：节点—关系复核",
            description="用于验证结构化图数据审核边界的本地合成材料",
            tasks=[
                ProjectTask(
                    id=TASK_ID,
                    name="节点—关系复核",
                    description="依据原文修订节点、关系和逐项证据，并进行结构校验。",
                    renderer_key="graph_review",
                    capabilities=[
                        "edit",
                        "autosave",
                        "export",
                        "structured_graph",
                        "evidence_quote",
                        "versioned_reviews",
                    ],
                    statuses=[
                        {"value": "pending", "label": "待复核"},
                        {"value": "approved", "label": "确认"},
                        {"value": "revised", "label": "已修订"},
                        {"value": "needs_followup", "label": "待核查"},
                    ],
                )
            ],
        )

    def dataset_version(self, task_id: str) -> str:
        self._require_task(task_id)
        return self._dataset_version

    def _load(self) -> None:
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(value, list) or not value:
            raise ValueError("demo graphs must be a non-empty JSON array")
        if any(not isinstance(row, dict) for row in value):
            raise ValueError("every demo graph row must be an object")
        rows: list[dict[str, Any]] = value
        item_ids = [str(row.get("id", "")) for row in rows]
        if any(not item_id for item_id in item_ids):
            raise ValueError("demo graphs require non-empty IDs")
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("demo graph IDs must be unique")
        self._items = {str(row["id"]): row for row in rows}
        self._positions = {
            item_id: position for position, item_id in enumerate(item_ids, start=1)
        }
        self._dataset_version = f"demo-graphs-{_sha256(self.path)[:12]}"
        for item_id, row in self._items.items():
            graph = row.get("model_graph", {})
            fixture_patch = ReviewPatch(
                status="pending",
                values={
                    "final_nodes": graph.get("nodes", []),
                    "final_edges": graph.get("edges", []),
                    "reviewer": "",
                },
            )
            self.validate_review(TASK_ID, item_id, fixture_patch)

    def list_items(
        self,
        task_id: str,
        *,
        query: str | None = None,
        status: str | None = None,
    ) -> list[ReviewItemSummary]:
        self._require_task(task_id)
        needle = (query or "").strip().lower()
        items: list[ReviewItemSummary] = []
        for item_id, row in self._items.items():
            graph = row.get("model_graph", {})
            nodes = graph.get("nodes", [])
            searchable = " ".join(
                [
                    item_id,
                    str(row.get("title", "")),
                    str(row.get("text", "")),
                    str(row.get("source_name", "")),
                    *[str(node.get("label", "")) for node in nodes],
                ]
            ).lower()
            if needle and needle not in searchable:
                continue
            node_types = list(
                dict.fromkeys(str(node.get("type", "")) for node in nodes)
            )
            edges = graph.get("edges", [])
            items.append(
                ReviewItemSummary(
                    id=item_id,
                    title=str(row.get("title", item_id)),
                    subtitle=(
                        f"{row.get('source_name', '未知来源')} · "
                        f"{row.get('published_at', '未知日期')}"
                    ),
                    badges=[
                        f"{len(nodes)} 节点",
                        f"{len(edges)} 关系",
                        *node_types[:2],
                    ],
                )
            )
        return items

    def get_item(self, task_id: str, item_id: str) -> ReviewItem:
        self._require_task(task_id)
        try:
            row = self._items[item_id]
        except KeyError as exc:
            raise KeyError(f"Unknown review item: {item_id}") from exc
        graph = row["model_graph"]
        return ReviewItem(
            id=item_id,
            title=str(row["title"]),
            source={
                "title": row["title"],
                "text": row["text"],
                "source_name": row["source_name"],
                "published_at": row["published_at"],
                "language": row["language"],
            },
            prediction={
                "graph_candidate": {
                    "nodes": [dict(node) for node in graph["nodes"]],
                    "edges": [dict(edge) for edge in graph["edges"]],
                }
            },
            metadata={
                "position": self._positions[item_id],
                "synthetic": True,
            },
        )

    def validate_review(
        self,
        task_id: str,
        item_id: str,
        patch: ReviewPatch,
    ) -> ReviewPatch:
        self._require_task(task_id)
        try:
            text = str(self._items[item_id]["text"])
        except KeyError as exc:
            raise KeyError(f"Unknown review item: {item_id}") from exc
        if patch.status not in STATUSES:
            raise ValueError("invalid review status")
        values = dict(patch.values)
        nodes = self._normalize_nodes(values.get("final_nodes"), text)
        edges = self._normalize_edges(values.get("final_edges"), nodes, text)
        return ReviewPatch(
            status=patch.status,
            values={
                "graph_schema_version": SCHEMA_VERSION,
                "final_nodes": nodes,
                "final_edges": edges,
                "reviewer": str(values.get("reviewer", "")).strip()[:100],
            },
            note=patch.note.strip()[:5000],
        )

    @staticmethod
    def _normalize_nodes(raw_nodes: Any, text: str) -> list[dict[str, str]]:
        if not isinstance(raw_nodes, list):
            raise ValueError("final nodes must be a list")
        if not 1 <= len(raw_nodes) <= 12:
            raise ValueError("graph review requires between one and twelve nodes")
        nodes: list[dict[str, str]] = []
        identifiers: set[str] = set()
        for raw_node in raw_nodes:
            if not isinstance(raw_node, dict):
                raise ValueError("every node must be an object")
            node_id = str(raw_node.get("id", "")).strip()
            node_type = str(raw_node.get("type", "")).strip()
            label = str(raw_node.get("label", "")).strip()
            evidence = str(raw_node.get("evidence", "")).strip()
            if not IDENTIFIER.fullmatch(node_id):
                raise ValueError(f"invalid node ID: {node_id or '<empty>'}")
            if node_id in identifiers:
                raise ValueError(f"duplicate node ID: {node_id}")
            if node_type not in NODE_TYPES:
                raise ValueError(f"invalid node type: {node_type or '<empty>'}")
            if not label or len(label) > 200:
                raise ValueError(f"node {node_id} requires a label of at most 200 chars")
            if not evidence or evidence not in text:
                raise ValueError(f"node {node_id} evidence must occur verbatim in source")
            identifiers.add(node_id)
            nodes.append(
                {
                    "id": node_id,
                    "type": node_type,
                    "label": label,
                    "evidence": evidence,
                }
            )
        return nodes

    @staticmethod
    def _normalize_edges(
        raw_edges: Any,
        nodes: list[dict[str, str]],
        text: str,
    ) -> list[dict[str, str]]:
        if not isinstance(raw_edges, list):
            raise ValueError("final edges must be a list")
        if len(raw_edges) > 20:
            raise ValueError("at most twenty edges are allowed")
        node_ids = {node["id"] for node in nodes}
        edge_ids: set[str] = set()
        triples: set[tuple[str, str, str]] = set()
        edges: list[dict[str, str]] = []
        for raw_edge in raw_edges:
            if not isinstance(raw_edge, dict):
                raise ValueError("every edge must be an object")
            edge_id = str(raw_edge.get("id", "")).strip()
            source = str(raw_edge.get("source", "")).strip()
            target = str(raw_edge.get("target", "")).strip()
            edge_type = str(raw_edge.get("type", "")).strip()
            evidence = str(raw_edge.get("evidence", "")).strip()
            if not IDENTIFIER.fullmatch(edge_id):
                raise ValueError(f"invalid edge ID: {edge_id or '<empty>'}")
            if edge_id in edge_ids:
                raise ValueError(f"duplicate edge ID: {edge_id}")
            if source not in node_ids or target not in node_ids:
                raise ValueError(f"edge {edge_id} must reference existing nodes")
            if source == target:
                raise ValueError(f"edge {edge_id} cannot be a self-loop")
            if edge_type not in EDGE_TYPES:
                raise ValueError(f"invalid edge type: {edge_type or '<empty>'}")
            triple = (source, target, edge_type)
            if triple in triples:
                raise ValueError(
                    f"duplicate edge relation: {source} {edge_type} {target}"
                )
            if not evidence or evidence not in text:
                raise ValueError(f"edge {edge_id} evidence must occur verbatim in source")
            edge_ids.add(edge_id)
            triples.add(triple)
            edges.append(
                {
                    "id": edge_id,
                    "source": source,
                    "target": target,
                    "type": edge_type,
                    "evidence": evidence,
                }
            )
        return edges

    @staticmethod
    def _require_task(task_id: str) -> None:
        if task_id != TASK_ID:
            raise KeyError(f"Unknown demo graph task: {task_id}")
