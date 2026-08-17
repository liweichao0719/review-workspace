from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from app.adapters.demo_articles import DemoArticleAdapter, _sha256


class DemoCsvArticleAdapter(DemoArticleAdapter):
    """Reference adapter for an article review source stored as CSV."""

    project_id = "demo_csv_articles"
    project_name = "格式示例：CSV 文章"
    project_description = "CSV 数据源接入模式的合成文章样本"
    task_name = "CSV 文章收录审查"
    task_description = "验证 CSV 字段转换后复用文章审核任务契约。"
    source_capabilities = ("csv_source",)

    def __init__(self, path: Path | None = None) -> None:
        default_path = Path(__file__).resolve().parents[2] / "fixtures/demo_articles.csv"
        self.path = Path(path or default_path).resolve()
        if not self.path.exists():
            raise FileNotFoundError(f"demo CSV article fixture missing: {self.path}")
        self._load()

    def _load(self) -> None:
        rows: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {
                "id",
                "title",
                "body",
                "source_name",
                "published_at",
                "language",
                "topics",
                "decision",
                "confidence",
                "reason",
                "suggested_tags",
            }
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"demo CSV is missing columns: {sorted(missing)}")
            for line_number, source in enumerate(reader, start=2):
                try:
                    confidence = float(source.get("confidence") or "")
                except ValueError as exc:
                    raise ValueError(
                        f"{self.path}:{line_number} confidence must be numeric"
                    ) from exc
                rows.append(
                    {
                        "id": source.get("id") or "",
                        "title": source.get("title") or "",
                        "body": source.get("body") or "",
                        "source_name": source.get("source_name") or "",
                        "published_at": source.get("published_at") or "",
                        "language": source.get("language") or "",
                        "topics": self._split_list(source.get("topics")),
                        "model_suggestion": {
                            "decision": source.get("decision") or "",
                            "confidence": confidence,
                            "reason": source.get("reason") or "",
                            "suggested_tags": self._split_list(
                                source.get("suggested_tags")
                            ),
                        },
                    }
                )
        self._set_rows(rows, f"demo-csv-articles-{_sha256(self.path)[:12]}")

    @staticmethod
    def _split_list(value: str | None) -> list[str]:
        return [part.strip() for part in (value or "").split("|") if part.strip()]
