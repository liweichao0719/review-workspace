from __future__ import annotations

import hashlib
import json
import os
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
    ReviewRecord,
)


TASK_ID = "rag-clause-audit"
STATUSES = {"pending", "approved", "revised", "needs_followup"}
TASK_TYPES = {"yellowbook_qa", "scenario_analysis", "special_clause_review", "multi_clause_reasoning", "insufficient_evidence"}
QUESTION_QUALITIES = {"usable", "needs_revision", "unusable"}
ANSWER_CONSISTENCY = {"supported", "partially_supported", "unsupported", "contradictory", "insufficient_evidence"}
CONTEXT_PREFIX = "fidic-yellow-book-2017:context:"
CLAUSE_REF = re.compile(r"(?<![\d.])([1-9]\d?(?:\.\d{1,3}){1,2})(?![\d.])")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _ref_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split("."))


def _context_ref(context_id: str) -> str:
    if not context_id.startswith(CONTEXT_PREFIX):
        raise ValueError(f"unsupported context ID: {context_id}")
    return context_id.removeprefix(CONTEXT_PREFIX)


class FidicRagAdapter(ReviewAdapter):
    """Expose the frozen dev192 set without mutating its source files."""

    def __init__(self, root: Path | None = None) -> None:
        default_root = Path(__file__).resolve().parents[4] / "RAG"
        self.root = Path(root or os.environ.get("REVIEW_FIDIC_RAG_ROOT", default_root)).resolve()
        self.paths = {
            "dataset": self.root / "results/human_gold_dev192_v1/dataset.jsonl",
            "manifest": self.root / "results/human_gold_dev192_v1/manifest.json",
            "corpus": self.root / "results/dev_audit_corpus/full_corpus.json",
        }
        missing = [str(path) for path in self.paths.values() if not path.exists()]
        if missing:
            raise FileNotFoundError("FIDIC final dataset sources missing: " + ", ".join(missing))
        self._load()

    @property
    def descriptor(self) -> ProjectDescriptor:
        return ProjectDescriptor(
            id="fidic",
            name="FIDIC 黄皮书",
            description="冻结开发集的独立复核工作区",
            tasks=[ProjectTask(
                id=TASK_ID,
                name="开发集审查",
                description="审查题型、问题、标准答案和展示上下文；修改写入独立审查记录，不回写冻结数据。",
                renderer_key="fidic_rag",
                capabilities=["edit", "autosave", "export", "bilingual_evidence", "versioned_reviews"],
                statuses=[
                    {"value": "pending", "label": "待复核"},
                    {"value": "approved", "label": "确认冻结版本"},
                    {"value": "revised", "label": "提出修订"},
                    {"value": "needs_followup", "label": "需要进一步核查"},
                ],
            )],
        )

    def dataset_version(self, task_id: str) -> str:
        self._require_task(task_id)
        return self._dataset_version

    def _load(self) -> None:
        corpus = json.loads(self.paths["corpus"].read_text(encoding="utf-8"))
        self._context_by_ref: dict[str, dict[str, Any]] = {}
        self._clause_to_context: dict[str, str] = {}
        self._context_order: list[str] = []
        for context in corpus["evidence_contexts"]:
            ref = _context_ref(str(context["context_id"]))
            if ref in self._context_by_ref:
                raise ValueError(f"duplicate context ref: {ref}")
            self._context_by_ref[ref] = context
            self._context_order.append(ref)
            for clause in context.get("covered_clause_nums", []):
                previous = self._clause_to_context.setdefault(str(clause), ref)
                if previous != ref:
                    raise ValueError(f"clause belongs to multiple contexts: {clause}")
        self._context_refs = set(self._context_by_ref)

        rows = _jsonl(self.paths["dataset"])
        if len(rows) != 192 or len({row["item_id"] for row in rows}) != 192:
            raise ValueError("frozen FIDIC dev set must contain 192 unique items")
        self._items: dict[str, dict[str, Any]] = {}
        for position, row in enumerate(sorted(rows, key=lambda value: value["item_id"]), 1):
            refs = list(row["gold_context_refs"])
            if set(refs) - self._context_refs:
                raise ValueError(f"item {row['item_id']} references missing contexts")
            audit = row.get("audit", {})
            quality = str(audit.get("final_question_quality", "usable"))
            task_type = str(row["task_type"])
            consistency = "insufficient_evidence" if task_type == "insufficient_evidence" else str(audit.get("source_answer_consistency", "supported"))
            if consistency not in ANSWER_CONSISTENCY:
                consistency = "supported"
            self._items[row["item_id"]] = {
                "row": row,
                "position": position,
                "contexts": self.resolve_contexts(refs),
                "assessment": {
                    "suggested_task_type": task_type,
                    "question_quality": quality,
                    "question_issues": [],
                    "recommended_context_refs": refs,
                    "answer_consistency": consistency,
                    "revised_answer": row["gold_answer"],
                    "answer_issues": [],
                    "human_review_priority": "high" if quality != "usable" else "low",
                    "overall_confidence": 1.0,
                    "rationale": "冻结开发集基线；任何人工修改将作为独立审查记录保存。",
                },
            }
        fingerprints = {name: _sha256(path) for name, path in self.paths.items()}
        packed = json.dumps(fingerprints, sort_keys=True, separators=(",", ":"))
        self._dataset_version = "fidic-dev192-" + hashlib.sha256(packed.encode()).hexdigest()[:12]

    def resolve_contexts(self, refs: list[str]) -> list[dict[str, Any]]:
        return [self._context_by_ref[ref] for ref in sorted(set(refs), key=_ref_key) if ref in self._context_by_ref]

    def list_items(self, task_id: str, *, query: str | None = None, status: str | None = None) -> list[ReviewItemSummary]:
        self._require_task(task_id)
        needle = (query or "").strip().lower()
        rows: list[ReviewItemSummary] = []
        for item_id, item in self._items.items():
            row = item["row"]
            if needle and needle not in f"{item_id} {row['question']} {row['gold_answer']}".lower():
                continue
            assessment = item["assessment"]
            badges = [row["task_type"]]
            if assessment["question_quality"] != "usable":
                badges.append("问题需修改" if assessment["question_quality"] == "needs_revision" else "证据不足")
            if len(row["gold_context_refs"]) > 6:
                badges.append("上下文偏多")
            rows.append(ReviewItemSummary(id=item_id, title=row["question"], subtitle=f"开发集 #{item['position']} · {len(row['gold_context_refs'])} 个上下文", badges=badges))
        return rows

    def get_item(self, task_id: str, item_id: str) -> ReviewItem:
        self._require_task(task_id)
        try:
            item = self._items[item_id]
        except KeyError as exc:
            raise KeyError(f"Unknown review item: {item_id}") from exc
        row = item["row"]
        return ReviewItem(
            id=item_id,
            title=row["question"],
            source={"question": row["question"], "existing_answer": row["gold_answer"], "clause_contexts": item["contexts"]},
            prediction={"context_audit": item["assessment"], "audit_meta": {"audit_version": "fidic-rag-dev192-gold-v1", "model": {"provider": "frozen", "name": "dev192"}, "attempt_count": 0}},
            metadata={"pilot_index": item["position"], "pilot_stratum": "frozen_dev192"},
        )

    def validate_review(
        self,
        task_id: str,
        item_id: str,
        patch: ReviewPatch,
    ) -> ReviewPatch:
        self._require_task(task_id)
        if item_id not in self._items:
            raise KeyError(f"Unknown review item: {item_id}")
        if patch.status not in STATUSES:
            raise ValueError("invalid review status")
        values = dict(patch.values)
        task_type = values.get("final_task_type")
        quality = values.get("final_question_quality")
        consistency = values.get("final_answer_consistency")
        refs = values.get("final_context_refs", [])
        if task_type not in TASK_TYPES or quality not in QUESTION_QUALITIES or consistency not in ANSWER_CONSISTENCY:
            raise ValueError("invalid review decision")
        if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
            raise ValueError("final context refs must be a string list")
        normalized_refs = sorted(set(refs), key=_ref_key)
        invalid = set(normalized_refs) - self._context_refs
        if invalid:
            raise ValueError(f"contexts outside the corpus: {sorted(invalid)}")
        answer = str(values.get("revised_answer", "")).strip()
        if not answer:
            raise ValueError("revised answer is required")
        if task_type == "insufficient_evidence" or quality == "unusable":
            if task_type != "insufficient_evidence" or quality != "unusable" or consistency != "insufficient_evidence" or normalized_refs:
                raise ValueError("unusable question must not keep context refs; insufficient-evidence review must be unusable")
        elif not normalized_refs:
            raise ValueError("answerable review must retain at least one context ref")
        citations = list(dict.fromkeys(CLAUSE_REF.findall(answer)))
        unknown = [citation for citation in citations if citation not in self._clause_to_context]
        if unknown:
            raise ValueError(f"answer cites clauses outside the corpus: {unknown}")
        if citations:
            used = {self._clause_to_context[citation] for citation in citations}
            derived = [ref for ref in self._context_order if ref in used]
            if derived != normalized_refs:
                raise ValueError("selected contexts must exactly cover the answer's cited clauses")
        values["final_context_refs"] = normalized_refs
        values["revised_question"] = str(values.get("revised_question", "")).strip()[:5000]
        values["revised_answer"] = answer[:20000]
        values["reviewer"] = str(values.get("reviewer", "")).strip()[:100]
        return ReviewPatch(status=patch.status, values=values, note=patch.note[:5000])

    def apply_review(
        self,
        task_id: str,
        item: ReviewItem,
        review: ReviewRecord,
    ) -> ReviewItem:
        item = super().apply_review(task_id, item, review)
        refs = review.values.get("final_context_refs")
        if isinstance(refs, list):
            item.source["clause_contexts"] = self.resolve_contexts(refs)
        return item

    @staticmethod
    def _require_task(task_id: str) -> None:
        if task_id != TASK_ID:
            raise KeyError(f"Unknown FIDIC task: {task_id}")
