import json

from src.config.sqlserver import get_connection
from src.load.pipeline_run_loader import get_source_id


def json_or_none(value) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def get_crawl_watermark(
    source_name: str,
    source_entity: str,
    scope_type: str,
    scope_value: str,
) -> dict | None:
    source_id = get_source_id(source_name)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                watermark_id,
                last_started_at,
                last_success_at,
                last_cursor,
                last_from_updated_date,
                last_to_updated_date,
                last_processed_record_id,
                metadata
            FROM ops.crawl_watermarks
            WHERE source_id = ?
              AND source_entity = ?
              AND scope_type = ?
              AND scope_value = ?
            """,
            source_id,
            source_entity,
            scope_type,
            scope_value,
        )
        row = cursor.fetchone()

    if not row:
        return None

    return {
        "watermark_id": str(row.watermark_id),
        "last_started_at": row.last_started_at,
        "last_success_at": row.last_success_at,
        "last_cursor": row.last_cursor,
        "last_from_updated_date": row.last_from_updated_date,
        "last_to_updated_date": row.last_to_updated_date,
        "last_processed_record_id": row.last_processed_record_id,
        "metadata": row.metadata,
    }


def mark_watermark_started(
    source_name: str,
    source_entity: str,
    scope_type: str,
    scope_value: str,
    metadata: dict | None = None,
) -> str:
    return upsert_crawl_watermark(
        source_name=source_name,
        source_entity=source_entity,
        scope_type=scope_type,
        scope_value=scope_value,
        set_started=True,
        metadata=metadata,
    )


def mark_watermark_success(
    source_name: str,
    source_entity: str,
    scope_type: str,
    scope_value: str,
    last_cursor: str | None = None,
    last_from_updated_date=None,
    last_to_updated_date=None,
    last_processed_record_id: str | None = None,
    metadata: dict | None = None,
) -> str:
    return upsert_crawl_watermark(
        source_name=source_name,
        source_entity=source_entity,
        scope_type=scope_type,
        scope_value=scope_value,
        set_success=True,
        last_cursor=last_cursor,
        last_from_updated_date=last_from_updated_date,
        last_to_updated_date=last_to_updated_date,
        last_processed_record_id=last_processed_record_id,
        metadata=metadata,
    )


def upsert_crawl_watermark(
    source_name: str,
    source_entity: str,
    scope_type: str,
    scope_value: str,
    set_started: bool = False,
    set_success: bool = False,
    last_cursor: str | None = None,
    last_from_updated_date=None,
    last_to_updated_date=None,
    last_processed_record_id: str | None = None,
    metadata: dict | None = None,
) -> str:
    source_id = get_source_id(source_name)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT watermark_id
            FROM ops.crawl_watermarks
            WHERE source_id = ?
              AND source_entity = ?
              AND scope_type = ?
              AND scope_value = ?
            """,
            source_id,
            source_entity,
            scope_type,
            scope_value,
        )
        row = cursor.fetchone()

        if row:
            watermark_id = str(row.watermark_id)
            cursor.execute(
                """
                UPDATE ops.crawl_watermarks
                SET
                    last_started_at =
                        CASE WHEN ? = 1 THEN SYSUTCDATETIME() ELSE last_started_at END,
                    last_success_at =
                        CASE WHEN ? = 1 THEN SYSUTCDATETIME() ELSE last_success_at END,
                    last_cursor = COALESCE(?, last_cursor),
                    last_from_updated_date = COALESCE(?, last_from_updated_date),
                    last_to_updated_date = COALESCE(?, last_to_updated_date),
                    last_processed_record_id = COALESCE(?, last_processed_record_id),
                    metadata = COALESCE(?, metadata),
                    updated_at = SYSUTCDATETIME()
                WHERE watermark_id = ?
                """,
                1 if set_started else 0,
                1 if set_success else 0,
                last_cursor,
                last_from_updated_date,
                last_to_updated_date,
                last_processed_record_id,
                json_or_none(metadata),
                watermark_id,
            )
        else:
            cursor.execute(
                """
                INSERT INTO ops.crawl_watermarks (
                    source_id,
                    source_entity,
                    scope_type,
                    scope_value,
                    last_started_at,
                    last_success_at,
                    last_cursor,
                    last_from_updated_date,
                    last_to_updated_date,
                    last_processed_record_id,
                    metadata,
                    updated_at
                )
                OUTPUT INSERTED.watermark_id
                VALUES (
                    ?, ?, ?, ?,
                    CASE WHEN ? = 1 THEN SYSUTCDATETIME() ELSE NULL END,
                    CASE WHEN ? = 1 THEN SYSUTCDATETIME() ELSE NULL END,
                    ?, ?, ?, ?, ?, SYSUTCDATETIME()
                )
                """,
                source_id,
                source_entity,
                scope_type,
                scope_value,
                1 if set_started else 0,
                1 if set_success else 0,
                last_cursor,
                last_from_updated_date,
                last_to_updated_date,
                last_processed_record_id,
                json_or_none(metadata),
            )
            watermark_id = str(cursor.fetchone().watermark_id)

        conn.commit()
        return watermark_id
