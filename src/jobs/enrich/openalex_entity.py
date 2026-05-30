from collections.abc import Callable

import httpx

from src.extract.openalex_extractor import (
    OPENALEX_TIMEOUT,
    fetch_openalex_entity_record,
)
from src.load.ops.job_runs import (
    attach_pipeline_run,
    log_job,
    mark_job_run_failed,
    mark_job_run_skipped,
    mark_job_run_success,
    start_job_run,
)
from src.load.pipeline_run_loader import (
    create_pipeline_run,
    mark_pipeline_run_failed,
    mark_pipeline_run_success,
)
from src.load.raw.entities import load_raw_entities
from src.utils.console import error as console_error
from src.utils.console import success as console_success
from src.utils.console import warning as console_warning


def enrich_openalex_entity(
    entity: str,
    source_record_ids: list[str],
    process_pending_raw: Callable[[int], None] | None = None,
    process_after_enrich: bool = True,
    process_limit: int | None = None,
) -> int:
    source_name = "OpenAlex"
    total_count = len(source_record_ids)
    job_run_id = start_job_run(
        job_name=f"openalex_enrich_{entity}",
        job_type="enrich",
        source_name=source_name,
        source_entity=entity,
        batch_size=total_count,
        metadata={"process_after_enrich": process_after_enrich},
    )

    if total_count == 0:
        message = f"No OpenAlex {entity} records selected for enrichment."
        print(message)
        log_job(job_run_id, message, source_entity=entity)
        mark_job_run_skipped(job_run_id, reason=message)
        return 0

    run_id = create_pipeline_run(
        source_name=source_name,
        source_entity=entity,
        query_keyword=f"enrich:{entity}",
    )
    attach_pipeline_run(job_run_id, run_id)

    fetched_count = 0
    failed_count = 0
    raw_items = []

    try:
        print(f"Fetching OpenAlex {entity}: selected={total_count}")
        log_job(
            job_run_id,
            f"Fetching OpenAlex {entity}: selected={total_count}",
            source_entity=entity,
            metadata={"selected": total_count},
        )

        with httpx.Client(timeout=OPENALEX_TIMEOUT) as client:
            for index, source_record_id in enumerate(source_record_ids, start=1):
                try:
                    raw_items.append(
                        fetch_openalex_entity_record(
                            entity=entity,
                            source_record_id=source_record_id,
                            client=client,
                        )
                    )
                    fetched_count += 1
                except Exception as error:
                    failed_count += 1
                    print(
                        console_warning(
                            f"Failed to fetch {entity} {source_record_id}: {error}"
                        )
                    )
                    log_job(
                        job_run_id,
                        f"Failed to fetch {entity} {source_record_id}",
                        log_level="warning",
                        source_entity=entity,
                        source_record_id=source_record_id,
                        error_detail=str(error),
                    )

                if index == total_count or index % 25 == 0:
                    progress_message = (
                        f"OpenAlex {entity} fetch progress: "
                        f"{index}/{total_count}, "
                        f"fetched={fetched_count}, "
                        f"failed={failed_count}"
                    )
                    print(progress_message)
                    log_job(
                        job_run_id,
                        progress_message,
                        source_entity=entity,
                        metadata={
                            "index": index,
                            "selected": total_count,
                            "fetched": fetched_count,
                            "failed": failed_count,
                        },
                    )

        changed_count = load_raw_entities(
            raw_items=raw_items,
            source_name=source_name,
            entity=entity,
            pipeline_run_id=run_id,
        )

        mark_pipeline_run_success(
            run_id=run_id,
            records_fetched=fetched_count,
            records_inserted=changed_count,
            records_failed=failed_count,
        )

        print(
            console_success(
                f"OpenAlex {entity} enrich success: "
                f"selected={len(source_record_ids)}, "
                f"fetched={fetched_count}, "
                f"changed={changed_count}, "
                f"failed={failed_count}"
            )
        )
        mark_job_run_success(
            job_run_id=job_run_id,
            records_in=len(source_record_ids),
            records_out=changed_count,
            records_failed=failed_count,
            metadata={
                "fetched": fetched_count,
                "changed": changed_count,
                "process_after_enrich": process_after_enrich,
            },
        )

        if process_after_enrich and changed_count > 0 and process_pending_raw:
            process_pending_raw(process_limit or changed_count)

        return changed_count

    except Exception as error:
        mark_pipeline_run_failed(run_id=run_id, error_message=str(error))
        mark_job_run_failed(
            job_run_id=job_run_id,
            error_message=str(error),
            records_in=len(source_record_ids),
            records_out=fetched_count,
            records_failed=failed_count,
        )
        print(console_error(f"OpenAlex {entity} enrich failed: {error}"))
        return 0
