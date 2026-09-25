from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
from great_expectations.expectations import (
    ExpectColumnValueLengthsToBeBetween,
    ExpectColumnValuesToBeUnique,
    ExpectColumnValuesToNotBeNull,
    ExpectTableRowCountToBeBetween,
)
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Execute Great Expectations 1.x data quality checks on the provided DataFrame."""
    check_details = []
    overall_success = True

    try:
        context = gx.get_context(mode="ephemeral")
        data_source = context.data_sources.add_pandas(name=f"papers_source_{report_name}")
        data_asset = data_source.add_dataframe_asset(name="papers_asset")
        batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
        batch = batch_def.get_batch(batch_parameters={"dataframe": df})

        suite = gx.ExpectationSuite(name=f"papers_suite_{report_name}")
        expectations = [
            ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
            ExpectColumnValuesToNotBeNull(column="paper_id"),
            ExpectColumnValuesToNotBeNull(column="title"),
            ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
            ExpectColumnValuesToBeUnique(column="paper_id"),
            ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
        ]
        for exp in expectations:
            suite.add_expectation(exp)

        validation_results = batch.validate(suite)
        overall_success = bool(validation_results.success)

        for res in validation_results.results:
            exp_type = getattr(res.expectation_config, "type", "UnknownExpectation")
            kwargs = getattr(res.expectation_config, "kwargs", {})
            col = kwargs.get("column", "table")
            success = bool(res.success)
            check_details.append(
                {
                    "expectation": exp_type,
                    "target": col,
                    "success": success,
                    "result": getattr(res, "result", {}),
                }
            )
    except Exception:
        # Fallback manual validation if GX encounters schema mismatch on corrupted data
        overall_success = True
        row_count_ok = 5 <= len(df) <= 5000
        overall_success = overall_success and row_count_ok
        check_details.append({"expectation": "ExpectTableRowCountToBeBetween", "target": "table", "success": row_count_ok})

        for col in ["paper_id", "title", "text_for_embedding"]:
            col_not_null = col in df.columns and df[col].notna().all() and (df[col].astype(str).str.strip() != "").all()
            overall_success = overall_success and col_not_null
            check_details.append({"expectation": "ExpectColumnValuesToNotBeNull", "target": col, "success": bool(col_not_null)})

        unique_ids = "paper_id" in df.columns and df["paper_id"].is_unique
        overall_success = overall_success and unique_ids
        check_details.append({"expectation": "ExpectColumnValuesToBeUnique", "target": "paper_id", "success": bool(unique_ids)})

        summary_len_ok = "summary" in df.columns and (df["summary"].astype(str).str.len() >= 30).all()
        overall_success = overall_success and summary_len_ok
        check_details.append({"expectation": "ExpectColumnValueLengthsToBeBetween", "target": "summary", "success": bool(summary_len_ok)})

    passed_checks = sum(1 for c in check_details if c["success"])
    failed_checks = len(check_details) - passed_checks

    report_payload = {
        "report_name": report_name,
        "success": bool(overall_success),
        "total_checks": len(check_details),
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "details": check_details,
    }

    output_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    if report_name == "baseline":
        output_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        output_path = settings.paths.corrupted_quality_report
    write_json(output_path, report_payload)

    return report_payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Calculate data freshness metrics against SLA thresholds and export JSON report."""
    latest_published = str(df["published"].max()) if not df.empty and "published" in df.columns else "N/A"
    oldest_published = str(df["published"].min()) if not df.empty and "published" in df.columns else "N/A"
    threshold = settings.freshness_threshold_days
    stale_rows = int((df["age_days"] > threshold).sum()) if not df.empty and "age_days" in df.columns else 0
    total_rows = len(df)
    stale_ratio = float(stale_rows / total_rows) if total_rows > 0 else 0.0
    is_fresh = bool(stale_ratio <= 0.25)

    report = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_threshold_days": threshold,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "is_fresh": is_fresh,
    }
    if report_path:
        write_json(Path(report_path), report)
    return report
