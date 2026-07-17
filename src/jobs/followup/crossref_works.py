import argparse
from time import sleep

import httpx

from src.config.settings import CROSSREF_PAGE_DELAY_SECONDS, DEFAULT_BATCH_SIZE
from src.extract.crossref_extractor import (
    CROSSREF_TIMEOUT,
    fetch_work_agency_by_doi,
    fetch_work_by_doi,
    normalize_doi,
)
from src.jobs.process.crossref_raw_works import process_pending_crossref_raw_works
from src.load.core.papers import fetch_papers_for_crossref_followup
from src.load.enrich.paper_source_checks import upsert_paper_source_check
from src.load.ops.job_runs import (
    attach_pipeline_run,
    log_job,
    mark_job_run_failed,
    mark_job_run_success,
    start_job_run,
)
from src.load.pipeline_run_loader import (
    create_pipeline_run,
    mark_pipeline_run_failed,
    mark_pipeline_run_success,
)
from src.load.raw.crossref_works import load_raw_crossref_work
from src.utils.console import error as console_error
from src.utils.console import progress as console_progress
from src.utils.console import success as console_success
from src.utils.console import warning as console_warning


def is_not_found_error(error: httpx.HTTPStatusError) -> bool:
    return error.response.status_code == 404


def mark_crossref_check_error(
    paper: dict,
    status: str,
    error_message: str | None = None,
) -> None:
    doi = normalize_doi(paper.get("doi"))
    if not doi:
        return

    upsert_paper_source_check(
        paper_id=paper["paper_id"],
        source_name="Crossref",
        source_record_id=doi,
        source_record_url=f"https://doi.org/{doi}",
        match_status=status,
        match_method="doi",
        confidence_score=0.0,
        summary={
            "doi": doi,
            "paper": {
                "paper_id": paper["paper_id"],
                "title": paper.get("title"),
                "publication_year": paper.get("publication_year"),
            },
        },
        error_message=error_message,
    )


