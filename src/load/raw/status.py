from src.config.sqlserver import get_connection
from src.load.raw.entities import get_raw_entity_config


def mark_raw_entity_processed(entity: str, raw_id: str) -> None:
    config = get_raw_entity_config(entity)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            UPDATE {config.table_name}
            SET
                processed_status = 'processed',
                process_error = NULL
            WHERE {config.id_column} = ?
            """,
            raw_id,
        )
        conn.commit()


def mark_raw_entity_failed(entity: str, raw_id: str, error_message: str) -> None:
    config = get_raw_entity_config(entity)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            UPDATE {config.table_name}
            SET
                processed_status = 'failed',
                process_error = ?
            WHERE {config.id_column} = ?
            """,
            error_message,
            raw_id,
        )
        conn.commit()
