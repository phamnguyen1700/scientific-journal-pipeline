def clean_openalex_id(value: str | None) -> str | None:
    if not value:
        return None
    return value.rstrip("/").split("/")[-1]


def clean_doi(value: str | None) -> str | None:
    if not value:
        return None
    return value.replace("https://doi.org/", "").lower().strip()


def reconstruct_abstract(inverted_index: dict | None) -> str | None:
    if not inverted_index:
        return None

    positioned_words = []
    for word, positions in inverted_index.items():
        for position in positions:
            positioned_words.append((position, word))

    if not positioned_words:
        return None

    return " ".join(word for _, word in sorted(positioned_words))


def format_page(biblio: dict) -> str | None:
    first_page = biblio.get("first_page")
    last_page = biblio.get("last_page")

    if first_page and last_page:
        return f"{first_page}-{last_page}"

    return first_page or last_page


def transform_taxonomy_node(node: dict | None) -> dict | None:
    if not node:
        return None

    source_record_id = clean_openalex_id(node.get("id"))
    display_name = node.get("display_name")

    if not source_record_id and not display_name:
        return None

    return {
        "source_record_id": source_record_id,
        "source_record_url": node.get("id"),
        "display_name": display_name,
    }


def transform_topic_node(topic: dict | None) -> dict | None:
    if not topic:
        return None

    source_record_id = clean_openalex_id(topic.get("id"))
    display_name = topic.get("display_name")

    if not source_record_id and not display_name:
        return None

    return {
        "source_record_id": source_record_id,
        "source_record_url": topic.get("id"),
        "display_name": display_name,
        "score": topic.get("score"),
        "count": topic.get("count"),
        "domain": transform_taxonomy_node(topic.get("domain")),
        "field": transform_taxonomy_node(topic.get("field")),
        "subfield": transform_taxonomy_node(topic.get("subfield")),
    }


def transform_paper(raw: dict) -> dict:
    source = (raw.get("primary_location") or {}).get("source") or {}
    primary_topic = raw.get("primary_topic") or {}
    biblio = raw.get("biblio") or {}
    abstract_inverted_index = raw.get("abstract_inverted_index")

    return {
        "source_record_id": clean_openalex_id(raw.get("id")),
        "source_record_url": raw.get("id"),
        "doi": clean_doi(raw.get("doi")),
        "title": raw.get("title"),
        "display_name": raw.get("display_name"),
        "abstract": reconstruct_abstract(abstract_inverted_index),
        "publication_year": raw.get("publication_year"),
        "publication_date": raw.get("publication_date"),
        "language": raw.get("language"),
        "type": raw.get("type"),
        "cited_by_count": raw.get("cited_by_count", 0),
        "referenced_works_count": raw.get("referenced_works_count", 0),
        "volume": biblio.get("volume"),
        "issue": biblio.get("issue"),
        "page": format_page(biblio),
        "is_retracted": raw.get("is_retracted"),
        "referenced_works": [
            clean_openalex_id(x) for x in raw.get("referenced_works", [])
        ],
        "related_works": [clean_openalex_id(x) for x in raw.get("related_works", [])],
        "abstract_inverted_index": abstract_inverted_index,
        "open_access": raw.get("open_access"),
        "journal": {
            "source_record_id": clean_openalex_id(source.get("id")),
            "source_record_url": source.get("id"),
            "display_name": source.get("display_name"),
            "type": source.get("type"),
        },
        "primary_topic": transform_topic_node(primary_topic),
        "authors": [
            {
                "source_record_id": clean_openalex_id(
                    (a.get("author") or {}).get("id")
                ),
                "source_record_url": (a.get("author") or {}).get("id"),
                "display_name": (a.get("author") or {}).get("display_name"),
                "author_position": a.get("author_position"),
                "is_corresponding": a.get("is_corresponding"),
                "raw_author_name": a.get("raw_author_name"),
            }
            for a in raw.get("authorships", [])
        ],
        "keywords": [
            {
                "source_record_id": clean_openalex_id(k.get("id")),
                "source_record_url": k.get("id"),
                "display_name": k.get("display_name"),
                "score": k.get("score"),
            }
            for k in raw.get("keywords", [])
        ],
        "topics": [
            topic
            for topic in (transform_topic_node(t) for t in raw.get("topics", []))
            if topic
        ],
        "counts_by_year": raw.get("counts_by_year", []),
    }


def transform_authors(raw: dict) -> list[dict]:
    authors = []

    for item in raw.get("authorships", []):
        author = item.get("author") or {}
        source_record_id = clean_openalex_id(author.get("id"))

        if not source_record_id:
            continue

        authors.append(
            {
                "source_record_id": source_record_id,
                "source_record_url": author.get("id"),
                "display_name": author.get("display_name"),
                "orcid": author.get("orcid"),
                "raw_author_names": [item.get("raw_author_name")],
                "countries": item.get("countries", []),
                "affiliations": item.get("affiliations", []),
                "raw_affiliation_strings": item.get("raw_affiliation_strings", []),
                "institutions": item.get("institutions", []),
                "last_seen_source_record_id": clean_openalex_id(raw.get("id")),
            }
        )

    return authors


def transform_journal(raw: dict) -> dict | None:
    source = (raw.get("primary_location") or {}).get("source") or {}

    source_record_id = clean_openalex_id(source.get("id"))
    if not source_record_id:
        return None

    return {
        "source_record_id": source_record_id,
        "source_record_url": source.get("id"),
        "display_name": source.get("display_name"),
        "issn_l": source.get("issn_l"),
        "issn": source.get("issn"),
        "type": source.get("type"),
        "is_oa": source.get("is_oa"),
        "is_in_doaj": source.get("is_in_doaj"),
        "is_core": source.get("is_core"),
        "host_organization": source.get("host_organization"),
        "host_organization_name": source.get("host_organization_name"),
    }


def transform_keywords(raw: dict) -> list[dict]:
    return [
        {
            "source_record_id": clean_openalex_id(k.get("id")),
            "source_record_url": k.get("id"),
            "display_name": k.get("display_name"),
            "score": k.get("score"),
        }
        for k in raw.get("keywords", [])
        if k.get("id")
    ]


def transform_topics(raw: dict) -> list[dict]:
    return [
        topic
        for topic in (transform_topic_node(topic) for topic in raw.get("topics", []))
        if topic
    ]
