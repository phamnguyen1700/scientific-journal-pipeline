from dataclasses import dataclass
from time import sleep

import httpx

from src.config.settings import OPENALEX_API_KEY, OPENALEX_BASE_URL, OPENALEX_MAILTO

OPENALEX_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
OPENALEX_MAX_RETRIES = 3
OPENALEX_RETRY_STATUSES = {429, 500, 502, 503, 504}


def normalize_openalex_id(value: str) -> str:
    return value.rstrip("/").split("/")[-1]


@dataclass(frozen=True)
class OpenAlexPage:
    results: list[dict]
    next_cursor: str | None
    meta: dict


def build_openalex_params(params: dict) -> dict:
    if OPENALEX_MAILTO:
        params["mailto"] = OPENALEX_MAILTO

    if OPENALEX_API_KEY:
        params["api_key"] = OPENALEX_API_KEY

    return params


def get_with_retries(client: httpx.Client, url: str, params: dict) -> httpx.Response:
    for attempt in range(OPENALEX_MAX_RETRIES):
        response = client.get(url, params=build_openalex_params(params.copy()))

        if response.status_code not in OPENALEX_RETRY_STATUSES:
            response.raise_for_status()
            return response

        if attempt == OPENALEX_MAX_RETRIES - 1:
            response.raise_for_status()

        retry_after = response.headers.get("Retry-After")
        wait_seconds = (
            int(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
        )
        sleep(wait_seconds)

    raise RuntimeError("OpenAlex request retry loop exited unexpectedly")


def fetch_works_by_keyword(
    keyword: str,
    per_page: int = 10,
    from_updated_date: str | None = None,
    to_updated_date: str | None = None,
    cursor: str | None = None,
) -> list[dict]:
    url = f"{OPENALEX_BASE_URL}/works"

    params = {"search": keyword, "per_page": per_page}
    filters = []

    if from_updated_date:
        filters.append(f"from_updated_date:{from_updated_date}")

    if to_updated_date:
        filters.append(f"to_updated_date:{to_updated_date}")

    if filters:
        params["filter"] = ",".join(filters)

    if cursor:
        params["cursor"] = cursor

    with httpx.Client(timeout=OPENALEX_TIMEOUT) as client:
        response = get_with_retries(client, url, params)

    data = response.json()

    return data.get("results", [])


def fetch_works_page_by_keyword(
    keyword: str,
    per_page: int = 200,
    from_updated_date: str | None = None,
    to_updated_date: str | None = None,
    cursor: str | None = "*",
) -> OpenAlexPage:
    url = f"{OPENALEX_BASE_URL}/works"

    params = {
        "search": keyword,
        "per_page": per_page,
        "cursor": cursor or "*",
    }
    filters = []

    if from_updated_date:
        filters.append(f"from_updated_date:{from_updated_date}")

    if to_updated_date:
        filters.append(f"to_updated_date:{to_updated_date}")

    if filters:
        params["filter"] = ",".join(filters)

    with httpx.Client(timeout=OPENALEX_TIMEOUT) as client:
        response = get_with_retries(client, url, params)

    data = response.json()
    meta = data.get("meta") or {}

    return OpenAlexPage(
        results=data.get("results", []),
        next_cursor=meta.get("next_cursor"),
        meta=meta,
    )


def fetch_openalex_entity_record(
    entity: str,
    source_record_id: str,
    client: httpx.Client | None = None,
) -> dict:
    clean_id = normalize_openalex_id(source_record_id)
    url = f"{OPENALEX_BASE_URL}/{entity}/{clean_id}"

    if client:
        response = get_with_retries(client, url, {})
        return response.json()

    with httpx.Client(timeout=OPENALEX_TIMEOUT) as local_client:
        response = get_with_retries(local_client, url, {})
        return response.json()


def fetch_openalex_entity_records(
    entity: str,
    source_record_ids: list[str],
) -> list[dict]:
    records = []

    with httpx.Client(timeout=OPENALEX_TIMEOUT) as client:
        for source_record_id in source_record_ids:
            records.append(
                fetch_openalex_entity_record(
                    entity=entity,
                    source_record_id=source_record_id,
                    client=client,
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
