from collections.abc import Callable

from src.config.sqlserver import get_connection
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
                    WHERE {' AND '.join(filters)}
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
                WHERE {' AND '.join(filters)}
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
    queued_count = queue_raw_entity_for_reprocess(
        entity=entity,
        limit=limit,
        source_record_id=source_record_id,
    )

    if queued_count > 0:
        process_pending_raw(limit=queued_count)

    return queued_count
