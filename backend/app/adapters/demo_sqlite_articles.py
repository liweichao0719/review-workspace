from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from app.adapters.demo_articles import DemoArticleAdapter


class DemoSqliteArticleAdapter(DemoArticleAdapter):
    """Reference adapter that reads article review rows from SQLite read-only."""

    project_id = "demo_sqlite_articles"
    project_name = "格式示例：SQLite 文章"
    project_description = "SQLite 数据源接入模式的合成文章样本"
    task_name = "SQLite 文章收录审查"
    task_description = "验证只读 SQLite 查询后复用文章审核任务契约。"
    source_capabilities = ("sqlite_source",)

    def __init__(self, path: Path) -> None:
        self.path = Path(path).resolve()
        if not self.path.exists():
            raise FileNotFoundError(f"demo SQLite article source missing: {self.path}")
        self._load()

    def _load(self) -> None:
        uri = f"{self.path.as_uri()}?mode=ro"
        try:
            with closing(sqlite3.connect(uri, uri=True)) as connection:
                connection.row_factory = sqlite3.Row
                source_rows = connection.execute(
                    """
                    SELECT
                        id, title, body, source_name, published_at, language,
                        topics_json, decision, confidence, reason,
                        suggested_tags_json
                    FROM articles
                    ORDER BY id
                    """
                ).fetchall()
        except sqlite3.DatabaseError as exc:
            raise ValueError(f"invalid demo SQLite article source: {exc}") from exc

        rows: list[dict[str, Any]] = []
        for source in source_rows:
            item_id = str(source["id"] or "")
            rows.append(
                {
                    "id": item_id,
                    "title": source["title"],
                    "body": source["body"],
                    "source_name": source["source_name"],
                    "published_at": source["published_at"],
                    "language": source["language"],
                    "topics": self._json_list(source["topics_json"], item_id, "topics"),
                    "model_suggestion": {
                        "decision": source["decision"],
                        "confidence": source["confidence"],
                        "reason": source["reason"],
                        "suggested_tags": self._json_list(
                            source["suggested_tags_json"],
                            item_id,
                            "suggested tags",
                        ),
                    },
                }
            )
        packed = json.dumps(
            rows,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        fingerprint = hashlib.sha256(packed.encode("utf-8")).hexdigest()[:12]
        self._set_rows(rows, f"demo-sqlite-articles-{fingerprint}")

    @staticmethod
    def _json_list(value: Any, item_id: str, field: str) -> Any:
        try:
            return json.loads(str(value))
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"demo SQLite article {item_id} has invalid JSON in {field}"
            ) from exc
