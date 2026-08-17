from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main
from app.adapters.demo_articles import DemoArticleAdapter, TASK_ID
from app.models import ReviewPatch
from app.store import ReviewStore


client = TestClient(main.app)


def test_demo_article_adapter_has_independent_schema_and_validation() -> None:
    adapter = DemoArticleAdapter()
    task = adapter.descriptor.tasks[0]
    assert task.renderer_key == "article_review"
    assert adapter.dataset_version(TASK_ID).startswith("demo-articles-")
    assert len(adapter.list_items(TASK_ID)) == 10
    assert [item.id for item in adapter.list_items(TASK_ID, query="钓鱼邮件")] == [
        "article_004"
    ]

    item = adapter.get_item(TASK_ID, "article_001")
    assert item.source["source_name"] == "示例物流周报"
    assert item.prediction["article_triage"]["decision"] == "include"

    normalized = adapter.validate_review(
        TASK_ID,
        "article_001",
        ReviewPatch(
            status="revised",
            values={
                "decision": "include",
                "relevance": "high",
                "final_tags": ["供应链", "物流", "供应链"],
                "evidence_quote": "东部港口暂停了两个夜间装卸窗口",
                "decision_reason": "存在明确的物流影响。",
                "reviewer": "tester",
            },
            note="adapter contract",
        ),
    )
    assert normalized.values["final_tags"] == ["供应链", "物流"]

    with pytest.raises(ValueError, match="verbatim"):
        adapter.validate_review(
            TASK_ID,
            "article_001",
            ReviewPatch(
                status="revised",
                values={
                    "decision": "include",
                    "relevance": "high",
                    "final_tags": ["供应链"],
                    "evidence_quote": "正文里不存在的摘录",
                    "decision_reason": "",
                    "reviewer": "tester",
                },
                note="",
            ),
        )


def test_demo_article_api_opt_in_save_restore_and_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REVIEW_ENABLE_DEMOS", "1")
    monkeypatch.setattr(main, "store", ReviewStore(tmp_path / "reviews.db"))
    main.register_available_adapters()
    try:
        projects = client.get("/api/projects").json()
        demo = next(project for project in projects if project["id"] == "demo_articles")
        assert demo["tasks"][0]["renderer_key"] == "article_review"

        listed = client.get(
            "/api/projects/demo_articles/tasks/article-triage/items"
        ).json()
        assert listed["counts"] == {"total": 10, "pending": 10}
        assert len(listed["items"]) == 10

        invalid = client.put(
            "/api/projects/demo_articles/tasks/article-triage/items/article_001/review",
            json={
                "status": "revised",
                "values": {
                    "decision": "include",
                    "relevance": "high",
                    "final_tags": ["供应链"],
                    "evidence_quote": "虚构摘录",
                    "decision_reason": "",
                    "reviewer": "tester",
                },
                "note": "",
            },
        )
        assert invalid.status_code == 422
        assert "article body" in invalid.json()["detail"]

        payload = {
            "status": "revised",
            "values": {
                "decision": "include",
                "relevance": "high",
                "final_tags": ["供应链", "物流"],
                "evidence_quote": "东部港口暂停了两个夜间装卸窗口",
                "decision_reason": "存在短期物流中断。",
                "reviewer": "tester",
            },
            "note": "API contract",
        }
        saved = client.put(
            "/api/projects/demo_articles/tasks/article-triage/items/article_001/review",
            json=payload,
        )
        assert saved.status_code == 200
        assert saved.json()["revision"] == 1

        restored = client.get(
            "/api/projects/demo_articles/tasks/article-triage/items/article_001"
        ).json()
        assert restored["status"] == "revised"
        assert restored["review"]["values"]["decision"] == "include"

        filtered = client.get(
            "/api/projects/demo_articles/tasks/article-triage/items?status=revised"
        ).json()
        assert [item["id"] for item in filtered["items"]] == ["article_001"]
    finally:
        monkeypatch.delenv("REVIEW_ENABLE_DEMOS", raising=False)
        main.register_available_adapters()
