from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.adapters.base import ReviewAdapter
from app.adapters.demo_articles import DemoArticleAdapter
from app.adapters.demo_csv_articles import DemoCsvArticleAdapter
from app.adapters.demo_graphs import DemoGraphAdapter
from app.adapters.demo_sqlite_articles import DemoSqliteArticleAdapter
from app.adapters.fidic_rag import FidicRagAdapter
from app.models import ReviewPatch
from tests.support.adapter_contract import (
    AdapterContractCase,
    assert_review_adapter_contract,
)


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
ARTICLE_TASK = "article-triage"
GRAPH_TASK = "graph-audit"
FIDIC_TASK = "rag-clause-audit"


def article_patch(evidence: str) -> ReviewPatch:
    return ReviewPatch(
        status="revised",
        values={
            "decision": "include",
            "relevance": "high",
            "final_tags": ["契约测试", "数据源"],
            "evidence_quote": evidence,
            "decision_reason": "存在明确且可核对的事件。",
            "reviewer": "contract-test",
        },
        note="adapter contract",
    )


def graph_patch(adapter: ReviewAdapter, item_id: str) -> ReviewPatch:
    graph = adapter.get_item(GRAPH_TASK, item_id).prediction["graph_candidate"]
    return ReviewPatch(
        status="revised",
        values={
            "final_nodes": graph["nodes"],
            "final_edges": graph["edges"],
            "reviewer": "contract-test",
        },
        note="adapter contract",
    )


def fidic_patch(adapter: ReviewAdapter, item_id: str) -> ReviewPatch:
    return ReviewPatch(
        status="revised",
        values={
            "final_task_type": "scenario_analysis",
            "final_question_quality": "usable",
            "revised_question": "最终问题",
            "final_answer_consistency": "partially_supported",
            "final_context_refs": ["5.2", "5.1"],
            "revised_answer": "最终答案",
            "reviewer": "contract-test",
        },
        note="adapter contract",
    )


def materialize_sqlite(path: Path) -> None:
    seed = (FIXTURES / "demo_articles.sqlite.sql").read_text(encoding="utf-8")
    with sqlite3.connect(path) as connection:
        connection.executescript(seed)


def test_jsonl_article_adapter_satisfies_shared_contract() -> None:
    assert_review_adapter_contract(
        AdapterContractCase(
            make_adapter=DemoArticleAdapter,
            task_id=ARTICLE_TASK,
            item_id="article_001",
            valid_patch=lambda _adapter, _item_id: article_patch(
                "东部港口暂停了两个夜间装卸窗口"
            ),
        )
    )


def test_json_graph_adapter_satisfies_shared_contract() -> None:
    assert_review_adapter_contract(
        AdapterContractCase(
            make_adapter=DemoGraphAdapter,
            task_id=GRAPH_TASK,
            item_id="graph_001",
            valid_patch=graph_patch,
        )
    )


def test_csv_article_adapter_satisfies_shared_contract() -> None:
    assert_review_adapter_contract(
        AdapterContractCase(
            make_adapter=DemoCsvArticleAdapter,
            task_id=ARTICLE_TASK,
            item_id="csv_001",
            valid_patch=lambda _adapter, _item_id: article_patch(
                "三辆公交车的电池温度传感器读数偏高"
            ),
        )
    )


def test_sqlite_article_adapter_satisfies_shared_contract(tmp_path: Path) -> None:
    database = tmp_path / "source.db"
    materialize_sqlite(database)
    assert_review_adapter_contract(
        AdapterContractCase(
            make_adapter=lambda: DemoSqliteArticleAdapter(database),
            task_id=ARTICLE_TASK,
            item_id="sql_001",
            valid_patch=lambda _adapter, _item_id: article_patch(
                "备用发电机在二十秒内启动"
            ),
        )
    )


def test_fidic_adapter_satisfies_shared_contract() -> None:
    try:
        FidicRagAdapter()
    except FileNotFoundError:
        pytest.skip("FIDIC RAG source project is not configured")
    assert_review_adapter_contract(
        AdapterContractCase(
            make_adapter=FidicRagAdapter,
            task_id=FIDIC_TASK,
            item_id="dev_090",
            valid_patch=fidic_patch,
        )
    )


def test_csv_and_sqlite_versions_follow_source_content(tmp_path: Path) -> None:
    csv_source = tmp_path / "articles.csv"
    csv_text = (FIXTURES / "demo_articles.csv").read_text(encoding="utf-8")
    csv_source.write_text(csv_text, encoding="utf-8")
    csv_before = DemoCsvArticleAdapter(csv_source).dataset_version(ARTICLE_TASK)
    csv_source.write_text(
        csv_text.replace("新能源公交电池巡检", "纯电公交电池巡检", 1),
        encoding="utf-8",
    )
    csv_after = DemoCsvArticleAdapter(csv_source).dataset_version(ARTICLE_TASK)
    assert csv_after != csv_before

    database = tmp_path / "source.db"
    materialize_sqlite(database)
    sqlite_before = DemoSqliteArticleAdapter(database).dataset_version(ARTICLE_TASK)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE articles SET title = ? WHERE id = ?",
            ("冷库断电与备用电源启动", "sql_001"),
        )
    sqlite_after = DemoSqliteArticleAdapter(database).dataset_version(ARTICLE_TASK)
    assert sqlite_after != sqlite_before


def test_format_adapters_report_clear_source_errors(tmp_path: Path) -> None:
    malformed_csv = tmp_path / "missing-columns.csv"
    malformed_csv.write_text("id,title\nrow_1,broken\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        DemoCsvArticleAdapter(malformed_csv)

    empty_database = tmp_path / "empty.db"
    with sqlite3.connect(empty_database):
        pass
    with pytest.raises(ValueError, match="invalid demo SQLite"):
        DemoSqliteArticleAdapter(empty_database)
