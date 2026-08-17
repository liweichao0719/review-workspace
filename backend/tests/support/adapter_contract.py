from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest

from app.adapters.base import ReviewAdapter
from app.models import ReviewPatch, ReviewRecord


AdapterFactory = Callable[[], ReviewAdapter]
PatchFactory = Callable[[ReviewAdapter, str], ReviewPatch]


@dataclass(frozen=True)
class AdapterContractCase:
    make_adapter: AdapterFactory
    task_id: str
    item_id: str
    valid_patch: PatchFactory


def assert_review_adapter_contract(case: AdapterContractCase) -> None:
    """Exercise behavior every adapter must provide to the shared workspace."""
    adapter = case.make_adapter()
    descriptor = adapter.descriptor
    assert descriptor.id.strip()
    assert descriptor.name.strip()
    assert descriptor.description.strip()
    assert descriptor.tasks
    assert len({task.id for task in descriptor.tasks}) == len(descriptor.tasks)

    task = next(task for task in descriptor.tasks if task.id == case.task_id)
    assert task.name.strip()
    assert task.description.strip()
    assert task.renderer_key.strip()
    assert task.capabilities
    status_values = [status["value"] for status in task.statuses]
    assert "pending" in status_values
    assert len(status_values) == len(set(status_values))

    version = adapter.dataset_version(case.task_id)
    assert version.strip()
    assert version == adapter.dataset_version(case.task_id)
    second = case.make_adapter()
    assert second.dataset_version(case.task_id) == version
    assert second.descriptor.model_dump() == descriptor.model_dump()

    summaries = adapter.list_items(case.task_id)
    assert summaries
    assert len({summary.id for summary in summaries}) == len(summaries)
    assert [summary.model_dump() for summary in summaries] == [
        summary.model_dump() for summary in adapter.list_items(case.task_id)
    ]
    assert case.item_id in {summary.id for summary in summaries}
    for summary in summaries:
        assert summary.id.strip()
        assert summary.title.strip()
        item = adapter.get_item(case.task_id, summary.id)
        assert item.id == summary.id
        assert item.title == summary.title
        assert item.status == "pending"
        assert item.review == {}

    matches = adapter.list_items(case.task_id, query=case.item_id)
    assert [summary.id for summary in matches] == [case.item_id]

    patch = case.valid_patch(adapter, case.item_id)
    original = patch.model_dump()
    normalized = adapter.validate_review(case.task_id, case.item_id, patch)
    assert patch.model_dump() == original
    assert normalized.status in status_values
    assert normalized.model_dump() == adapter.validate_review(
        case.task_id,
        case.item_id,
        patch,
    ).model_dump()

    invalid_status = patch.model_copy(update={"status": "__invalid_status__"})
    with pytest.raises(ValueError):
        adapter.validate_review(case.task_id, case.item_id, invalid_status)
    with pytest.raises(KeyError):
        adapter.get_item(case.task_id, "__missing_item__")
    with pytest.raises(KeyError):
        adapter.validate_review(case.task_id, "__missing_item__", patch)

    invalid_task = "__missing_task__"
    with pytest.raises(KeyError):
        adapter.dataset_version(invalid_task)
    with pytest.raises(KeyError):
        adapter.list_items(invalid_task)
    with pytest.raises(KeyError):
        adapter.get_item(invalid_task, case.item_id)
    with pytest.raises(KeyError):
        adapter.validate_review(invalid_task, case.item_id, patch)

    record = ReviewRecord(
        project_id=descriptor.id,
        task_id=case.task_id,
        item_id=case.item_id,
        dataset_version=version,
        revision=1,
        status=normalized.status,
        values=normalized.values,
        note=normalized.note,
        created_at="2026-08-17T00:00:00+00:00",
        updated_at="2026-08-17T00:00:00+00:00",
    )
    attached = adapter.apply_review(
        case.task_id,
        adapter.get_item(case.task_id, case.item_id),
        record,
    )
    assert attached.status == normalized.status
    assert attached.review["revision"] == 1
    assert attached.review["values"] == normalized.values

    fresh = adapter.get_item(case.task_id, case.item_id)
    assert fresh.status == "pending"
    assert fresh.review == {}
