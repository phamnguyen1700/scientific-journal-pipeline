import json
from collections.abc import Callable

from src.config.sqlserver import get_connection
from src.load.raw.entities import get_raw_entity_config
from src.load.raw.status import mark_raw_entity_failed, mark_raw_entity_processed


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
    raw_docs = fetch_pending_raw_entities(entity, limit)

    for raw_doc in raw_docs:
        raw_id = str(getattr(raw_doc, config.id_column))

        try:
            raw = json.loads(raw_doc.raw_data)
            success_message = handle_raw_record(raw, raw_id)

            mark_raw_entity_processed(entity, raw_id)
            print(success_message)

        except Exception as error:
            mark_raw_entity_failed(entity, raw_id, str(error))
            print(f"Failed raw {entity} {raw_id}: {error}")
