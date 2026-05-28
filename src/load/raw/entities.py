import json
from dataclasses import dataclass

from src.config.sqlserver import get_connection
from src.load.pipeline_run_loader import get_source_id


@dataclass(frozen=True)
class RawEntityConfig:
    entity: str
    table_name: str
    id_column: str
    supports_query_keyword: bool = False


RAW_ENTITY_CONFIGS = {
    "works": RawEntityConfig(
        entity="works",
        table_name="raw.openalex_works",
        id_column="raw_work_id",
        supports_query_keyword=True,
    ),
    "authors": RawEntityConfig(
        entity="authors",
        table_name="raw.openalex_authors",
        id_column="raw_author_id",
    ),
    "sources": RawEntityConfig(
        entity="sources",
        table_name="raw.openalex_sources",
        id_column="raw_source_id",
    ),
}


def clean_source_record_id(value: str | None) -> str | None:
    if not value:
        return None
    return value.rstrip("/").split("/")[-1]


def serialize_raw_data(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def get_raw_entity_config(entity: str) -> RawEntityConfig:
    try:
        return RAW_ENTITY_CONFIGS[entity]
    except KeyError as error:
        supported = ", ".join(sorted(RAW_ENTITY_CONFIGS))
        raise ValueError(f"Unsupported raw entity '{entity}'. Supported: {supported}") from error


def load_raw_entities(
    raw_items: list[dict],
    source_name: str,
    entity: str,
    pipeline_run_id: str,
    query_keyword: str | None = None,
) -> int:
    if not raw_items:
        return 0

    config = get_raw_entity_config(entity)
    source_id = get_source_id(source_name)
    changed_count = 0

    with get_connection() as conn:
        cursor = conn.cursor()

        for item in raw_items:
            source_record_id = clean_source_record_id(item.get("id"))

            if not source_record_id:
                continue

            source_record_url = item.get("id")
            raw_data = serialize_raw_data(item)

            cursor.execute(
                f"""
                SELECT {config.id_column}, raw_data
                FROM {config.table_name}
                WHERE source_id = ?
                  AND source_record_id = ?
                """,
                source_id,
                source_record_id,
            )
            row = cursor.fetchone()

            if row:
                raw_id = getattr(row, config.id_column)
                raw_changed = row.raw_data != raw_data
                processed_status = "pending" if raw_changed else None
                process_error = None if raw_changed else "__KEEP_EXISTING__"

                if config.supports_query_keyword:
                    if raw_changed:
                        cursor.execute(
                            f"""
                            UPDATE {config.table_name}
                            SET
                                source_entity = ?,
                                query_keyword = ?,
                                pipeline_run_id = ?,
                                raw_data = ?,
                                last_seen_at = SYSUTCDATETIME(),
                                processed_status = ?,
                                process_error = ?
                            WHERE {config.id_column} = ?
                            """,
                            config.entity,
                            query_keyword,
                            pipeline_run_id,
                            raw_data,
                            processed_status,
                            process_error,
                            raw_id,
                        )
                    else:
                        cursor.execute(
                            f"""
                            UPDATE {config.table_name}
                            SET
                                source_entity = ?,
                                query_keyword = ?,
                                pipeline_run_id = ?,
                                raw_data = ?,
                                last_seen_at = SYSUTCDATETIME()
                            WHERE {config.id_column} = ?
                            """,
                            config.entity,
                            query_keyword,
                            pipeline_run_id,
                            raw_data,
                            raw_id,
                        )
                else:
                    if raw_changed:
                        cursor.execute(
                            f"""
                            UPDATE {config.table_name}
                            SET
                                source_entity = ?,
                                source_record_url = ?,
                                pipeline_run_id = ?,
                                raw_data = ?,
                                last_seen_at = SYSUTCDATETIME(),
                                processed_status = ?,
                                process_error = ?
                            WHERE {config.id_column} = ?
                            """,
                            config.entity,
                            source_record_url,
                            pipeline_run_id,
                            raw_data,
                            processed_status,
                            process_error,
                            raw_id,
                        )
                    else:
                        cursor.execute(
                            f"""
                            UPDATE {config.table_name}
                            SET
                                source_entity = ?,
                                source_record_url = ?,
                                pipeline_run_id = ?,
                                raw_data = ?,
                                last_seen_at = SYSUTCDATETIME()
                            WHERE {config.id_column} = ?
                            """,
                            config.entity,
                            source_record_url,
                            pipeline_run_id,
                            raw_data,
                            raw_id,
                        )

                if raw_changed:
                    changed_count += 1

                continue

            if config.supports_query_keyword:
                cursor.execute(
                    f"""
                    INSERT INTO {config.table_name} (
                        source_id,
                        source_entity,
                        source_record_id,
                        query_keyword,
                        pipeline_run_id,
                        raw_data,
                        fetched_at,
                        last_seen_at,
                        processed_status
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?,
                        SYSUTCDATETIME(),
                        SYSUTCDATETIME(),
                        'pending'
                    )
                    """,
                    source_id,
                    config.entity,
                    source_record_id,
                    query_keyword,
                    pipeline_run_id,
                    raw_data,
                )
            else:
                cursor.execute(
                    f"""
                    INSERT INTO {config.table_name} (
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
                    VALUES (
                        ?, ?, ?, ?, ?, ?,
                        SYSUTCDATETIME(),
                        SYSUTCDATETIME(),
                        'pending'
                    )
                    """,
                    source_id,
                    config.entity,
                    source_record_id,
                    source_record_url,
                    pipeline_run_id,
                    raw_data,
                )

            changed_count += 1

        conn.commit()

    return changed_count
