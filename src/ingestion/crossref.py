from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload into a list of PaperRecord objects."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        paper_id = str(item.get("DOI") or item.get("id") or "").strip()
        if not paper_id:
            continue

        raw_title = item.get("title", [])
        if isinstance(raw_title, list) and raw_title:
            title_text = str(raw_title[0])
        else:
            title_text = str(raw_title or "")
        title = normalize_whitespace(re.sub(r"<[^>]+>", "", title_text))
        if not title:
            continue

        raw_abstract = item.get("abstract", "") or ""
        abstract_cleaned = re.sub(r"<[^>]+>", "", str(raw_abstract))
        summary = normalize_whitespace(abstract_cleaned)

        raw_authors = item.get("author", [])
        authors: list[str] = []
        if isinstance(raw_authors, list):
            for a in raw_authors:
                if isinstance(a, dict):
                    given = str(a.get("given", "")).strip()
                    family = str(a.get("family", "")).strip()
                    name = f"{given} {family}".strip()
                    if name:
                        authors.append(name)

        raw_subject = item.get("subject", [])
        if isinstance(raw_subject, list):
            categories = [str(s).strip() for s in raw_subject if str(s).strip()]
        elif raw_subject:
            categories = [str(raw_subject).strip()]
        else:
            categories = []
        primary_category = categories[0] if categories else "General"

        date_parts = item.get("published", {}).get("date-parts", [[]])
        if date_parts and date_parts[0]:
            parts = date_parts[0]
            if len(parts) >= 3:
                published = f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
            elif len(parts) == 2:
                published = f"{parts[0]:04d}-{parts[1]:02d}-01"
            else:
                published = f"{parts[0]:04d}-01-01"
        else:
            published = str(item.get("created", {}).get("date-time", ""))[:10] or "2026-01-01"

        updated = str(item.get("updated", {}).get("date-time", ""))[:10] or published
        abs_url = str(item.get("URL") or f"https://doi.org/{paper_id}")
        pdf_url = abs_url
        comment = f"Crossref record {paper_id}"

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch records from Crossref REST API or fallback to local snapshot."""
    if settings.refresh_source:
        try:
            params = {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            }
            response = requests.get(
                "https://api.crossref.org/works",
                params=params,
                headers={"User-Agent": "Day10DataLab/1.0 (mailto:student@lab.edu)"},
                timeout=15,
            )
            if response.status_code == 200:
                payload = response.json()
                write_json(settings.paths.raw_api_response, payload)
                records = parse_crossref_payload(payload)
                write_json(settings.paths.raw_records_json, [asdict(r) for r in records])
                return records
        except Exception:
            pass

    # Fallback to local raw snapshot
    if settings.paths.raw_records_json.exists():
        return load_raw_records(settings.paths.raw_records_json)

    if settings.paths.raw_api_response.exists():
        payload = read_json(settings.paths.raw_api_response)
        records = parse_crossref_payload(payload)
        write_json(settings.paths.raw_records_json, [asdict(r) for r in records])
        return records

    return []


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load raw records from JSON file and map to PaperRecord list."""
    data = read_json(path)
    return [PaperRecord(**item) for item in data]

