import json
from collections.abc import Callable

from src.config.sqlserver import get_connection
from src.load.ops.job_runs import (
    log_job,
    mark_job_run_failed,
    mark_job_run_skipped,
    mark_job_run_success,
    start_job_run,
)
from src.load.raw.entities import get_raw_entity_config
from src.load.raw.status import mark_raw_entity_failed, mark_raw_entity_processed
from src.utils.console import error as console_error
from src.utils.console import progress as console_progress


def fetch_pending_raw_entities(entity: str, limit: int) -> list:
    config = get_raw_entity_config(entity)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT TOP (?) {config.id_column}, raw_data
            FROM {config.table_name}
            WHERE processed_status = 'pending'
            ORDER BY fetched_at ASC
            """,
            limit,
        )
        return cursor.fetchall()


def process_pending_raw_entities(
    entity: str,
    limit: int,
    handle_raw_record: Callable[[dict, str], str],
) -> None:
    config = get_raw_entity_config(entity)
    job_run_id = start_job_run(
        job_name=f"process_raw_{entity}",
        job_type="process",
        source_name="OpenAlex",
        source_entity=entity,
        batch_size=limit,
        metadata={"raw_table": config.table_name},
    )
    raw_docs = fetch_pending_raw_entities(entity, limit)

    if not raw_docs:
        message = f"No pending raw {entity} records to process."
        print(message)
        log_job(job_run_id, message, source_entity=entity)
        mark_job_run_skipped(job_run_id, reason=message)
        return

    processed_count = 0
    failed_count = 0

    for raw_doc in raw_docs:
        raw_id = str(getattr(raw_doc, config.id_column))

        try:
            raw = json.loads(raw_doc.raw_data)
            success_message = handle_raw_record(raw, raw_id)

            mark_raw_entity_processed(entity, raw_id)
            print(console_progress(success_message))
            processed_count += 1
            log_job(
                job_run_id,
                success_message,
                source_entity=entity,
                source_record_id=raw_id,
            )

        except Exception as error:
            mark_raw_entity_failed(entity, raw_id, str(error))
            print(console_error(f"Failed raw {entity} {raw_id}: {error}"))
            failed_count += 1
            log_job(
                job_run_id,
                f"Failed raw {entity} {raw_id}",
                log_level="error",
                source_entity=entity,
                source_record_id=raw_id,
                error_detail=str(error),
            )

    if failed_count:
        mark_job_run_failed(
            job_run_id=job_run_id,
            error_message=f"Processed with {failed_count} failed raw {entity} records.",
            records_in=len(raw_docs),
            records_out=processed_count,
            records_failed=failed_count,
            metadata={"raw_table": config.table_name},
        )
    else:
        mark_job_run_success(
            job_run_id=job_run_id,
            records_in=len(raw_docs),
            records_out=processed_count,
            records_failed=failed_count,
            metadata={"raw_table": config.table_name},
        )
