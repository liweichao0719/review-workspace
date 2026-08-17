"""Build a reproducible retrieval snapshot for the 20-item FIDIC audit pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAG_ROOT = PROJECT_ROOT.parent / "RAG"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/snapshots/fidic_rag_pilot_retrieval.jsonl"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_hit(hit: dict[str, Any], rank: int) -> dict[str, Any]:
    metadata = hit.get("metadata", {})
    return {
        "rank": rank,
        "clause_id": hit.get("clause_id", ""),
        "clause_num": metadata.get("clause_num", ""),
        "context_id": hit.get("context_id", ""),
        "context_clause_num": metadata.get("context_clause_num", ""),
        "title_cn": metadata.get("title_cn", ""),
        "title_en": metadata.get("title_en", ""),
        "text": hit.get("text", ""),
        "source": hit.get("source", ""),
        "matched_sources": hit.get("matched_sources", []),
        "score": hit.get("score"),
        "rrf_score": hit.get("rrf_score"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rag-root", type=Path, default=DEFAULT_RAG_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="cpu")
    parser.add_argument("--dense-k", type=int, default=20)
    parser.add_argument("--sparse-k", type=int, default=20)
    parser.add_argument("--display-k", type=int, default=10)
    args = parser.parse_args()

    rag_root = args.rag_root.resolve()
    sys.path.insert(0, str(rag_root))
    from src.fidic.retriever import Retriever

    manifest_path = rag_root / "results/dev_audit_layer2_prep/pilot_manifest.jsonl"
    bm25_path = rag_root / "data/fidic/clauses/bm25_cn_v2.pkl"
    manifest = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    retriever = Retriever(device=args.device)
    records: list[dict[str, Any]] = []
    for index, item in enumerate(manifest, start=1):
        result = retriever.search(
            item["question"],
            dense_k=args.dense_k,
            sparse_k=args.sparse_k,
            rrf_k=60,
            include_english=True,
        )
        channels = {
            name: [
                normalize_hit(hit, rank)
                for rank, hit in enumerate(result[name][: args.display_k], start=1)
            ]
            for name in ("dense_cn", "dense_en", "bm25_cn", "union")
        }
        records.append(
            {
                "snapshot_version": "fidic-rag-retrieval-v1",
                "sample_id": item["sample_id"],
                "question_sha256": hashlib.sha256(
                    item["question"].encode("utf-8")
                ).hexdigest(),
                "retrieval_config": {
                    "dense_k": args.dense_k,
                    "sparse_k": args.sparse_k,
                    "display_k": args.display_k,
                    "rrf_k": 60,
                    "include_english": True,
                    "device": args.device,
                },
                "channels": channels,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        print(f"[{index:02d}/{len(manifest)}] {item['sample_id']}", flush=True)

    header = {
        "snapshot_version": "fidic-rag-retrieval-v1",
        "manifest_sha256": sha256(manifest_path),
        "bm25_sha256": sha256(bm25_path),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(header, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(args.output)
    print(f"Wrote {args.output} ({len(records)} items)")


if __name__ == "__main__":
    main()
