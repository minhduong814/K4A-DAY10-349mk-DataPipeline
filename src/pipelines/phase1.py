from __future__ import annotations

from datetime import UTC, datetime

from core.config import load_settings
from core.utils import write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Run Phase 1 baseline pipeline end-to-end:
    1. Load configuration and project paths.
    2. Ingest raw records (Crossref API with offline snapshot fallback).
    3. Clean and normalize data, constructing text_for_embedding.
    4. Save clean CSV and JSON artifacts.
    5. Run Great Expectations 1.x quality checks and Freshness SLA monitoring.
    6. Generate benchmark evaluation test set.
    7. Build ChromaDB vector collection and compute embeddings.
    8. Evaluate retrieval hit rate and QA answer accuracy.
    9. Export Phase 1 Markdown report.
    """
    print("=" * 60)
    print(">>> Starting Phase 1: Baseline Data Pipeline & Observability")
    print("=" * 60)

    settings = load_settings()

    # 1. Fetch raw records
    records = fetch_source_records(settings)
    print(f"[*] Ingested {len(records)} raw records from {settings.source_api}.")

    # 2. Clean data
    run_date = datetime.now(UTC)
    df = build_clean_dataframe(records, run_date)
    print(f"[*] Cleaned and validated {len(df)} records.")

    # 3. Save clean artifacts
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))
    print(f"[*] Clean artifacts saved to {settings.paths.clean_csv.name} & {settings.paths.clean_json.name}.")

    # 4. Data Observability (GX 1.x & Freshness)
    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    print(f"[*] Data Quality Check (GX 1.x): status={quality['success']} ({quality['passed_checks']}/{quality['total_checks']} passed)")
    print(f"[*] Freshness Monitoring: is_fresh={freshness['is_fresh']} (stale_ratio={freshness['stale_ratio']:.1%})")

    # 5. Build Benchmark Test Set
    test_set = build_test_set(df, settings.paths.eval_testset)
    print(f"[*] Generated benchmark test set with {len(test_set)} questions.")

    # 6. Build ChromaDB Index
    print(f"[*] Building ChromaDB index '{settings.baseline_collection_name}'...")
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    print(f"[*] Indexed {len(df)} documents successfully.")

    # 7. Evaluation
    print("[*] Running pipeline evaluation...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    hit_rate = bundle.summary.get("retrieval_hit_rate", 0.0)
    token_f1 = bundle.summary.get("mean_token_f1", 0.0)
    judge_acc = bundle.summary.get("judge_accuracy", 0.0)
    print(f"[*] Evaluation completed: Hit Rate = {hit_rate:.1%}, Token F1 = {token_f1:.4f}, Judge Acc = {judge_acc:.1%}")

    # 8. Generate Report
    source_summary = {
        "raw_records": len(records),
        "clean_records": len(df),
        "source_api": settings.source_api,
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )
    print(f"[+] Phase 1 Report exported: {settings.paths.baseline_report}")
    print("=" * 60)
    print(">>> Phase 1 completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
