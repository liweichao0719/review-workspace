from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main
from app.store import ReviewStore


client = TestClient(main.app)


def require_fidic() -> None:
    if not any(adapter.descriptor.id == "fidic" for adapter in main.registry.all()):
        pytest.skip("FIDIC RAG source project is not configured")


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_fidic_workspace_has_frozen_dev192_dataset() -> None:
    require_fidic()
    projects = client.get("/api/projects").json()
    assert projects[0]["tasks"][0]["renderer_key"] == "fidic_rag"
    response = client.get("/api/projects/fidic/tasks/rag-clause-audit/items")
    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["total"] == 192
    assert len(body["items"]) == 192
    assert {item["id"] for item in body["items"]} >= {"dev_090", "dev_199", "dev_195"}
    assert body["dataset_version"].startswith("fidic-dev192-")


def test_item_contains_candidate_and_bilingual_context() -> None:
    require_fidic()
    body = client.get(
        "/api/projects/fidic/tasks/rag-clause-audit/items/dev_090"
    ).json()
    candidate = body["prediction"]["context_audit"]
    assert candidate["revised_answer"]
    assert "run_1" not in body["prediction"]
    assert "retrieval" not in body["prediction"]
    context = body["source"]["clause_contexts"][0]
    assert context["text_cn"]
    assert context["text_en"]


def test_review_save_restore_contexts_filter_and_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    require_fidic()
    monkeypatch.setattr(main, "store", ReviewStore(tmp_path / "reviews.db"))
    payload = {
        "status": "revised",
        "values": {
            "final_task_type": "scenario_analysis",
            "final_question_quality": "usable",
            "revised_question": "最终问题",
            "final_answer_consistency": "partially_supported",
            "final_context_refs": ["5.2", "5.1", "5.2"],
            "revised_answer": "最终答案",
            "reviewer": "tester",
        },
        "note": "integration test",
    }
    saved = client.put(
        "/api/projects/fidic/tasks/rag-clause-audit/items/dev_090/review",
        json=payload,
    )
    assert saved.status_code == 200
    assert saved.json()["revision"] == 1
    assert saved.json()["values"]["final_context_refs"] == ["5.1", "5.2"]

    restored = client.get(
        "/api/projects/fidic/tasks/rag-clause-audit/items/dev_090"
    ).json()
    assert restored["status"] == "revised"
    assert restored["review"]["note"] == "integration test"
    refs = [row["context_id"].split(":")[-1] for row in restored["source"]["clause_contexts"]]
    assert refs == ["5.1", "5.2"]

    filtered = client.get(
        "/api/projects/fidic/tasks/rag-clause-audit/items?status=revised"
    ).json()
    assert [row["id"] for row in filtered["items"]] == ["dev_090"]

    exported = client.get("/api/projects/fidic/tasks/rag-clause-audit/export")
    assert exported.status_code == 200
    assert "dev_090" in exported.text
    assert "attachment" in exported.headers["content-disposition"]


def test_rejects_context_outside_corpus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    require_fidic()
    monkeypatch.setattr(main, "store", ReviewStore(tmp_path / "reviews.db"))
    response = client.put(
        "/api/projects/fidic/tasks/rag-clause-audit/items/dev_090/review",
        json={
            "status": "revised",
            "values": {
                "final_task_type": "scenario_analysis",
                "final_question_quality": "usable",
                "revised_question": "问题",
                "final_answer_consistency": "supported",
                "final_context_refs": ["99.99"],
                "revised_answer": "答案",
                "reviewer": "tester",
            },
            "note": "",
        },
    )
    assert response.status_code == 422
    assert "outside the corpus" in response.json()["detail"]


def test_unusable_question_cannot_keep_contexts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    require_fidic()
    monkeypatch.setattr(main, "store", ReviewStore(tmp_path / "reviews.db"))
    response = client.put(
        "/api/projects/fidic/tasks/rag-clause-audit/items/dev_015/review",
        json={
            "status": "revised",
            "values": {
                "final_task_type": "insufficient_evidence",
                "final_question_quality": "unusable",
                "revised_question": "",
                "final_answer_consistency": "insufficient_evidence",
                "final_context_refs": ["8.12"],
                "revised_answer": "缺少前文。",
                "reviewer": "tester",
            },
            "note": "",
        },
    )
    assert response.status_code == 422
    assert "must not keep context" in response.json()["detail"]


def test_rejects_answer_context_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    require_fidic()
    monkeypatch.setattr(main, "store", ReviewStore(tmp_path / "reviews.db"))
    response = client.put(
        "/api/projects/fidic/tasks/rag-clause-audit/items/dev_090/review",
        json={
            "status": "revised",
            "values": {
                "final_task_type": "scenario_analysis",
                "final_question_quality": "usable",
                "revised_question": "问题",
                "final_answer_consistency": "supported",
                "final_context_refs": ["5.2"],
                "revised_answer": "应依第5.1款处理。",
                "reviewer": "tester",
            },
            "note": "",
        },
    )
    assert response.status_code == 422
    assert "exactly cover" in response.json()["detail"]
