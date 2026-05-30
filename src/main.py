from time import sleep

from src.jobs.ingest.openalex_works import (
    run_openalex_raw_ingestion,
)

from src.jobs.process.raw_works import (
    process_pending_raw_works,
)

from src.config.seed_keywords import SEED_KEYWORDS
from src.config.settings import OPENALEX_KEYWORD_DELAY_SECONDS
from src.utils.console import success as console_success
from src.utils.console import warning as console_warning


def main():

    total_changed = 0

    for keyword in SEED_KEYWORDS:
        print(f"\n=== Crawling keyword: {keyword} ===")

        changed_count = run_openalex_raw_ingestion(
            keyword=keyword,
            per_page=25,
            max_pages=1,
        )

        total_changed += changed_count

        if changed_count > 0:
            process_pending_raw_works(limit=changed_count)

            print(console_success(f"Transform success for keyword: {keyword}"))

        else:
            print(console_warning(f"No changed records for keyword: {keyword}"))

        if OPENALEX_KEYWORD_DELAY_SECONDS > 0:
            sleep(OPENALEX_KEYWORD_DELAY_SECONDS)

    print(
        console_success(
            f"\nPipeline completed. Total changed raw works: {total_changed}"
        )
    )


if __name__ == "__main__":
    main()
