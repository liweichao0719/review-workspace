from abc import ABC, abstractmethod

from app.models import (
    ProjectDescriptor,
    ReviewItem,
    ReviewItemSummary,
    ReviewPatch,
    ReviewRecord,
)


class ReviewAdapter(ABC):
    """Boundary between project-specific data and the shared workspace."""

    @property
    @abstractmethod
    def descriptor(self) -> ProjectDescriptor:
        """Describe the project and its available review tasks."""

    @abstractmethod
    def dataset_version(self, task_id: str) -> str:
        """Return a stable fingerprint for one task's source data."""

    @abstractmethod
    def list_items(
        self,
        task_id: str,
        *,
        query: str | None = None,
        status: str | None = None,
    ) -> list[ReviewItemSummary]:
        """Return lightweight records for the navigation list."""

    @abstractmethod
    def get_item(self, task_id: str, item_id: str) -> ReviewItem:
        """Return one normalized review item."""

    @abstractmethod
    def validate_review(
        self,
        task_id: str,
        item_id: str,
        patch: ReviewPatch,
    ) -> ReviewPatch:
        """Normalize and validate values before the shared store persists them."""

    def apply_review(
        self,
        task_id: str,
        item: ReviewItem,
        review: ReviewRecord,
    ) -> ReviewItem:
        """Attach a stored review to an item before returning it to the UI."""
        item.status = review.status
        item.review = review.model_dump()
        return item
