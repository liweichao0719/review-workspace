from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.adapters import AdapterRegistry
from app.adapters.demo_articles import DemoArticleAdapter
from app.adapters.fidic_rag import FidicRagAdapter
from app.models import (
    ProjectDescriptor,
    ReviewItem,
    ReviewListResponse,
    ReviewPatch,
    ReviewRecord,
)
from app.store import ReviewStore


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = Path(
    os.environ.get("REVIEW_DATABASE_PATH", PROJECT_ROOT / "data/reviews.db")
)

app = FastAPI(
    title="Review Workspace API",
    version="0.2.0",
    description="Shared review infrastructure with project-specific adapters.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

registry = AdapterRegistry()
store = ReviewStore(DATABASE_PATH)


def register_available_adapters() -> None:
    registry.clear()
    try:
        registry.register(FidicRagAdapter())
    except FileNotFoundError:
        pass
    if os.environ.get("REVIEW_ENABLE_DEMOS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        registry.register(DemoArticleAdapter())


register_available_adapters()


def _adapter(project_id: str):
    try:
        return registry.get(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/health")
def health() -> dict[str, str | int]:
    return {"status": "ok", "projects": len(registry.all())}


@app.get("/api/projects", response_model=list[ProjectDescriptor])
def list_projects() -> list[ProjectDescriptor]:
    return [adapter.descriptor for adapter in registry.all()]


@app.get(
    "/api/projects/{project_id}/tasks/{task_id}/items",
    response_model=ReviewListResponse,
)
def list_items(
    project_id: str,
    task_id: str,
    query: str | None = Query(default=None, max_length=200),
    status: str | None = Query(default=None, max_length=50),
) -> ReviewListResponse:
    adapter = _adapter(project_id)
    dataset_version = adapter.dataset_version(task_id)
    reviews = store.list(project_id, task_id, dataset_version)
    items = adapter.list_items(task_id, query=query)
    for item in items:
        item.status = reviews.get(item.id).status if item.id in reviews else "pending"
    if status and status != "all":
        items = [item for item in items if item.status == status]
    all_items = adapter.list_items(task_id)
    counts: dict[str, int] = {"total": len(all_items)}
    for item in all_items:
        current = reviews.get(item.id).status if item.id in reviews else "pending"
        counts[current] = counts.get(current, 0) + 1
    return ReviewListResponse(
        project_id=project_id,
        task_id=task_id,
        dataset_version=dataset_version,
        total=len(items),
        counts=counts,
        items=items,
    )


@app.get(
    "/api/projects/{project_id}/tasks/{task_id}/items/{item_id}",
    response_model=ReviewItem,
)
def get_item(project_id: str, task_id: str, item_id: str) -> ReviewItem:
    adapter = _adapter(project_id)
    try:
        item = adapter.get_item(task_id, item_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    review = store.get(
        project_id,
        task_id,
        item_id,
        adapter.dataset_version(task_id),
    )
    if review:
        item = adapter.apply_review(task_id, item, review)
    return item


@app.put(
    "/api/projects/{project_id}/tasks/{task_id}/items/{item_id}/review",
    response_model=ReviewRecord,
)
def save_review(
    project_id: str, task_id: str, item_id: str, patch: ReviewPatch
) -> ReviewRecord:
    adapter = _adapter(project_id)
    try:
        adapter.get_item(task_id, item_id)
        normalized = adapter.validate_review(task_id, item_id, patch)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return store.save(
        project_id,
        task_id,
        item_id,
        adapter.dataset_version(task_id),
        normalized,
    )


@app.get("/api/projects/{project_id}/tasks/{task_id}/export")
def export_reviews(project_id: str, task_id: str) -> Response:
    adapter = _adapter(project_id)
    dataset_version = adapter.dataset_version(task_id)
    rows = store.export_rows(project_id, task_id, dataset_version)
    content = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    )
    filename = f"{project_id}-{task_id}-{dataset_version}.jsonl"
    return Response(
        content=content,
        media_type="application/x-ndjson; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
