import argparse
from time import sleep

from src.config.seed_keywords import SEED_KEYWORDS
from src.config.settings import (
    DEFAULT_BATCH_SIZE,
    OPENALEX_KEYWORD_DELAY_SECONDS,
    OPENALEX_PAGE_DELAY_SECONDS,
)
from src.jobs.enrich.openalex_authors import enrich_openalex_authors
from src.jobs.enrich.openalex_sources import enrich_openalex_sources
from src.jobs.ingest.openalex_works import parse_max_pages, run_openalex_raw_ingestion
from src.jobs.process.raw_works import process_pending_raw_works
from src.utils.console import progress as console_progress
from src.utils.console import success as console_success
from src.utils.console import warning as console_warning


def normalize_keywords(keywords: list[str] | None) -> list[str]:
    if not keywords:
        return SEED_KEYWORDS

    return [keyword.strip() for keyword in keywords if keyword.strip()]


def sync_openalex_works(
    keywords: list[str] | None = None,
    per_page: int = 200,
    max_pages_per_keyword: int | None = 1,
    process_after_ingest: bool = True,
    process_limit: int | None = None,
    page_delay_seconds: float = OPENALEX_PAGE_DELAY_SECONDS,
    keyword_delay_seconds: float = OPENALEX_KEYWORD_DELAY_SECONDS,
    enrich_authors: bool = False,
    enrich_sources: bool = False,
    enrich_limit: int = DEFAULT_BATCH_SIZE,
) -> int:
    selected_keywords = normalize_keywords(keywords)
    total_changed = 0

    print(
        console_progress(
            f"OpenAlex works sync started: "
            f"keywords={len(selected_keywords)}, "
            f"per_page={per_page}, "
            f"max_pages_per_keyword={max_pages_per_keyword}"
        )
    )

    for index, keyword in enumerate(selected_keywords, start=1):
        print(
            console_progress(
                f"[{index}/{len(selected_keywords)}] Sync keyword: {keyword}"
            )
        )

        changed_count = run_openalex_raw_ingestion(
            keyword=keyword,
            per_page=per_page,
            max_pages=max_pages_per_keyword,
            page_delay_seconds=page_delay_seconds,
        )
        total_changed += changed_count

        if process_after_ingest:
            if changed_count > 0:
                process_pending_raw_works(limit=process_limit or changed_count)
            else:
                print(
                    console_warning(f"No changed raw works to process for: {keyword}")
                )

        if keyword_delay_seconds > 0 and index < len(selected_keywords):
            sleep(keyword_delay_seconds)

    if enrich_authors:
        print(console_progress("Enriching OpenAlex authors..."))
        enrich_openalex_authors(limit=enrich_limit)

    if enrich_sources:
        print(console_progress("Enriching OpenAlex sources..."))
        enrich_openalex_sources(limit=enrich_limit)

    print(
        console_success(
            f"OpenAlex works sync completed. Total changed raw works: {total_changed}"
        )
    )

    return total_changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synchronize OpenAlex works for seed or selected keywords."
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=None,
        help="Keywords to sync. Defaults to configured seed keywords.",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=200,
        help="OpenAlex records per page. Default: 200.",
    )
    parser.add_argument(
        "--max-pages-per-keyword",
        type=parse_max_pages,
        default=1,
        help="Maximum pages per keyword. Use all/none/full to crawl the full window.",
    )
    parser.add_argument(
        "--skip-process",
        action="store_true",
        help="Skip processing raw works after ingestion.",
    )
    parser.add_argument(
        "--process-limit",
        type=int,
        default=None,
        help="Maximum pending raw works to process per keyword.",
    )
    parser.add_argument(
        "--page-delay-seconds",
        type=float,
        default=OPENALEX_PAGE_DELAY_SECONDS,
        help="Delay between cursor pages.",
    )
    parser.add_argument(
        "--keyword-delay-seconds",
        type=float,
        default=OPENALEX_KEYWORD_DELAY_SECONDS,
        help="Delay between keywords.",
    )
    parser.add_argument(
        "--enrich-authors",
        action="store_true",
        help="Run OpenAlex author enrichment after works sync.",
    )
    parser.add_argument(
        "--enrich-sources",
        action="store_true",
        help="Run OpenAlex source enrichment after works sync.",
    )
    parser.add_argument(
        "--enrich-limit",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Limit for each enrich job. Default: DEFAULT_BATCH_SIZE.",
    )

    args = parser.parse_args()

    sync_openalex_works(
        keywords=args.keywords,
        per_page=args.per_page,
        max_pages_per_keyword=args.max_pages_per_keyword,
        process_after_ingest=not args.skip_process,
        process_limit=args.process_limit,
        page_delay_seconds=args.page_delay_seconds,
        keyword_delay_seconds=args.keyword_delay_seconds,
        enrich_authors=args.enrich_authors,
        enrich_sources=args.enrich_sources,
        enrich_limit=args.enrich_limit,
    )


if __name__ == "__main__":
    main()
