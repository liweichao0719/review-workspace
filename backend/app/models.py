from typing import Any

from pydantic import BaseModel, Field


class ProjectTask(BaseModel):
    id: str
    name: str
    description: str
    renderer_key: str
    capabilities: list[str] = Field(default_factory=list)
    statuses: list[dict[str, str]] = Field(default_factory=list)


class ProjectDescriptor(BaseModel):
    id: str
    name: str
    description: str
    tasks: list[ProjectTask]


class ReviewItemSummary(BaseModel):
    id: str
    title: str
    subtitle: str | None = None
    status: str = "pending"
    badges: list[str] = Field(default_factory=list)


class ReviewItem(BaseModel):
    id: str
    title: str
    status: str = "pending"
    source: dict[str, Any] = Field(default_factory=dict)
    prediction: dict[str, Any] = Field(default_factory=dict)
    review: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewPatch(BaseModel):
    status: str
    values: dict[str, Any] = Field(default_factory=dict)
    note: str = ""


class ReviewRecord(BaseModel):
    project_id: str
    task_id: str
    item_id: str
    dataset_version: str
    revision: int
    status: str
    values: dict[str, Any] = Field(default_factory=dict)
    note: str = ""
    created_at: str
    updated_at: str


class ReviewListResponse(BaseModel):
    project_id: str
    task_id: str
    dataset_version: str
    total: int
    counts: dict[str, int]
    items: list[ReviewItemSummary]
