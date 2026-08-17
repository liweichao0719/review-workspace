"""Run the API for browser tests with demos and an isolated temporary store."""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn


def main() -> None:
    value = os.environ.get("REVIEW_E2E_DATABASE")
    if not value:
        raise RuntimeError("REVIEW_E2E_DATABASE is required")
    database = Path(value).resolve()
    if database.name != "e2e-reviews.db" or database.parent.name != "test-results":
        raise RuntimeError("E2E database must be test-results/e2e-reviews.db")
    database.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-shm", "-wal"):
        Path(f"{database}{suffix}").unlink(missing_ok=True)

    os.environ["REVIEW_ENABLE_DEMOS"] = "1"
    os.environ["REVIEW_DATABASE_PATH"] = str(database)
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=18010,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
