import httpx

from src.config.settings import OPENALEX_BASE_URL


def fetch_works_by_keyword(keyword: str, per_page: int = 10) -> list[dict]:
    url = f"{OPENALEX_BASE_URL}/works"

    params = {"search": keyword, "per_page": per_page}

    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, params=params)
        response.raise_for_status()

    data = response.json()

    return data.get("results", [])
