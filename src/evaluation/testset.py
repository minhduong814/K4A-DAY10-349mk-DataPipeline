from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: Path | str) -> list[dict[str, Any]]:
    """Build a standardized benchmark evaluation test set of 10 items across 4 task categories."""
    if df.empty:
        raise ValueError("Cannot build test set from an empty DataFrame.")

    total_needed = 10
    questions: list[dict[str, Any]] = []

    # Map question formats and ground truth extractions
    specs = [
        ("summary", "What is the summary of the paper '{title}'?", lambda r: first_sentence(str(r["summary"]))),
        ("summary", "What is the summary of the paper '{title}'?", lambda r: first_sentence(str(r["summary"]))),
        ("summary", "What is the summary of the paper '{title}'?", lambda r: first_sentence(str(r["summary"]))),
        ("authors", "Who authored the paper '{title}'?", lambda r: str(r["authors_joined"])),
        ("authors", "Who authored the paper '{title}'?", lambda r: str(r["authors_joined"])),
        ("authors", "Who authored the paper '{title}'?", lambda r: str(r["authors_joined"])),
        ("date", "When was the paper '{title}' published?", lambda r: str(r["published"])),
        ("date", "When was the paper '{title}' published?", lambda r: str(r["published"])),
        ("categories", "What categories does the paper '{title}' belong to?", lambda r: str(r["categories_joined"])),
        ("categories", "What categories does the paper '{title}' belong to?", lambda r: str(r["categories_joined"])),
    ]

    n_rows = len(df)
    for idx, (q_type, template, gt_func) in enumerate(specs[:total_needed]):
        row = df.iloc[idx % n_rows]
        title = str(row["title"]).strip()
        paper_id = str(row["paper_id"]).strip()
        ground_truth = gt_func(row)
        question_text = template.format(title=title)

        questions.append(
            {
                "id": f"eval_{idx+1:03d}",
                "question_type": q_type,
                "question": question_text,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    if output_path:
        write_json(Path(output_path), questions)

    return questions
