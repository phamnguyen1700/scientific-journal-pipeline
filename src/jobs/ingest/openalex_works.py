import argparse
from datetime import date, datetime, timedelta, timezone
from time import sleep

from src.config.settings import OPENALEX_PAGE_DELAY_SECONDS
from src.extract.openalex_extractor import fetch_works_page_by_keyword
from src.jobs.process.raw_works import process_pending_raw_works
from src.load.ops.job_runs import (
    attach_pipeline_run,
    log_job,
    mark_job_run_failed,
    mark_job_run_success,
    start_job_run,
)
from src.load.ops.watermarks import (
    get_crawl_watermark,
    mark_watermark_started,
    mark_watermark_success,
)
from src.load.pipeline_run_loader import (
    create_pipeline_run,
    mark_pipeline_run_failed,
    mark_pipeline_run_success,
)
from src.load.raw.entities import load_raw_entities
from src.utils.console import error as console_error
from src.utils.console import progress as console_progress
from src.utils.console import warning as console_warning

VIETNAM_TZ = timezone(timedelta(hours=7))


def format_openalex_date(value) -> str | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    return str(value).split(" ")[0].split("T")[0]


def run_openalex_raw_ingestion(
    keyword: str,
    per_page: int = 5,
    max_pages: int | None = 1,
    page_delay_seconds: float = OPENALEX_PAGE_DELAY_SECONDS,
) -> int:

    source_name = "OpenAlex"
    source_entity = "works"
    scope_type = "keyword"
    scope_value = keyword
    watermark = get_crawl_watermark(
        source_name=source_name,
        source_entity=source_entity,
        scope_type=scope_type,
        scope_value=scope_value,
    )
    resume_cursor = watermark.get("last_cursor") if watermark else None
    from_updated_date = format_openalex_date(
        watermark.get(
            "last_from_updated_date" if resume_cursor else "last_to_updated_date"
        )
        if watermark
        else None
    )
    to_updated_date = format_openalex_date(
        watermark.get("last_to_updated_date")
        if watermark and resume_cursor and from_updated_date
        else None
    )
    watermark_to_updated_date = (
        to_updated_date or datetime.now(VIETNAM_TZ).date().isoformat()
    )

    if from_updated_date and not to_updated_date:
        to_updated_date = watermark_to_updated_date

    crawl_mode = (
        "resume" if resume_cursor else "incremental" if from_updated_date else "initial"
    )

    job_run_id = start_job_run(
        job_name="openalex_ingest_works",
        job_type="ingest",
        source_name=source_name,
        source_entity=source_entity,
        scope_type=scope_type,
        scope_value=scope_value,
        batch_size=per_page,
        metadata={
            "keyword": keyword,
            "per_page": per_page,
            "max_pages": max_pages,
            "page_delay_seconds": page_delay_seconds,
            "crawl_mode": crawl_mode,
            "from_updated_date": from_updated_date,
            "to_updated_date": watermark_to_updated_date,
            "request_to_updated_date": to_updated_date,
            "resume_cursor": resume_cursor,
        },
    )

    run_id = create_pipeline_run(
        source_name=source_name,
        source_entity=source_entity,
        query_keyword=keyword,
    )
    attach_pipeline_run(job_run_id, run_id)
    mark_watermark_started(
        source_name=source_name,
        source_entity=source_entity,
        scope_type=scope_type,
        scope_value=scope_value,
        metadata={
            "per_page": per_page,
            "max_pages": max_pages,
            "page_delay_seconds": page_delay_seconds,
            "crawl_mode": crawl_mode,
            "job_run_id": job_run_id,
            "from_updated_date": from_updated_date,
            "to_updated_date": watermark_to_updated_date,
            "request_to_updated_date": to_updated_date,
            "resume_cursor": resume_cursor,
        },
    )

    try:
        print(
            console_progress(
                f"OpenAlex works ingest mode={crawl_mode}, "
                f"keyword={keyword}, "
                f"from_updated_date={from_updated_date}, "
                f"to_updated_date={to_updated_date}, "
                f"max_pages={max_pages}"
            )
        )
        log_job(
            job_run_id,
            f"Fetching OpenAlex works for keyword: {keyword} ({crawl_mode})",
            source_entity=source_entity,
            metadata={
                "keyword": keyword,
                "per_page": per_page,
                "max_pages": max_pages,
                "page_delay_seconds": page_delay_seconds,
                "crawl_mode": crawl_mode,
                "from_updated_date": from_updated_date,
                "to_updated_date": watermark_to_updated_date,
                "request_to_updated_date": to_updated_date,
                "resume_cursor": resume_cursor,
            },
        )
        total_fetched = 0
        total_changed = 0
        pages_fetched = 0
        cursor = resume_cursor or "*"
        next_cursor = None
        last_processed_record_id = None

        while True:
            page = fetch_works_page_by_keyword(
                keyword=keyword,
                per_page=per_page,
                from_updated_date=from_updated_date,
                to_updated_date=to_updated_date,
                cursor=cursor,
            )
            raw_items = page.results
            pages_fetched += 1
            total_fetched += len(raw_items)
            next_cursor = page.next_cursor

            changed_count = load_raw_entities(
                raw_items=raw_items,
                source_name=source_name,
                entity=source_entity,
                query_keyword=keyword,
                pipeline_run_id=run_id,
            )
            total_changed += changed_count

            if raw_items:
                last_processed_record_id = raw_items[-1].get("id")

            log_job(
                job_run_id,
                (
                    f"Fetched OpenAlex works page {pages_fetched}: "
                    f"fetched={len(raw_items)}, changed={changed_count}"
                ),
                source_entity=source_entity,
                metadata={
                    "keyword": keyword,
                    "crawl_mode": crawl_mode,
                    "page": pages_fetched,
                    "fetched": len(raw_items),
                    "changed": changed_count,
                    "cursor": cursor,
                    "next_cursor": next_cursor,
                },
            )

            if not raw_items or len(raw_items) < per_page:
                next_cursor = None
                break

            if max_pages is not None and pages_fetched >= max_pages:
                break

            if not next_cursor:
                break

            if page_delay_seconds > 0:
                sleep(page_delay_seconds)

            cursor = next_cursor

        is_window_complete = next_cursor is None

        mark_pipeline_run_success(
            run_id=run_id,
            records_fetched=total_fetched,
            records_inserted=total_changed,
        )

        print(
            console_progress(
                f"Raw ingestion success: "
                f"fetched={total_fetched}, "
                f"changed={total_changed}"
            )
        )
        log_job(
            job_run_id,
            (
                f"Raw ingestion success: fetched={total_fetched}, "
                f"changed={total_changed}, pages={pages_fetched}"
            ),
            source_entity=source_entity,
            metadata={
                "keyword": keyword,
                "crawl_mode": crawl_mode,
                "fetched": total_fetched,
                "changed": total_changed,
                "pages_fetched": pages_fetched,
                "window_complete": is_window_complete,
                "next_cursor": next_cursor,
                "from_updated_date": from_updated_date,
                "to_updated_date": watermark_to_updated_date,
                "request_to_updated_date": to_updated_date,
            },
        )
        mark_job_run_success(
            job_run_id=job_run_id,
            records_in=total_fetched,
            records_out=total_changed,
            records_failed=0,
            metadata={
                "fetched": total_fetched,
                "keyword": keyword,
                "crawl_mode": crawl_mode,
                "pages_fetched": pages_fetched,
                "window_complete": is_window_complete,
            },
        )
        mark_watermark_success(
            source_name=source_name,
            source_entity=source_entity,
            scope_type="keyword",
            scope_value=keyword,
            last_cursor=next_cursor,
            clear_cursor=is_window_complete,
            last_from_updated_date=from_updated_date,
            last_to_updated_date=watermark_to_updated_date,
            last_processed_record_id=last_processed_record_id,
            metadata={
                "per_page": per_page,
                "max_pages": max_pages,
                "page_delay_seconds": page_delay_seconds,
                "crawl_mode": crawl_mode,
                "fetched": total_fetched,
                "changed": total_changed,
                "pages_fetched": pages_fetched,
                "window_complete": is_window_complete,
                "job_run_id": job_run_id,
                "pipeline_run_id": run_id,
                "from_updated_date": from_updated_date,
                "to_updated_date": watermark_to_updated_date,
                "request_to_updated_date": to_updated_date,
                "next_cursor": next_cursor,
            },
        )

        return total_changed

    except Exception as error:
        mark_pipeline_run_failed(
            run_id=run_id,
            error_message=str(error),
        )

        print(console_error(f"Pipeline failed: {error}"))
        log_job(
            job_run_id,
            f"OpenAlex works ingestion failed for keyword: {keyword}",
            log_level="error",
            source_entity=source_entity,
            error_detail=str(error),
            metadata={"keyword": keyword, "per_page": per_page},
        )
        mark_job_run_failed(
            job_run_id=job_run_id,
            error_message=str(error),
            records_in=per_page,
            records_out=0,
            records_failed=per_page,
            metadata={"keyword": keyword},
        )

        return 0


