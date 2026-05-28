import argparse

from src.config.settings import DEFAULT_BATCH_SIZE
from src.jobs.reprocess.raw_authors import reprocess_raw_authors
from src.jobs.reprocess.raw_sources import reprocess_raw_sources
from src.jobs.reprocess.raw_works import reprocess_raw_works


def reprocess_all(
    works_limit: int | None = DEFAULT_BATCH_SIZE,
    authors_limit: int | None = DEFAULT_BATCH_SIZE,
    sources_limit: int | None = DEFAULT_BATCH_SIZE,
    source_record_id: str | None = None,
) -> None:
    print("\n=== Reprocessing raw works ===")
    works_queued_count = reprocess_raw_works(
        limit=works_limit,
        source_record_id=source_record_id,
    )
    print(f"Raw works reprocess completed. queued={works_queued_count}")

    print("\n=== Reprocessing raw authors ===")
    authors_queued_count = reprocess_raw_authors(
        limit=authors_limit,
        source_record_id=source_record_id,
    )
    print(f"Raw authors reprocess completed. queued={authors_queued_count}")

    print("\n=== Reprocessing raw sources ===")
    sources_queued_count = reprocess_raw_sources(
        limit=sources_limit,
        source_record_id=source_record_id,
    )
    print(f"Raw sources reprocess completed. queued={sources_queued_count}")

    print("\nRaw reprocess completed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run raw reprocess jobs.")
    parser.add_argument("--works-limit", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--authors-limit", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--sources-limit", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--source-record-id", type=str, default=None)
    args = parser.parse_args()

    reprocess_all(
        works_limit=args.works_limit,
        authors_limit=args.authors_limit,
        sources_limit=args.sources_limit,
        source_record_id=args.source_record_id,
    )


if __name__ == "__main__":
    main()
