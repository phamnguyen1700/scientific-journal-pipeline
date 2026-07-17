import argparse
import json

from src.config.settings import DEFAULT_BATCH_SIZE
from src.load.core.papers import fetch_paper_by_doi
from src.load.enrich.paper_source_checks import (
    upsert_paper_source_check,
    upsert_paper_source_mapping,
)
from src.load.ops.job_runs import (
    log_job,
    mark_job_run_failed,
    mark_job_run_skipped,
    mark_job_run_success,
    start_job_run,
)
from src.load.raw.crossref_works import (
    fetch_pending_raw_crossref_works,
    mark_raw_crossref_work_failed,
    mark_raw_crossref_work_processed,
)
from src.transform.crossref.works import (
    compare_crossref_to_paper,
    extract_crossref_summary,
)
from src.utils.console import error as console_error
from src.utils.console import progress as console_progress


def handle_raw_crossref_work(
    raw: dict,
    raw_crossref_work_id: str,
    add_mapping: bool = False,
) -> str:
    summary = extract_crossref_summary(raw)
    doi = summary.get("doi")
    if not doi:
        raise ValueError(f"Invalid Crossref work: missing DOI. raw_id={raw_crossref_work_id}")

    paper = fetch_paper_by_doi(doi)
    if not paper:
        raise ValueError(f"No core paper found for Crossref DOI: {doi}")

    comparison = compare_crossref_to_paper(paper, summary)
    check_summary = {
        "crossref": summary,
        "comparison": comparison,
    }

    upsert_paper_source_check(
        paper_id=paper["paper_id"],
        source_name="Crossref",
        source_record_id=doi,
        source_record_url=summary.get("source_record_url"),
        raw_crossref_work_id=raw_crossref_work_id,
        match_status=comparison["match_status"],
        match_method=comparison["match_method"],
        confidence_score=comparison["confidence_score"],
        summary=check_summary,
    )

    if add_mapping and comparison["match_status"] == "matched":
        upsert_paper_source_mapping(
            paper_id=paper["paper_id"],
            source_name="Crossref",
            source_record_id=doi,
            source_record_url=summary.get("source_record_url"),
            source_specific_data=summary,
        )

    return (
        f"Processed Crossref work: {doi} | "
        f"{comparison['match_status']} | {paper['title']}"
    )


def process_pending_crossref_raw_works(
    limit: int = DEFAULT_BATCH_SIZE,
    add_mapping: bool = False,
) -> None:
    job_run_id = start_job_run(
        job_name="process_crossref_raw_works",
        job_type="process",
        source_name="Crossref",
        source_entity="works",
        batch_size=limit,
        metadata={
            "raw_table": "raw.crossref_works",
            "add_mapping": add_mapping,
        },
    )
    raw_docs = fetch_pending_raw_crossref_works(limit)

    if not raw_docs:
        message = "No pending raw Crossref works to process."
        print(message)
        log_job(job_run_id, message, source_entity="works")
        mark_job_run_skipped(job_run_id, reason=message)
        return

    processed_count = 0
    failed_count = 0

    for raw_doc in raw_docs:
        raw_id = str(raw_doc.raw_crossref_work_id)

        try:
            raw = json.loads(raw_doc.raw_data)
            success_message = handle_raw_crossref_work(
                raw=raw,
                raw_crossref_work_id=raw_id,
                add_mapping=add_mapping,
            )
            mark_raw_crossref_work_processed(raw_id)
            print(console_progress(success_message))
            processed_count += 1
            log_job(
                job_run_id,
                success_message,
                source_entity="works",
                source_record_id=raw_id,
            )

        except Exception as error:
            mark_raw_crossref_work_failed(raw_id, str(error))
            print(console_error(f"Failed raw Crossref work {raw_id}: {error}"))
            failed_count += 1
            log_job(
                job_run_id,
                f"Failed raw Crossref work {raw_id}",
                log_level="error",
                source_entity="works",
                source_record_id=raw_id,
                error_detail=str(error),
            )

    if failed_count:
        mark_job_run_failed(
            job_run_id=job_run_id,
            error_message=(
                f"Processed with {failed_count} failed raw Crossref work records."
            ),
            records_in=len(raw_docs),
            records_out=processed_count,
            records_failed=failed_count,
            metadata={"raw_table": "raw.crossref_works"},
        )
    else:
        mark_job_run_success(
            job_run_id=job_run_id,
            records_in=len(raw_docs),
            records_out=processed_count,
            records_failed=failed_count,
            metadata={"raw_table": "raw.crossref_works"},
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Process pending raw Crossref works.")
    parser.add_argument("--limit", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--add-mapping",
        action="store_true",
        help="Insert matched Crossref DOI mappings into core.paper_source_mappings.",
    )
    args = parser.parse_args()

    process_pending_crossref_raw_works(
        limit=args.limit,
        add_mapping=args.add_mapping,
    )


if __name__ == "__main__":
    main()
