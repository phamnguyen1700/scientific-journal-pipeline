from time import sleep
from urllib.parse import quote

import httpx

from src.config.settings import (
    CROSSREF_BASE_URL,
    CROSSREF_MAILTO,
    CROSSREF_USER_AGENT,
)

CROSSREF_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
CROSSREF_MAX_RETRIES = 3
CROSSREF_RETRY_STATUSES = {429, 500, 502, 503, 504}


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None

    cleaned = value.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if cleaned.startswith(prefix):
            cleaned = cleaned.removeprefix(prefix)

    return cleaned.strip().rstrip("/") or None


def build_crossref_params(params: dict | None = None) -> dict:
    normalized_params = dict(params or {})

    if CROSSREF_MAILTO:
        normalized_params["mailto"] = CROSSREF_MAILTO

    return normalized_params


def build_crossref_headers() -> dict:
    user_agent = CROSSREF_USER_AGENT

    if CROSSREF_MAILTO and "mailto:" not in user_agent.lower():
        user_agent = f"{user_agent} (mailto:{CROSSREF_MAILTO})"

    return {"User-Agent": user_agent}


def get_with_retries(client: httpx.Client, url: str, params: dict | None = None) -> httpx.Response:
    for attempt in range(CROSSREF_MAX_RETRIES):
        response = client.get(
            url,
            params=build_crossref_params(params),
            headers=build_crossref_headers(),
        )

        if response.status_code not in CROSSREF_RETRY_STATUSES:
            response.raise_for_status()
            return response

        if attempt == CROSSREF_MAX_RETRIES - 1:
            response.raise_for_status()

        retry_after = response.headers.get("Retry-After")
        wait_seconds = (
            int(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
        )
        sleep(wait_seconds)

    raise RuntimeError("Crossref request retry loop exited unexpectedly")


def build_work_url(doi: str) -> str:
    clean_doi = normalize_doi(doi)
    if not clean_doi:
        raise ValueError("Crossref DOI is required.")

    return f"{CROSSREF_BASE_URL}/works/{quote(clean_doi, safe='/')}"


def fetch_work_by_doi(doi: str, client: httpx.Client | None = None) -> dict:
    url = build_work_url(doi)

    if client:
        response = get_with_retries(client, url)
        return response.json()

    with httpx.Client(timeout=CROSSREF_TIMEOUT) as local_client:
        response = get_with_retries(local_client, url)
        return response.json()


def fetch_work_agency_by_doi(doi: str, client: httpx.Client | None = None) -> dict:
    url = f"{build_work_url(doi)}/agency"

    if client:
        response = get_with_retries(client, url)
        return response.json()

    with httpx.Client(timeout=CROSSREF_TIMEOUT) as local_client:
        response = get_with_retries(local_client, url)
        return response.json()


def check_crossref_health() -> dict:
    url = f"{CROSSREF_BASE_URL}/works"

    with httpx.Client(timeout=CROSSREF_TIMEOUT) as client:
        response = get_with_retries(client, url, {"rows": 0})

    return {
        "status_code": response.status_code,
        "base_url": CROSSREF_BASE_URL,
        "mailto_configured": bool(CROSSREF_MAILTO),
        "user_agent": build_crossref_headers()["User-Agent"],
        "response": response.json(),
    }
