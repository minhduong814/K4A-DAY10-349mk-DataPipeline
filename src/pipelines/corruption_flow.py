from __future__ import annotations

from datetime import UTC, datetime
import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.phase1 import main as run_phase1
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Run full Phase 2 Corruption, Degradation Measurement, Repair, and Comparison flow."""
    print("=" * 70)
    print(">>> Starting Phase 2: Data Corruption Suite, Repair & Impact Analysis")
    print("=" * 70)

    settings = load_settings()

    # Ensure baseline artifacts exist
    if not settings.paths.clean_json.exists() or not settings.paths.baseline_metrics.exists():
        print("[!] Baseline artifacts not found. Running Phase 1 first...")
        run_phase1()

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.read_json(settings.paths.clean_json)
    print(f"[*] Loaded clean baseline data: {len(clean_df)} records.")

    # 1. Synthetic Data Corruption
    print("[*] Injecting 6 data corruption scenarios into clean dataset...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    print(f"[*] Corrupted data generated: {len(corrupted_df)} records. Log saved to {settings.paths.corruption_log.name}.")

    # 2. Quality Checks & Freshness on Corrupted Data
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness_report.json"
    )
    print(f"[*] Corrupted Data Quality: status={corrupted_quality['success']} (passed {corrupted_quality['passed_checks']}/{corrupted_quality['total_checks']})")
    print(f"[*] Corrupted Freshness: is_fresh={corrupted_freshness['is_fresh']} (stale_ratio={corrupted_freshness['stale_ratio']:.1%})")

    # 3. Build Corrupted Index & Evaluate (Observing Silent Failure)
    print(f"[*] Building corrupted ChromaDB index '{settings.corrupted_collection_name}'...")
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
    print("[*] Evaluating RAG performance on corrupted dataset...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    c_hit = corrupted_bundle.summary.get("retrieval_hit_rate", 0.0)
    c_f1 = corrupted_bundle.summary.get("mean_token_f1", 0.0)
    print(f"[!] Corrupted RAG metrics: Hit Rate = {c_hit:.1%}, Token F1 = {c_f1:.4f}")

    # 4. Idempotent Repair from Raw Source
    print("\n[*] Initiating Idempotent Repair from raw preservation layer...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, datetime.now(UTC))
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    print(f"[*] Clean data reconstructed from raw backup: {len(repaired_df)} records.")

    # 5. Quality Checks & Freshness on Repaired Data
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "repaired_freshness_report.json"
    )
    print(f"[*] Repaired Data Quality: status={repaired_quality['success']} ({repaired_quality['passed_checks']}/{repaired_quality['total_checks']} passed)")
    print(f"[*] Repaired Freshness: is_fresh={repaired_freshness['is_fresh']} (stale_ratio={repaired_freshness['stale_ratio']:.1%})")

    # 6. Build Repaired Index & Evaluate
    print(f"[*] Re-indexing repaired data into ChromaDB '{settings.repaired_collection_name}'...")
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
    print("[*] Evaluating RAG performance on repaired dataset...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    r_hit = repaired_bundle.summary.get("retrieval_hit_rate", 0.0)
    r_f1 = repaired_bundle.summary.get("mean_token_f1", 0.0)
    print(f"[*] Repaired RAG metrics: Hit Rate = {r_hit:.1%}, Token F1 = {r_f1:.4f}")

    # 7. Generate Comparison Report
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"\n[+] Comparison report generated at: {settings.paths.comparison_report}")

    # 8. Print 3-state comparison table
    b_hit = baseline_metrics.get("retrieval_hit_rate", 0.0)
    b_f1 = baseline_metrics.get("mean_token_f1", 0.0)
    b_acc = baseline_metrics.get("judge_accuracy", 0.0)
    c_acc = corrupted_bundle.summary.get("judge_accuracy", 0.0)
    r_acc = repaired_bundle.summary.get("judge_accuracy", 0.0)

    print("\n" + "=" * 70)
    print("           BẢNG ĐỐI CHIẾU 3 TRẠNG THÁI HIỆU NĂNG RAG PIPELINE")
    print("=" * 70)
    print(f"{'Tiêu chí':<25} | {'Baseline (Sạch)':<16} | {'Corrupted (Lỗi)':<16} | {'Repaired (Phục Hồi)':<16}")
    print("-" * 79)
    print(f"{'Data Quality (GX 1.x)':<25} | {'PASS':<16} | {('PASS' if corrupted_quality['success'] else 'FAIL'):<16} | {('PASS' if repaired_quality['success'] else 'FAIL'):<16}")
    print(f"{'Freshness Status':<25} | {'Fresh':<16} | {('Fresh' if corrupted_freshness['is_fresh'] else 'Stale (SLA Fail)'):<16} | {('Fresh' if repaired_freshness['is_fresh'] else 'Stale'):<16}")
    print(f"{'Retrieval Hit Rate':<25} | {b_hit:<16.1%} | {c_hit:<16.1%} | {r_hit:<16.1%}")
    print(f"{'Mean Token F1':<25} | {b_f1:<16.4f} | {c_f1:<16.4f} | {r_f1:<16.4f}")
    print(f"{'LLM Judge Accuracy':<25} | {b_acc:<16.1%} | {c_acc:<16.1%} | {r_acc:<16.1%}")
    print("=" * 70)
    print(">>> Phase 2 completed successfully!")


if __name__ == "__main__":
    main()
