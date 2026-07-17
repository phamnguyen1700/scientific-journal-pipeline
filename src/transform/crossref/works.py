import re
from datetime import date

from src.extract.crossref_extractor import normalize_doi


def first_value(value):
    if isinstance(value, list) and value:
        return value[0]
    return value


def date_parts_to_year(value) -> int | None:
    date_parts = (value or {}).get("date-parts") or []
    if not date_parts or not date_parts[0]:
        return None
    return date_parts[0][0]


def date_parts_to_date(value) -> str | None:
    date_parts = (value or {}).get("date-parts") or []
    if not date_parts or not date_parts[0]:
        return None

    parts = date_parts[0]
    year = parts[0]
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1

    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def normalize_text(value: str | None) -> str | None:
    if not value:
        return None

    return re.sub(r"\s+", " ", value).strip().lower()


def compact_title(value: str | None) -> str | None:
    normalized = normalize_text(value)
    if not normalized:
        return None

    return re.sub(r"[^a-z0-9]+", "", normalized)


def author_display_name(author: dict) -> str:
    given = author.get("given") or ""
    family = author.get("family") or ""
    name = " ".join(part for part in (given, family) if part).strip()
    return name or author.get("name") or ""


def extract_crossref_summary(raw: dict) -> dict:
    message = raw.get("message") or {}
    issued = message.get("published") or message.get("issued") or {}

    license_urls = [
        item.get("URL")
        for item in message.get("license", [])
        if item.get("URL")
    ]
    links = [
        item.get("URL")
        for item in message.get("link", [])
        if item.get("URL")
    ]

    return {
        "doi": normalize_doi(message.get("DOI")),
        "source_record_url": message.get("URL"),
        "title": first_value(message.get("title")),
        "type": message.get("type"),
        "publisher": message.get("publisher"),
        "publisher_location": message.get("publisher-location"),
        "container_titles": message.get("container-title") or [],
        "issn": message.get("ISSN") or [],
        "isbn": message.get("ISBN") or [],
        "publication_year": date_parts_to_year(issued),
        "publication_date": date_parts_to_date(issued),
        "page": message.get("page"),
        "author_names": [
            name
            for name in (author_display_name(author) for author in message.get("author", []))
            if name
        ],
        "license_urls": license_urls,
        "links": links,
        "reference_count": (
            message.get("reference-count")
            if message.get("reference-count") is not None
            else message.get("references-count")
        ),
        "cited_by_count": message.get("is-referenced-by-count"),
        "member": message.get("member"),
        "prefix": message.get("prefix"),
        "deposited_at": (message.get("deposited") or {}).get("date-time"),
        "indexed_at": (message.get("indexed") or {}).get("date-time"),
    }


def compare_crossref_to_paper(paper: dict, summary: dict) -> dict:
    issues = []
    score = 1.0

    paper_doi = normalize_doi(paper.get("doi"))
    crossref_doi = normalize_doi(summary.get("doi"))
    if paper_doi and crossref_doi and paper_doi != crossref_doi:
        issues.append(
            {
                "field": "doi",
                "core_value": paper_doi,
                "crossref_value": crossref_doi,
                "severity": "high",
            }
        )
        score -= 0.5

    paper_title = compact_title(paper.get("title"))
    crossref_title = compact_title(summary.get("title"))
    if paper_title and crossref_title and paper_title != crossref_title:
        issues.append(
            {
                "field": "title",
                "core_value": paper.get("title"),
                "crossref_value": summary.get("title"),
                "severity": "medium",
            }
        )
        score -= 0.25

    paper_year = paper.get("publication_year")
    crossref_year = summary.get("publication_year")
    if paper_year and crossref_year and int(paper_year) != int(crossref_year):
        issues.append(
            {
                "field": "publication_year",
                "core_value": paper_year,
                "crossref_value": crossref_year,
                "severity": "medium",
            }
        )
        score -= 0.15

    score = max(0.0, min(1.0, score))
    status = "conflict" if any(item["severity"] in {"high", "medium"} for item in issues) else "matched"

    return {
        "match_status": status,
        "match_method": "doi",
        "confidence_score": score,
        "issues": issues,
    }
