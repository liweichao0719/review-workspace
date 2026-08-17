from __future__ import annotations

import hashlib
import json
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


TASK_ID = "article-triage"
STATUSES = {"pending", "approved", "revised", "needs_followup"}
DECISIONS = {"include", "exclude", "needs_followup"}
RELEVANCE = {"high", "medium", "low", "irrelevant"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class DemoArticleAdapter(ReviewAdapter):
    """Small synthetic article task used to exercise the adapter boundary."""

    def __init__(self, path: Path | None = None) -> None:
        default_path = Path(__file__).resolve().parents[2] / "fixtures/demo_articles.jsonl"
        self.path = Path(path or default_path).resolve()
        if not self.path.exists():
            raise FileNotFoundError(f"demo article fixture missing: {self.path}")
        self._load()

    @property
    def descriptor(self) -> ProjectDescriptor:
        return ProjectDescriptor(
            id="demo_articles",
            name="示例：文章筛选",
            description="用于验证多数据类型边界的本地合成文章",
            tasks=[
                ProjectTask(
                    id=TASK_ID,
                    name="文章收录审查",
                    description="阅读文章并复核收录决定、相关性、标签与证据摘录。",
                    renderer_key="article_review",
                    capabilities=[
                        "edit",
                        "autosave",
                        "export",
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
        rows: list[dict[str, Any]] = []
        for line_number, raw in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not raw.strip():
                continue
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError(f"{self.path}:{line_number} must be an object")
            rows.append(value)
        item_ids = [str(row.get("id", "")) for row in rows]
        if not rows or any(not item_id for item_id in item_ids):
            raise ValueError("demo articles require non-empty IDs")
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("demo article IDs must be unique")
        self._items = {str(row["id"]): row for row in rows}
        self._positions = {
            item_id: position for position, item_id in enumerate(item_ids, start=1)
        }
        self._dataset_version = f"demo-articles-{_sha256(self.path)[:12]}"

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
            searchable = " ".join(
                [
                    item_id,
                    str(row.get("title", "")),
                    str(row.get("body", "")),
                    str(row.get("source_name", "")),
                    " ".join(map(str, row.get("topics", []))),
                ]
            ).lower()
            if needle and needle not in searchable:
                continue
            suggestion = row.get("model_suggestion", {})
            badges = [
                str(suggestion.get("decision", "unknown")),
                *[str(topic) for topic in row.get("topics", [])[:2]],
            ]
            items.append(
                ReviewItemSummary(
                    id=item_id,
                    title=str(row.get("title", item_id)),
                    subtitle=(
                        f"{row.get('source_name', '未知来源')} · "
                        f"{row.get('published_at', '未知日期')}"
                    ),
                    badges=badges,
                )
            )
        return items

    def get_item(self, task_id: str, item_id: str) -> ReviewItem:
        self._require_task(task_id)
        try:
            row = self._items[item_id]
        except KeyError as exc:
            raise KeyError(f"Unknown review item: {item_id}") from exc
        return ReviewItem(
            id=item_id,
            title=str(row["title"]),
            source={
                "title": row["title"],
                "body": row["body"],
                "source_name": row["source_name"],
                "published_at": row["published_at"],
                "language": row["language"],
                "topics": list(row.get("topics", [])),
            },
            prediction={"article_triage": dict(row["model_suggestion"])},
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
            article = self._items[item_id]
        except KeyError as exc:
            raise KeyError(f"Unknown review item: {item_id}") from exc
        if patch.status not in STATUSES:
            raise ValueError("invalid review status")
        values = dict(patch.values)
        decision = str(values.get("decision", ""))
        relevance = str(values.get("relevance", ""))
        if decision not in DECISIONS:
            raise ValueError("invalid article decision")
        if relevance not in RELEVANCE:
            raise ValueError("invalid article relevance")
        raw_tags = values.get("final_tags", [])
        if not isinstance(raw_tags, list) or any(
            not isinstance(tag, str) for tag in raw_tags
        ):
            raise ValueError("final tags must be a string list")
        tags = list(
            dict.fromkeys(tag.strip()[:40] for tag in raw_tags if tag.strip())
        )
        if len(tags) > 8:
            raise ValueError("at most eight final tags are allowed")
        evidence_quote = str(values.get("evidence_quote", "")).strip()
        decision_reason = str(values.get("decision_reason", "")).strip()
        if evidence_quote and evidence_quote not in str(article["body"]):
            raise ValueError("evidence quote must occur verbatim in the article body")
        if decision == "include" and (not tags or not evidence_quote):
            raise ValueError("included articles require tags and an evidence quote")
        if decision != "include" and not decision_reason:
            raise ValueError("excluded or follow-up articles require a decision reason")
        normalized = {
            "decision": decision,
            "relevance": relevance,
            "final_tags": tags,
            "evidence_quote": evidence_quote[:2000],
            "decision_reason": decision_reason[:2000],
            "reviewer": str(values.get("reviewer", "")).strip()[:100],
        }
        return ReviewPatch(
            status=patch.status,
            values=normalized,
            note=patch.note.strip()[:5000],
        )

    @staticmethod
    def _require_task(task_id: str) -> None:
        if task_id != TASK_ID:
            raise KeyError(f"Unknown demo article task: {task_id}")
