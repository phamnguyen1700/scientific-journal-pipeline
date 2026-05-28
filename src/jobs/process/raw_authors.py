import argparse

from src.config.settings import DEFAULT_BATCH_SIZE
from src.jobs.process.raw_processor import process_pending_raw_entities
from src.load.core.authors import upsert_author_detail
from src.load.pipeline_run_loader import get_source_id
from src.transform.openalex.authors import transform_author_detail


def handle_raw_author(raw: dict, raw_author_id: str) -> str:
    source_id = get_source_id("OpenAlex")
    author = transform_author_detail(raw)

    if not author.get("source_record_id") or not author.get("display_name"):
        raise ValueError(
            f"Invalid author: missing source_record_id or display_name. "
            f"raw_id={raw_author_id}"
        )

    upsert_author_detail(
        author,
        source_id=source_id,
        raw_author_id=raw_author_id,
    )

    return f"Processed author: {author['source_record_id']} | {author['display_name']}"


def process_pending_raw_authors(limit: int = DEFAULT_BATCH_SIZE) -> None:
    process_pending_raw_entities(
        entity="authors",
        limit=limit,
        handle_raw_record=handle_raw_author,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Process pending raw OpenAlex authors.")
    parser.add_argument("--limit", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()

    process_pending_raw_authors(limit=args.limit)


if __name__ == "__main__":
    main()
