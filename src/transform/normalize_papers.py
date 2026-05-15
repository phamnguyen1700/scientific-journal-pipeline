from datetime import datetime, timezone


def clean_openalex_id(value: str | None) -> str | None:
    if not value:
        return None
    return value.rstrip("/").split("/")[-1]


def clean_doi(value: str | None) -> str | None:
    if not value:
        return None
    return value.replace("https://doi.org/", "").lower().strip()


def transform_paper(raw: dict) -> dict:
    source = (raw.get("primary_location") or {}).get("source") or {}
    primary_topic = raw.get("primary_topic") or {}

    return {
        "paper_id": clean_openalex_id(raw.get("id")),
        "openalex_id": raw.get("id"),
        "doi": clean_doi(raw.get("doi")),
        "title": raw.get("title"),
        "display_name": raw.get("display_name"),
        "publication_year": raw.get("publication_year"),
        "publication_date": raw.get("publication_date"),
        "language": raw.get("language"),
        "type": raw.get("type"),
        "cited_by_count": raw.get("cited_by_count", 0),
        "referenced_works_count": raw.get("referenced_works_count", 0),
        "referenced_works": [
            clean_openalex_id(x) for x in raw.get("referenced_works", [])
        ],
        "related_works": [clean_openalex_id(x) for x in raw.get("related_works", [])],
        "abstract_inverted_index": raw.get("abstract_inverted_index"),
        "open_access": raw.get("open_access"),
        "journal": {
            "journal_id": clean_openalex_id(source.get("id")),
            "display_name": source.get("display_name"),
            "type": source.get("type"),
        },
        "primary_topic": {
            "topic_id": clean_openalex_id(primary_topic.get("id")),
            "display_name": primary_topic.get("display_name"),
            "score": primary_topic.get("score"),
        },
        "authors": [
            {
                "author_id": clean_openalex_id((a.get("author") or {}).get("id")),
                "display_name": (a.get("author") or {}).get("display_name"),
                "author_position": a.get("author_position"),
                "is_corresponding": a.get("is_corresponding"),
            }
            for a in raw.get("authorships", [])
        ],
        "keywords": [
            {
                "keyword_id": clean_openalex_id(k.get("id")),
                "display_name": k.get("display_name"),
                "score": k.get("score"),
            }
            for k in raw.get("keywords", [])
        ],
        "topics": [
            {
                "topic_id": clean_openalex_id(t.get("id")),
                "display_name": t.get("display_name"),
                "score": t.get("score"),
            }
            for t in raw.get("topics", [])
        ],
        "counts_by_year": raw.get("counts_by_year", []),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


def transform_authors(raw: dict) -> list[dict]:
    authors = []

    for item in raw.get("authorships", []):
        author = item.get("author") or {}
        author_id = clean_openalex_id(author.get("id"))

        if not author_id:
            continue

        authors.append(
            {
                "author_id": author_id,
                "openalex_id": author.get("id"),
                "display_name": author.get("display_name"),
                "orcid": author.get("orcid"),
                "raw_author_names": [item.get("raw_author_name")],
                "countries": item.get("countries", []),
                "institutions": item.get("institutions", []),
                "last_seen_paper_id": clean_openalex_id(raw.get("id")),
                "updated_at": datetime.now(timezone.utc),
            }
        )

    return authors


def transform_journal(raw: dict) -> dict | None:
    source = (raw.get("primary_location") or {}).get("source") or {}

    journal_id = clean_openalex_id(source.get("id"))
    if not journal_id:
        return None

    return {
        "journal_id": journal_id,
        "openalex_id": source.get("id"),
        "display_name": source.get("display_name"),
        "issn_l": source.get("issn_l"),
        "issn": source.get("issn"),
        "type": source.get("type"),
        "is_oa": source.get("is_oa"),
        "is_in_doaj": source.get("is_in_doaj"),
        "host_organization": source.get("host_organization"),
        "host_organization_name": source.get("host_organization_name"),
        "updated_at": datetime.now(timezone.utc),
    }


def transform_keywords(raw: dict) -> list[dict]:
    return [
        {
            "keyword_id": clean_openalex_id(k.get("id")),
            "openalex_id": k.get("id"),
            "display_name": k.get("display_name"),
            "score": k.get("score"),
            "updated_at": datetime.now(timezone.utc),
        }
        for k in raw.get("keywords", [])
        if k.get("id")
    ]


def transform_topics(raw: dict) -> list[dict]:
    topics = []

    for topic in raw.get("topics", []):
        topics.append(
            {
                "topic_id": clean_openalex_id(topic.get("id")),
                "openalex_id": topic.get("id"),
                "display_name": topic.get("display_name"),
                "score": topic.get("score"),
                "subfield": topic.get("subfield"),
                "field": topic.get("field"),
                "domain": topic.get("domain"),
                "updated_at": datetime.now(timezone.utc),
            }
        )

    return topics
