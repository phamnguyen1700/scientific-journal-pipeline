import json

from src.config.settings import CROSSREF_BASE_URL
from src.config.sqlserver import get_connection
from src.extract.crossref_extractor import normalize_doi
from src.load.pipeline_run_loader import get_source_id


def serialize_raw_data(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def get_crossref_work_url(raw: dict, doi: str) -> str:
    message = raw.get("message") or {}
    return message.get("URL") or f"https://doi.org/{doi}"


def load_raw_crossref_work(
    raw: dict,
    doi: str,
    pipeline_run_id: str,
) -> tuple[str, bool]:
    source_id = get_source_id("Crossref", CROSSREF_BASE_URL)
    source_record_id = normalize_doi(doi)
    if not source_record_id:
        raise ValueError("Crossref raw work requires a DOI.")

    source_record_url = get_crossref_work_url(raw, source_record_id)
    raw_data = serialize_raw_data(raw)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT raw_crossref_work_id, raw_data, processed_status
            FROM raw.crossref_works
            WHERE source_id = ?
              AND source_record_id = ?
            """,
            source_id,
            source_record_id,
        )
        row = cursor.fetchone()

        if row:
            raw_id = str(row.raw_crossref_work_id)
            raw_changed = row.raw_data != raw_data
            should_reprocess = raw_changed or row.processed_status != "processed"

            if should_reprocess:
                cursor.execute(
                    """
                    UPDATE raw.crossref_works
                    SET
                        source_entity = 'works',
                        source_record_url = ?,
                        pipeline_run_id = ?,
                        raw_data = ?,
                        last_seen_at = DATEADD(HOUR, 7, SYSUTCDATETIME()),
                        processed_status = 'pending',
                        process_error = NULL
                    WHERE raw_crossref_work_id = ?
                    """,
                    source_record_url,
                    pipeline_run_id,
                    raw_data,
                    raw_id,
                )
            else:
                cursor.execute(
                    """
                    UPDATE raw.crossref_works
                    SET
                        source_entity = 'works',
                        source_record_url = ?,
                        pipeline_run_id = ?,
                        last_seen_at = DATEADD(HOUR, 7, SYSUTCDATETIME())
                    WHERE raw_crossref_work_id = ?
                    """,
                    source_record_url,
                    pipeline_run_id,
                    raw_id,
                )

            conn.commit()
            return raw_id, should_reprocess

        cursor.execute(
            """
            INSERT INTO raw.crossref_works (
                source_id,
                source_entity,
                source_record_id,
                source_record_url,
                pipeline_run_id,
                raw_data,
                fetched_at,
                last_seen_at,
                processed_status
            )
            OUTPUT INSERTED.raw_crossref_work_id
            VALUES (
                ?, 'works', ?, ?, ?, ?,
                DATEADD(HOUR, 7, SYSUTCDATETIME()),
                DATEADD(HOUR, 7, SYSUTCDATETIME()),
                'pending'
            )
            """,
            source_id,
            source_record_id,
            source_record_url,
            pipeline_run_id,
            raw_data,
        )
        raw_id = str(cursor.fetchone().raw_crossref_work_id)
        conn.commit()

        return raw_id, True


def fetch_pending_raw_crossref_works(limit: int) -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT TOP (?) raw_crossref_work_id, raw_data
            FROM raw.crossref_works
            WHERE processed_status = 'pending'
            ORDER BY fetched_at ASC
            """,
            limit,
        )
        return cursor.fetchall()


def mark_raw_crossref_work_processed(raw_crossref_work_id: str) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE raw.crossref_works
            SET
                processed_status = 'processed',
                process_error = NULL
            WHERE raw_crossref_work_id = ?
            """,
            raw_crossref_work_id,
        )
        conn.commit()


def mark_raw_crossref_work_failed(
    raw_crossref_work_id: str,
    error_message: str,
) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE raw.crossref_works
            SET
                processed_status = 'failed',
                process_error = ?
            WHERE raw_crossref_work_id = ?
            """,
            error_message,
            raw_crossref_work_id,
        )
        conn.commit()


def queue_crossref_works_for_reprocess(
    limit: int | None = None,
    source_record_id: str | None = None,
) -> int:
    filters = ["processed_status IN ('processed', 'failed')"]
    params = []

    if source_record_id:
        filters.append("source_record_id = ?")
        params.append(normalize_doi(source_record_id))

    with get_connection() as conn:
        cursor = conn.cursor()

        if limit:
            params.insert(0, limit)
            cursor.execute(
                f"""
                UPDATE raw.crossref_works
                SET
                    processed_status = 'pending',
                    process_error = NULL
                WHERE raw_crossref_work_id IN (
                    SELECT TOP (?) raw_crossref_work_id
                    FROM raw.crossref_works
                    WHERE {" AND ".join(filters)}
                    ORDER BY fetched_at ASC
                )
                """,
                *params,
            )
        else:
            cursor.execute(
                f"""
                UPDATE raw.crossref_works
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
