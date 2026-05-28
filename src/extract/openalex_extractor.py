import httpx

from src.config.settings import OPENALEX_BASE_URL


def normalize_openalex_id(value: str) -> str:
    return value.rstrip("/").split("/")[-1]


def fetch_works_by_keyword(keyword: str, per_page: int = 10) -> list[dict]:
    url = f"{OPENALEX_BASE_URL}/works"

    params = {"search": keyword, "per_page": per_page}

    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, params=params)
        response.raise_for_status()

    data = response.json()

    return data.get("results", [])


def fetch_openalex_entity_record(entity: str, source_record_id: str) -> dict:
    clean_id = normalize_openalex_id(source_record_id)
    url = f"{OPENALEX_BASE_URL}/{entity}/{clean_id}"

    with httpx.Client(timeout=30.0) as client:
        response = client.get(url)
        response.raise_for_status()

    return response.json()


def fetch_openalex_entity_records(
    entity: str,
    source_record_ids: list[str],
) -> list[dict]:
    records = []

    for source_record_id in source_record_ids:
        records.append(
            fetch_openalex_entity_record(
                entity=entity,
                source_record_id=source_record_id,
            )
        )

    return records


def fetch_author_by_id(author_id: str) -> dict:
    return fetch_openalex_entity_record("authors", author_id)


def fetch_authors_by_ids(author_ids: list[str]) -> list[dict]:
    return fetch_openalex_entity_records("authors", author_ids)


def fetch_source_by_id(source_id: str) -> dict:
    return fetch_openalex_entity_record("sources", source_id)


def fetch_sources_by_ids(source_ids: list[str]) -> list[dict]:
    return fetch_openalex_entity_records("sources", source_ids)