def parse_max_pages(value: str) -> int | None:
    if value.lower() in {"none", "all", "full"}:
        return None

    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError(
            "max-pages must be >= 1, or one of: none, all, full"
        )

    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest OpenAlex works by keyword with cursor pagination."
    )
    parser.add_argument(
        "--keyword",
        required=True,
        help="Keyword to search in OpenAlex works.",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=200,
        help="OpenAlex records per page. Default: 200.",
    )
    parser.add_argument(
        "--max-pages",
        type=parse_max_pages,
        default=1,
        help="Maximum pages to fetch. Use 'all' to crawl the full window. Default: 1.",
    )
    parser.add_argument(
        "--page-delay-seconds",
        type=float,
        default=OPENALEX_PAGE_DELAY_SECONDS,
        help="Delay between cursor pages to reduce OpenAlex 429s.",
    )
    parser.add_argument(
        "--process",
        action="store_true",
        help="Process changed raw works after ingestion.",
    )
    parser.add_argument(
        "--process-limit",
        type=int,
        default=None,
        help="Maximum pending raw works to process. Defaults to changed record count.",
    )

    args = parser.parse_args()

    changed_count = run_openalex_raw_ingestion(
        keyword=args.keyword,
        per_page=args.per_page,
        max_pages=args.max_pages,
        page_delay_seconds=args.page_delay_seconds,
    )

    if args.process:
        if changed_count > 0:
            process_pending_raw_works(limit=args.process_limit or changed_count)
        else:
            print(console_warning("No changed raw works to process."))


if __name__ == "__main__":
    main()
