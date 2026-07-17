import json

from src.config.sqlserver import get_connection
from src.load.pipeline_run_loader import get_source_id


def json_or_none(value) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def upsert_paper_source_check(
    paper_id: str,
    source_name: str,
    source_record_id: str,
    match_status: str,
    match_method: str,
    confidence_score: float | None = None,
    source_record_url: str | None = None,
    raw_crossref_work_id: str | None = None,
    summary: dict | None = None,
    error_message: str | None = None,
) -> str:
    source_id = get_source_id(source_name)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT check_id
            FROM enrich.paper_source_checks
            WHERE paper_id = ?
              AND source_id = ?
              AND source_record_id = ?
            """,
            paper_id,
            source_id,
            source_record_id,
        )
        row = cursor.fetchone()

        if row:
            check_id = str(row.check_id)
            cursor.execute(
                """
                UPDATE enrich.paper_source_checks
                SET
                    raw_crossref_work_id = ?,
                    source_record_url = ?,
                    match_status = ?,
                    match_method = ?,
                    confidence_score = ?,
                    summary_json = ?,
                    error_message = ?,
                    checked_at = DATEADD(HOUR, 7, SYSUTCDATETIME()),
                    updated_at = DATEADD(HOUR, 7, SYSUTCDATETIME())
                WHERE check_id = ?
                """,
                raw_crossref_work_id,
                source_record_url,
                match_status,
                match_method,
                confidence_score,
                json_or_none(summary),
                error_message,
                check_id,
            )
        else:
            cursor.execute(
                """
                INSERT INTO enrich.paper_source_checks (
                    paper_id,
                    source_id,
                    raw_crossref_work_id,
                    source_record_id,
                    source_record_url,
                    match_status,
                    match_method,
                    confidence_score,
                    summary_json,
                    error_message
                )
                OUTPUT INSERTED.check_id
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                paper_id,
                source_id,
                raw_crossref_work_id,
                source_record_id,
                source_record_url,
                match_status,
                match_method,
                confidence_score,
                json_or_none(summary),
                error_message,
            )
            check_id = str(cursor.fetchone().check_id)

        conn.commit()
        return check_id


def upsert_paper_source_mapping(
    paper_id: str,
    source_name: str,
    source_record_id: str,
    source_record_url: str | None = None,
    source_specific_data: dict | None = None,
) -> str:
    source_id = get_source_id(source_name)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT mapping_id
            FROM core.paper_source_mappings
            WHERE source_id = ?
              AND source_record_id = ?
            """,
            source_id,
            source_record_id,
        )
        row = cursor.fetchone()

        if row:
            mapping_id = str(row.mapping_id)
            cursor.execute(
                """
                UPDATE core.paper_source_mappings
                SET
                    source_record_url = ?,
                    source_specific_data = ?
                WHERE mapping_id = ?
                """,
                source_record_url,
                json_or_none(source_specific_data),
                mapping_id,
            )
        else:
            cursor.execute(
                """
                INSERT INTO core.paper_source_mappings (
                    paper_id,
                    source_id,
                    raw_work_id,
                    source_record_id,
                    source_record_url,
                    source_specific_data
                )
                OUTPUT INSERTED.mapping_id
                VALUES (?, ?, NULL, ?, ?, ?)
                """,
                paper_id,
                source_id,
                source_record_id,
                source_record_url,
                json_or_none(source_specific_data),
            )
            mapping_id = str(cursor.fetchone().mapping_id)

        conn.commit()
        return mapping_id
