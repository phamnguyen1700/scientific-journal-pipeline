from src.jobs.ingest.openalex_works import (
    run_openalex_raw_ingestion,
)

from src.jobs.process.raw_works import (
    process_pending_raw_works,
)

from src.config.seed_keywords import SEED_KEYWORDS


def main():

    total_inserted = 0

    for keyword in SEED_KEYWORDS:
        print(f"\n=== Crawling keyword: {keyword} ===")

        inserted_count = run_openalex_raw_ingestion(
            keyword=keyword,
            per_page=25,
        )

        total_inserted += inserted_count

        if inserted_count > 0:

            process_pending_raw_works(limit=inserted_count)

            print(f"Transform success for keyword: {keyword}")

        else:
            print(f"No new records inserted for keyword: {keyword}")

    print(f"\nPipeline completed. " f"Total changed raw works: {total_inserted}")


if __name__ == "__main__":
    main()
