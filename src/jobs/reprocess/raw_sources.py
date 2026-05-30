import argparse

from src.config.settings import DEFAULT_BATCH_SIZE
from src.jobs.process.raw_sources import process_pending_raw_sources
from src.jobs.reprocess.raw_entity import reprocess_raw_entity


def reprocess_raw_sources(
    limit: int | None = DEFAULT_BATCH_SIZE,
    source_record_id: str | None = None,
) -> int:
    return reprocess_raw_entity(
        entity="sources",
        process_pending_raw=process_pending_raw_sources,
        limit=limit,
        source_record_id=source_record_id,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Queue and reprocess raw OpenAlex sources."
    )
    parser.add_argument("--limit", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--source-record-id", type=str, default=None)
    args = parser.parse_args()

    reprocess_raw_sources(
        limit=args.limit,
        source_record_id=args.source_record_id,
    )
