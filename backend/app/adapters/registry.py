from app.adapters.base import ReviewAdapter


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ReviewAdapter] = {}

    def register(self, adapter: ReviewAdapter) -> None:
        project_id = adapter.descriptor.id
        if project_id in self._adapters:
            raise ValueError(f"Adapter already registered: {project_id}")
        self._adapters[project_id] = adapter

    def clear(self) -> None:
        self._adapters.clear()

    def all(self) -> list[ReviewAdapter]:
        return list(self._adapters.values())

    def get(self, project_id: str) -> ReviewAdapter:
        try:
            return self._adapters[project_id]
        except KeyError as exc:
            raise KeyError(f"Unknown project: {project_id}") from exc
