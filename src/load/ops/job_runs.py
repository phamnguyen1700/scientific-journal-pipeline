import json

from src.config.sqlserver import get_connection
from src.load.pipeline_run_loader import get_source_id


def json_or_none(value) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def start_job_run(
    job_name: str,
    job_type: str,
    parent_job_run_id: str | None = None,
    source_name: str | None = None,
    source_entity: str | None = None,
    pipeline_run_id: str | None = None,
    scope_type: str | None = None,
    scope_value: str | None = None,
    batch_size: int | None = None,
    triggered_by: str | None = "manual",
    metadata: dict | None = None,
) -> str:
    source_id = get_source_id(source_name) if source_name else None
    normalized_batch_size = batch_size if batch_size and batch_size > 0 else None

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO ops.job_runs (
                parent_job_run_id,
                job_name,
                job_type,
                status,
                source_id,
                source_entity,
                pipeline_run_id,
                scope_type,
                scope_value,
                batch_size,
                triggered_by,
                metadata
            )
            OUTPUT INSERTED.job_run_id
            VALUES (?, ?, ?, 'running', ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            parent_job_run_id,
            job_name,
            job_type,
            source_id,
            source_entity,
            pipeline_run_id,
            scope_type,
            scope_value,
            normalized_batch_size,
            triggered_by,
            json_or_none(metadata),
        )
        job_run_id = cursor.fetchone().job_run_id
        conn.commit()

        return str(job_run_id)


def mark_job_run_success(
    job_run_id: str,
    records_in: int | None = None,
    records_out: int | None = None,
    records_failed: int | None = None,
    metadata: dict | None = None,
) -> None:
    finish_job_run(
        job_run_id=job_run_id,
        status="success",
        records_in=records_in,
        records_out=records_out,
        records_failed=records_failed,
        metadata=metadata,
    )


def mark_job_run_failed(
    job_run_id: str,
    error_message: str,
    records_in: int | None = None,
    records_out: int | None = None,
    records_failed: int | None = None,
    metadata: dict | None = None,
) -> None:
    finish_job_run(
        job_run_id=job_run_id,
        status="failed",
        records_in=records_in,
        records_out=records_out,
        records_failed=records_failed,
        error_message=error_message,
        metadata=metadata,
    )


def mark_job_run_skipped(
    job_run_id: str,
    reason: str | None = None,
    metadata: dict | None = None,
) -> None:
    finish_job_run(
        job_run_id=job_run_id,
        status="skipped",
        error_message=reason,
        metadata=metadata,
    )


def finish_job_run(
    job_run_id: str,
    status: str,
    records_in: int | None = None,
    records_out: int | None = None,
    records_failed: int | None = None,
    error_message: str | None = None,
    metadata: dict | None = None,
) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE ops.job_runs
            SET
                status = ?,
                finished_at = SYSUTCDATETIME(),
                records_in = COALESCE(?, records_in),
                records_out = COALESCE(?, records_out),
                records_failed = COALESCE(?, records_failed),
                error_message = ?,
                metadata = COALESCE(?, metadata)
            WHERE job_run_id = ?
            """,
            status,
            records_in,
            records_out,
            records_failed,
            error_message,
            json_or_none(metadata),
            job_run_id,
        )
        conn.commit()


def attach_pipeline_run(
    job_run_id: str,
    pipeline_run_id: str,
) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE ops.job_runs
            SET pipeline_run_id = ?
            WHERE job_run_id = ?
            """,
            pipeline_run_id,
            job_run_id,
        )
        conn.commit()


def log_job(
    job_run_id: str,
    message: str,
    log_level: str = "info",
    source_entity: str | None = None,
    source_record_id: str | None = None,
    error_detail: str | None = None,
    metadata: dict | None = None,
) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO ops.job_logs (
                job_run_id,
                log_level,
                message,
                source_entity,
                source_record_id,
                error_detail,
                metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            job_run_id,
            log_level,
            message,
            source_entity,
            source_record_id,
            error_detail,
            json_or_none(metadata),
        )
        conn.commit()
