from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Simulate 6 realistic production data corruption patterns:
    1. Drop 20% newest records (simulating pipeline truncation / missing fresh data).
    2. Blank out summary in select records (simulating scraping failure / empty payload).
    3. Inject random noise into summary (simulating OCR/encoding errors).
    4. Truncate title to < 8 chars (simulating field cut-off).
    5. Age date by 365 days (simulating stale cache).
    6. Duplicate select rows (simulating duplicate webhook / replay attack).
    """
    corrupted_df = df.copy()
    logs: list[dict[str, Any]] = []

    if corrupted_df.empty:
        if output_log_path:
            write_json(Path(output_log_path), logs)
        return corrupted_df

    # 1. Drop 20% newest records
    num_to_drop = max(1, int(len(corrupted_df) * 0.20))
    if "published" in corrupted_df.columns:
        corrupted_df = corrupted_df.sort_values(by="published", ascending=False).reset_index(drop=True)
    dropped_ids = corrupted_df.iloc[:num_to_drop]["paper_id"].tolist()
    corrupted_df = corrupted_df.iloc[num_to_drop:].reset_index(drop=True)
    logs.append(
        {
            "corruption_type": "drop_latest_records",
            "count": num_to_drop,
            "dropped_paper_ids": dropped_ids,
            "description": f"Dropped top {num_to_drop} newest records.",
        }
    )

    # 2. Blank out summary on selected rows
    blank_indices = [0, min(1, len(corrupted_df) - 1)] if len(corrupted_df) > 1 else [0]
    blanked_ids = []
    for idx in set(blank_indices):
        paper_id = corrupted_df.at[idx, "paper_id"]
        corrupted_df.at[idx, "summary"] = ""
        corrupted_df.at[idx, "summary_chars"] = 0
        blanked_ids.append(paper_id)
    logs.append(
        {
            "corruption_type": "blank_summary",
            "count": len(blanked_ids),
            "affected_paper_ids": blanked_ids,
            "description": "Erased summary text for selected rows.",
        }
    )

    # 3. Inject noise into summary on selected rows
    noise_indices = [min(2, len(corrupted_df) - 1), min(3, len(corrupted_df) - 1)]
    noisy_ids = []
    for idx in set(noise_indices):
        paper_id = corrupted_df.at[idx, "paper_id"]
        corrupted_df.at[idx, "summary"] = f"### CORRUPTED NOISE %$#@&*! ### {corrupted_df.at[idx, 'summary']}"
        corrupted_df.at[idx, "summary_chars"] = len(corrupted_df.at[idx, "summary"])
        noisy_ids.append(paper_id)
    logs.append(
        {
            "corruption_type": "inject_noise",
            "count": len(noisy_ids),
            "affected_paper_ids": noisy_ids,
            "description": "Injected gibberish noise tokens into summary.",
        }
    )

    # 4. Truncate title to < 8 chars
    truncate_indices = [min(4, len(corrupted_df) - 1)]
    truncated_ids = []
    for idx in set(truncate_indices):
        paper_id = corrupted_df.at[idx, "paper_id"]
        corrupted_df.at[idx, "title"] = "Bad..."
        truncated_ids.append(paper_id)
    logs.append(
        {
            "corruption_type": "truncate_title",
            "count": len(truncated_ids),
            "affected_paper_ids": truncated_ids,
            "description": "Truncated title string to less than 8 characters.",
        }
    )

    # 5. Stale date (shift published date backwards by 365 days for ~30% of records to trigger SLA breach)
    stale_indices = [idx for idx in range(5, min(12, len(corrupted_df)))]
    stale_ids = []
    for idx in set(stale_indices):
        paper_id = corrupted_df.at[idx, "paper_id"]
        pub_str = str(corrupted_df.at[idx, "published"])
        try:
            old_year = int(pub_str[:4])
            stale_pub = f"{old_year - 1}{pub_str[4:]}"
        except Exception:
            stale_pub = "2020-01-01"
        corrupted_df.at[idx, "published"] = stale_pub
        corrupted_df.at[idx, "age_days"] = int(corrupted_df.at[idx, "age_days"]) + 365
        stale_ids.append(paper_id)
    logs.append(
        {
            "corruption_type": "stale_date",
            "count": len(stale_ids),
            "affected_paper_ids": stale_ids,
            "description": "Shifted publication date back by 365 days.",
        }
    )

    # 6. Duplicate rows
    dup_rows = corrupted_df.iloc[[0, min(1, len(corrupted_df) - 1)]].copy()
    corrupted_df = pd.concat([corrupted_df, dup_rows], ignore_index=True)
    logs.append(
        {
            "corruption_type": "duplicate_rows",
            "count": len(dup_rows),
            "duplicated_paper_ids": dup_rows["paper_id"].tolist(),
            "description": "Duplicated records to induce uniqueness violations.",
        }
    )

    # Rebuild text_for_embedding for all rows based on corrupted values
    rebuilt_texts = []
    for _, row in corrupted_df.iterrows():
        rebuilt_texts.append(
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Published: {row['published']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Summary: {row['summary']}".strip()
        )
    corrupted_df["text_for_embedding"] = rebuilt_texts

    if output_log_path:
        write_json(Path(output_log_path), logs)

    return corrupted_df
