from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main
from app.adapters.demo_graphs import DemoGraphAdapter, TASK_ID
from app.models import ReviewPatch
from app.store import ReviewStore


client = TestClient(main.app)


def candidate_patch(adapter: DemoGraphAdapter, item_id: str = "graph_001") -> ReviewPatch:
    graph = adapter.get_item(TASK_ID, item_id).prediction["graph_candidate"]
    return ReviewPatch(
        status="revised",
        values={
            "final_nodes": deepcopy(graph["nodes"]),
            "final_edges": deepcopy(graph["edges"]),
            "reviewer": " tester ",
        },
        note=" graph contract ",
    )


def test_demo_graph_adapter_contract_and_normalization() -> None:
    adapter = DemoGraphAdapter()
    task = adapter.descriptor.tasks[0]
    assert task.renderer_key == "graph_review"
    assert "structured_graph" in task.capabilities
    assert adapter.dataset_version(TASK_ID).startswith("demo-graphs-")
    assert len(adapter.list_items(TASK_ID)) == 5
    assert [item.id for item in adapter.list_items(TASK_ID, query="连接池耗尽")] == [
        "graph_002"
    ]

    item = adapter.get_item(TASK_ID, "graph_001")
    assert item.source["source_name"] == "示例物流快报"
    assert len(item.prediction["graph_candidate"]["nodes"]) == 3

    normalized = adapter.validate_review(
        TASK_ID,
        "graph_001",
        candidate_patch(adapter),
    )
    assert normalized.values["graph_schema_version"] == "demo-graph-review-v1"
    assert normalized.values["reviewer"] == "tester"
    assert normalized.note == "graph contract"


def test_demo_graph_adapter_rejects_invalid_graphs() -> None:
    adapter = DemoGraphAdapter()

    duplicate_node = candidate_patch(adapter)
    duplicate_node.values["final_nodes"][1]["id"] = "n1"
    with pytest.raises(ValueError, match="duplicate node ID"):
        adapter.validate_review(TASK_ID, "graph_001", duplicate_node)

    missing_endpoint = candidate_patch(adapter)
    missing_endpoint.values["final_edges"][0]["target"] = "missing"
    with pytest.raises(ValueError, match="existing nodes"):
        adapter.validate_review(TASK_ID, "graph_001", missing_endpoint)

    self_loop = candidate_patch(adapter)
    self_loop.values["final_edges"][0]["target"] = "n1"
    with pytest.raises(ValueError, match="self-loop"):
        adapter.validate_review(TASK_ID, "graph_001", self_loop)

    duplicate_relation = candidate_patch(adapter)
    repeated = deepcopy(duplicate_relation.values["final_edges"][0])
    repeated["id"] = "e3"
    duplicate_relation.values["final_edges"].append(repeated)
    with pytest.raises(ValueError, match="duplicate edge relation"):
        adapter.validate_review(TASK_ID, "graph_001", duplicate_relation)

    fake_evidence = candidate_patch(adapter)
    fake_evidence.values["final_nodes"][0]["evidence"] = "原文中不存在的证据"
    with pytest.raises(ValueError, match="verbatim"):
        adapter.validate_review(TASK_ID, "graph_001", fake_evidence)


def test_demo_graph_api_opt_in_save_restore_and_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REVIEW_ENABLE_DEMOS", "1")
    monkeypatch.setattr(main, "store", ReviewStore(tmp_path / "reviews.db"))
    main.register_available_adapters()
    try:
        projects = client.get("/api/projects").json()
        demo = next(project for project in projects if project["id"] == "demo_graphs")
        assert demo["tasks"][0]["renderer_key"] == "graph_review"

        listed = client.get(
            "/api/projects/demo_graphs/tasks/graph-audit/items"
        ).json()
        assert listed["counts"] == {"total": 5, "pending": 5}
        assert len(listed["items"]) == 5

        item = client.get(
            "/api/projects/demo_graphs/tasks/graph-audit/items/graph_001"
        ).json()
        candidate = item["prediction"]["graph_candidate"]
        invalid_edges = deepcopy(candidate["edges"])
        invalid_edges[0]["target"] = "missing"
        invalid = client.put(
            "/api/projects/demo_graphs/tasks/graph-audit/items/graph_001/review",
            json={
                "status": "revised",
                "values": {
                    "final_nodes": candidate["nodes"],
                    "final_edges": invalid_edges,
                    "reviewer": "tester",
                },
                "note": "",
            },
        )
        assert invalid.status_code == 422
        assert "existing nodes" in invalid.json()["detail"]

        payload = {
            "status": "revised",
            "values": {
                "final_nodes": candidate["nodes"],
                "final_edges": candidate["edges"],
                "reviewer": "tester",
            },
            "note": "API graph contract",
        }
        saved = client.put(
            "/api/projects/demo_graphs/tasks/graph-audit/items/graph_001/review",
            json=payload,
        )
        assert saved.status_code == 200
        assert saved.json()["revision"] == 1
        assert saved.json()["values"]["graph_schema_version"] == (
            "demo-graph-review-v1"
        )

        restored = client.get(
            "/api/projects/demo_graphs/tasks/graph-audit/items/graph_001"
        ).json()
        assert restored["status"] == "revised"
        assert len(restored["review"]["values"]["final_nodes"]) == 3

        filtered = client.get(
            "/api/projects/demo_graphs/tasks/graph-audit/items?status=revised"
        ).json()
        assert [entry["id"] for entry in filtered["items"]] == ["graph_001"]
    finally:
        monkeypatch.delenv("REVIEW_ENABLE_DEMOS", raising=False)
        main.register_available_adapters()
