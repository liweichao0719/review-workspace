from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models import ReviewPatch, ReviewRecord


SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    revision INTEGER NOT NULL,
    status TEXT NOT NULL,
    values_json TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, task_id, item_id, dataset_version)
);
CREATE TABLE IF NOT EXISTS review_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    revision INTEGER NOT NULL,
    status TEXT NOT NULL,
    values_json TEXT NOT NULL,
    note TEXT NOT NULL,
    saved_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reviews_scope
ON reviews(project_id, task_id, dataset_version, status);
"""


class ReviewStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @staticmethod
    def _decode(row: sqlite3.Row) -> ReviewRecord:
        return ReviewRecord(
            project_id=row["project_id"],
            task_id=row["task_id"],
            item_id=row["item_id"],
            dataset_version=row["dataset_version"],
            revision=row["revision"],
            status=row["status"],
            values=json.loads(row["values_json"]),
            note=row["note"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get(
        self, project_id: str, task_id: str, item_id: str, dataset_version: str
    ) -> ReviewRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM reviews
                WHERE project_id=? AND task_id=? AND item_id=? AND dataset_version=?""",
                (project_id, task_id, item_id, dataset_version),
            ).fetchone()
        return self._decode(row) if row else None

    def list(
        self, project_id: str, task_id: str, dataset_version: str
    ) -> dict[str, ReviewRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM reviews
                WHERE project_id=? AND task_id=? AND dataset_version=?
                ORDER BY item_id""",
                (project_id, task_id, dataset_version),
            ).fetchall()
        return {row["item_id"]: self._decode(row) for row in rows}

    def save(
        self,
        project_id: str,
        task_id: str,
        item_id: str,
        dataset_version: str,
        patch: ReviewPatch,
    ) -> ReviewRecord:
        now = datetime.now(timezone.utc).isoformat()
        values_json = json.dumps(
            patch.values, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute(
                """SELECT revision, created_at FROM reviews
                WHERE project_id=? AND task_id=? AND item_id=? AND dataset_version=?""",
                (project_id, task_id, item_id, dataset_version),
            ).fetchone()
            revision = int(previous["revision"]) + 1 if previous else 1
            created_at = str(previous["created_at"]) if previous else now
            connection.execute(
                """INSERT INTO reviews (
                    project_id, task_id, item_id, dataset_version, revision,
                    status, values_json, note, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, task_id, item_id, dataset_version)
                DO UPDATE SET revision=excluded.revision, status=excluded.status,
                    values_json=excluded.values_json, note=excluded.note,
                    updated_at=excluded.updated_at""",
                (
                    project_id, task_id, item_id, dataset_version, revision,
                    patch.status, values_json, patch.note, created_at, now,
                ),
            )
            connection.execute(
                """INSERT INTO review_events (
                    project_id, task_id, item_id, dataset_version, revision,
                    status, values_json, note, saved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_id, task_id, item_id, dataset_version, revision,
                    patch.status, values_json, patch.note, now,
                ),
            )
        record = self.get(project_id, task_id, item_id, dataset_version)
        if record is None:
            raise RuntimeError("review was not persisted")
        return record

    def export_rows(
        self, project_id: str, task_id: str, dataset_version: str
    ) -> list[dict[str, Any]]:
        return [
            record.model_dump()
            for record in self.list(project_id, task_id, dataset_version).values()
        ]
