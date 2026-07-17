import argparse

from src.config.settings import DEFAULT_BATCH_SIZE
from src.jobs.process.crossref_raw_works import process_pending_crossref_raw_works
from src.load.ops.job_runs import (
    log_job,
    mark_job_run_failed,
    mark_job_run_skipped,
    mark_job_run_success,
    start_job_run,
)
from src.load.raw.crossref_works import queue_crossref_works_for_reprocess


def reprocess_crossref_raw_works(
    limit: int | None = None,
    source_record_id: str | None = None,
    add_mapping: bool = False,
) -> int:
    job_run_id = start_job_run(
        job_name="reprocess_crossref_raw_works",
        job_type="reprocess",
        source_name="Crossref",
        source_entity="works",
        scope_type="source_record_id" if source_record_id else None,
        scope_value=source_record_id,
        batch_size=limit,
        metadata={
            "source_record_id": source_record_id,
            "add_mapping": add_mapping,
        },
    )

    try:
        queued_count = queue_crossref_works_for_reprocess(
            limit=limit,
            source_record_id=source_record_id,
        )

        if queued_count <= 0:
            message = "No raw Crossref works queued for reprocess."
            print(message)
            log_job(job_run_id, message, source_entity="works")
            mark_job_run_skipped(job_run_id, reason=message)
            return queued_count

        log_job(
            job_run_id,
            f"Queued raw Crossref works for reprocess: {queued_count}",
            source_entity="works",
            metadata={"queued_count": queued_count},
        )
        process_pending_crossref_raw_works(
            limit=queued_count,
            add_mapping=add_mapping,
        )

        mark_job_run_success(
            job_run_id=job_run_id,
            records_in=queued_count,
            records_out=queued_count,
            records_failed=0,
            metadata={"source_record_id": source_record_id},
        )

        return queued_count

    except Exception as error:
        log_job(
            job_run_id,
            "Failed to reprocess raw Crossref works",
            log_level="error",
            source_entity="works",
            error_detail=str(error),
        )
        mark_job_run_failed(
            job_run_id=job_run_id,
            error_message=str(error),
            metadata={"source_record_id": source_record_id},
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Queue and reprocess raw Crossref works.")
    parser.add_argument("--limit", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--source-record-id", default=None)
    parser.add_argument(
        "--add-mapping",
        action="store_true",
        help="Insert matched Crossref DOI mappings into core.paper_source_mappings.",
    )
    args = parser.parse_args()

    reprocess_crossref_raw_works(
        limit=args.limit,
        source_record_id=args.source_record_id,
        add_mapping=args.add_mapping,
    )


if __name__ == "__main__":
    main()
