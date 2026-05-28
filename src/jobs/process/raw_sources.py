import argparse

from src.config.settings import DEFAULT_BATCH_SIZE
from src.jobs.process.raw_processor import process_pending_raw_entities
from src.load.core.journals import upsert_journal_detail
from src.load.pipeline_run_loader import get_source_id
from src.transform.openalex.sources import transform_source_detail


def handle_raw_source(raw: dict, raw_source_id: str) -> str:
    source_id = get_source_id("OpenAlex")
    journal = transform_source_detail(raw)

    if not journal.get("source_record_id") or not journal.get("display_name"):
        raise ValueError(
            f"Invalid source: missing source_record_id or display_name. "
            f"raw_id={raw_source_id}"
        )

    upsert_journal_detail(
        journal,
        source_id=source_id,
        raw_source_id=raw_source_id,
    )

    return f"Processed source: {journal['source_record_id']} | {journal['display_name']}"


def process_pending_raw_sources(limit: int = DEFAULT_BATCH_SIZE) -> None:
    process_pending_raw_entities(
        entity="sources",
        limit=limit,
        handle_raw_record=handle_raw_source,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Process pending raw OpenAlex sources.")
    parser.add_argument("--limit", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()

    process_pending_raw_sources(limit=args.limit)


if __name__ == "__main__":
    main()
