from pathlib import Path

from app.models import ReviewPatch
from app.store import ReviewStore


def test_store_versions_and_keeps_revision_history(tmp_path: Path) -> None:
    store = ReviewStore(tmp_path / "reviews.db")
    first = store.save(
        "project",
        "task",
        "item",
        "dataset-v1",
        ReviewPatch(status="approved", values={"answer": 1}, note="first"),
    )
    second = store.save(
        "project",
        "task",
        "item",
        "dataset-v1",
        ReviewPatch(status="revised", values={"answer": 2}, note="second"),
    )
    other_version = store.save(
        "project",
        "task",
        "item",
        "dataset-v2",
        ReviewPatch(status="pending", values={}, note="new source"),
    )

    assert first.revision == 1
    assert second.revision == 2
    assert second.created_at == first.created_at
    assert other_version.revision == 1
    assert store.get("project", "task", "item", "dataset-v1") == second
    assert store.get("project", "task", "item", "dataset-v2") == other_version

    with store._connect() as connection:
        event_count = connection.execute(
            "SELECT COUNT(*) FROM review_events"
        ).fetchone()[0]
    assert event_count == 3
