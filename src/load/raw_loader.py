import json

from src.config.sqlserver import get_connection
from src.load.pipeline_run_loader import get_source_id


def clean_source_record_id(value: str | None) -> str | None:
    if not value:
        return None
    return value.rstrip("/").split("/")[-1]


def load_raw_papers(
    raw_items: list[dict],
    source_name: str,
    source_entity: str,
    query_keyword: str,
    pipeline_run_id: str,
) -> int:
    if not raw_items:
        return 0

    source_id = get_source_id(source_name)
    inserted_count = 0

    with get_connection() as conn:
        cursor = conn.cursor()

        for item in raw_items:
            source_record_id = clean_source_record_id(item.get("id"))

            if not source_record_id:
                continue

            raw_data = json.dumps(item, ensure_ascii=False)

            cursor.execute(
                """
                SELECT raw_work_id
                FROM raw.works
                WHERE source_id = ?
                  AND source_record_id = ?
                """,
                source_id,
                source_record_id,
            )
            row = cursor.fetchone()

            if row:
                cursor.execute(
                    """
                    UPDATE raw.works
                    SET
                        source_entity = ?,
                        query_keyword = ?,
                        pipeline_run_id = ?,
                        raw_data = ?,
                        last_seen_at = SYSUTCDATETIME()
                    WHERE raw_work_id = ?
                    """,
                    source_entity,
                    query_keyword,
                    pipeline_run_id,
                    raw_data,
                    row.raw_work_id,
                )
                continue

            cursor.execute(
                """
                INSERT INTO raw.works (
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
                source_entity,
                source_record_id,
                query_keyword,
                pipeline_run_id,
                raw_data,
            )
            inserted_count += 1

        conn.commit()

    return inserted_count