def run_crossref_followup(
    limit: int = 100,
    process_after_ingest: bool = True,
    process_limit: int | None = None,
    page_delay_seconds: float = CROSSREF_PAGE_DELAY_SECONDS,
    include_checked: bool = False,
    skip_agency_check: bool = False,
    add_mapping: bool = False,
) -> int:
    source_name = "Crossref"
    source_entity = "works"
    papers = fetch_papers_for_crossref_followup(
        limit=limit,
        include_checked=include_checked,
    )

    job_run_id = start_job_run(
        job_name="crossref_followup_works",
        job_type="followup",
        source_name=source_name,
        source_entity=source_entity,
        scope_type="doi",
        scope_value="core.papers",
        batch_size=limit,
        metadata={
            "selected_papers": len(papers),
            "include_checked": include_checked,
            "skip_agency_check": skip_agency_check,
            "add_mapping": add_mapping,
        },
    )
    pipeline_run_id = create_pipeline_run(
        source_name=source_name,
        source_entity=source_entity,
        query_keyword="doi_followup",
    )
    attach_pipeline_run(job_run_id, pipeline_run_id)

    if not papers:
        message = "No core papers selected for Crossref follow-up."
        print(console_warning(message))
        log_job(job_run_id, message, source_entity=source_entity)
        mark_pipeline_run_success(pipeline_run_id, 0, 0, 0)
        mark_job_run_success(job_run_id, 0, 0, 0)
        return 0

    print(console_progress(f"Crossref follow-up selected papers: {len(papers)}"))

    total_fetched = 0
    total_changed = 0
    total_failed = 0

    try:
        with httpx.Client(timeout=CROSSREF_TIMEOUT) as client:
            for index, paper in enumerate(papers, start=1):
                doi = normalize_doi(paper.get("doi"))
                if not doi:
                    continue

                print(
                    console_progress(
                        f"[{index}/{len(papers)}] Crossref follow-up DOI: {doi}"
                    )
                )

                try:
                    if not skip_agency_check:
                        agency_response = fetch_work_agency_by_doi(doi, client=client)
                        agency = (agency_response.get("message") or {}).get("agency") or {}
                        agency_id = (agency.get("id") or "").lower()

                        if agency_id and agency_id != "crossref":
                            mark_crossref_check_error(
                                paper,
                                "not_crossref",
                                f"DOI agency is {agency_id}.",
                            )
                            log_job(
                                job_run_id,
                                f"Skipped non-Crossref DOI: {doi}",
                                source_entity=source_entity,
                                source_record_id=doi,
                                metadata={"agency": agency},
                            )
                            continue

                    raw = fetch_work_by_doi(doi, client=client)
                    total_fetched += 1
                    raw_id, changed = load_raw_crossref_work(
                        raw=raw,
                        doi=doi,
                        pipeline_run_id=pipeline_run_id,
                    )
                    if changed:
                        total_changed += 1

                    log_job(
                        job_run_id,
                        f"Fetched Crossref work: {doi}",
                        source_entity=source_entity,
                        source_record_id=doi,
                        metadata={"raw_crossref_work_id": raw_id, "changed": changed},
                    )

                    if page_delay_seconds > 0 and index < len(papers):
                        sleep(page_delay_seconds)

                except httpx.HTTPStatusError as error:
                    if is_not_found_error(error):
                        mark_crossref_check_error(
                            paper,
                            "not_found",
                            f"Crossref returned 404 for DOI: {doi}",
                        )
                    else:
                        mark_crossref_check_error(
                            paper,
                            "error",
                            str(error),
                        )
                        total_failed += 1

                    log_job(
                        job_run_id,
                        f"Crossref HTTP error for DOI: {doi}",
                        log_level="error",
                        source_entity=source_entity,
                        source_record_id=doi,
                        error_detail=str(error),
                    )

                except Exception as error:
                    mark_crossref_check_error(paper, "error", str(error))
                    total_failed += 1
                    log_job(
                        job_run_id,
                        f"Crossref follow-up failed for DOI: {doi}",
                        log_level="error",
                        source_entity=source_entity,
                        source_record_id=doi,
                        error_detail=str(error),
                    )

        mark_pipeline_run_success(
            pipeline_run_id,
            records_fetched=total_fetched,
            records_inserted=total_changed,
            records_failed=total_failed,
        )

        if process_after_ingest and total_changed > 0:
            process_pending_crossref_raw_works(
                limit=process_limit or total_changed,
                add_mapping=add_mapping,
            )
        elif process_after_ingest:
            print(console_warning("No changed Crossref raw works to process."))

        mark_job_run_success(
            job_run_id,
            records_in=len(papers),
            records_out=total_changed,
            records_failed=total_failed,
            metadata={
                "fetched": total_fetched,
                "changed": total_changed,
                "failed": total_failed,
            },
        )
        print(
            console_success(
                f"Crossref follow-up completed. Changed raw works: {total_changed}"
            )
        )
        return total_changed

    except Exception as error:
        mark_pipeline_run_failed(pipeline_run_id, str(error))
        log_job(
            job_run_id,
            "Crossref follow-up failed.",
            log_level="error",
            source_entity=source_entity,
            error_detail=str(error),
        )
        mark_job_run_failed(
            job_run_id=job_run_id,
            error_message=str(error),
            records_in=len(papers),
            records_out=total_changed,
            records_failed=total_failed,
        )
        print(console_error(f"Crossref follow-up failed: {error}"))
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Crossref DOI follow-up for existing core papers."
    )
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--skip-process", action="store_true")
    parser.add_argument("--process-limit", type=int, default=None)
    parser.add_argument(
        "--page-delay-seconds",
        type=float,
        default=CROSSREF_PAGE_DELAY_SECONDS,
    )
    parser.add_argument("--include-checked", action="store_true")
    parser.add_argument("--skip-agency-check", action="store_true")
    parser.add_argument(
        "--add-mapping",
        action="store_true",
        help="Insert matched Crossref DOI mappings into core.paper_source_mappings.",
    )
    args = parser.parse_args()

    run_crossref_followup(
        limit=args.limit,
        process_after_ingest=not args.skip_process,
        process_limit=args.process_limit,
        page_delay_seconds=args.page_delay_seconds,
        include_checked=args.include_checked,
        skip_agency_check=args.skip_agency_check,
        add_mapping=args.add_mapping,
    )


if __name__ == "__main__":
    main()
