import argparse

from src.config.settings import DEFAULT_BATCH_SIZE
from src.config.sqlserver import get_connection
from src.jobs.enrich.openalex_entity import enrich_openalex_entity
from src.jobs.process.raw_sources import process_pending_raw_sources


def fetch_source_record_ids(limit: int = DEFAULT_BATCH_SIZE) -> list[str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT TOP (?) jsm.source_record_id
            FROM core.journal_source_mappings AS jsm
            INNER JOIN raw.api_sources AS src
                ON jsm.source_id = src.source_id
            LEFT JOIN raw.openalex_sources AS ras
                ON jsm.source_id = ras.source_id
               AND jsm.source_record_id = ras.source_record_id
            WHERE src.source_name = 'OpenAlex'
            ORDER BY
                CASE WHEN jsm.raw_source_id IS NULL THEN 0 ELSE 1 END,
                COALESCE(ras.last_seen_at, ras.fetched_at, '1900-01-01') ASC,
                jsm.created_at ASC
            """,
            limit,
        )
        return [row.source_record_id for row in cursor.fetchall()]


def enrich_openalex_sources(
    limit: int = DEFAULT_BATCH_SIZE,
    process_after_enrich: bool = True,
    process_limit: int | None = None,
) -> int:
    source_record_ids = fetch_source_record_ids(limit)

    return enrich_openalex_entity(
        entity="sources",
        source_record_ids=source_record_ids,
        process_pending_raw=process_pending_raw_sources,
        process_after_enrich=process_after_enrich,
        process_limit=process_limit,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich OpenAlex sources by id.")
    parser.add_argument("--limit", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--process-limit", type=int, default=None)
    parser.add_argument("--skip-process", action="store_true")
    args = parser.parse_args()

    enrich_openalex_sources(
        limit=args.limit,
        process_after_enrich=not args.skip_process,
        process_limit=args.process_limit,
    )


if __name__ == "__main__":
    main()
