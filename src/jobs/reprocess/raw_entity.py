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


def queue_raw_entity_for_reprocess(
    entity: str,
    limit: int | None = None,
    source_record_id: str | None = None,
) -> int:
    config = get_raw_entity_config(entity)

    with get_connection() as conn:
        cursor = conn.cursor()

        filters = ["processed_status IN ('processed', 'failed')"]
        params = []

        if source_record_id:
            filters.append("source_record_id = ?")
            params.append(source_record_id)

        if limit:
            params.insert(0, limit)
            cursor.execute(
                f"""
                UPDATE {config.table_name}
                SET
                    processed_status = 'pending',
                    process_error = NULL
                WHERE {config.id_column} IN (
                    SELECT TOP (?) {config.id_column}
                    FROM {config.table_name}
                    WHERE {" AND ".join(filters)}
                    ORDER BY fetched_at ASC
                )
                """,
                *params,
            )
        else:
            cursor.execute(
                f"""
                UPDATE {config.table_name}
                SET
                    processed_status = 'pending',
                    process_error = NULL
                WHERE {" AND ".join(filters)}
                """,
                *params,
            )

        queued_count = cursor.rowcount
        conn.commit()

        return queued_count


def reprocess_raw_entity(
    entity: str,
    process_pending_raw: Callable[[int], None],
    limit: int | None = None,
    source_record_id: str | None = None,
) -> int:
    job_run_id = start_job_run(
        job_name=f"reprocess_raw_{entity}",
        job_type="reprocess",
        source_name="OpenAlex",
        source_entity=entity,
        scope_type="source_record_id" if source_record_id else None,
        scope_value=source_record_id,
        batch_size=limit,
        metadata={"source_record_id": source_record_id},
    )

    try:
        queued_count = queue_raw_entity_for_reprocess(
            entity=entity,
            limit=limit,
            source_record_id=source_record_id,
        )

        if queued_count <= 0:
            message = f"No raw {entity} records queued for reprocess."
            print(message)
            log_job(job_run_id, message, source_entity=entity)
            mark_job_run_skipped(job_run_id, reason=message)
            return queued_count

        log_job(
            job_run_id,
            f"Queued raw {entity} records for reprocess: {queued_count}",
            source_entity=entity,
            metadata={"queued_count": queued_count},
        )
        process_pending_raw(limit=queued_count)

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
            f"Failed to reprocess raw {entity}",
            log_level="error",
            source_entity=entity,
            error_detail=str(error),
        )
        mark_job_run_failed(
            job_run_id=job_run_id,
            error_message=str(error),
            metadata={"source_record_id": source_record_id},
        )
        raise
