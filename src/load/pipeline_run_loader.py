from src.config.sqlserver import get_connection


def get_source_id(source_name: str, base_url: str | None = None) -> str:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT source_id
            FROM raw.api_sources
            WHERE source_name = ?
            """,
            source_name,
        )
        row = cursor.fetchone()

        if row:
            return str(row.source_id)

        cursor.execute(
            """
            INSERT INTO raw.api_sources (source_name, base_url)
            OUTPUT INSERTED.source_id
            VALUES (?, ?)
            """,
            source_name,
            base_url or "",
        )
        source_id = cursor.fetchone().source_id
        conn.commit()

        return str(source_id)


def create_pipeline_run(
    source_name: str,
    source_entity: str,
    query_keyword: str,
) -> str:
    source_id = get_source_id(source_name)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO raw.pipeline_runs (
                source_id,
                source_entity,
                query_keyword,
                status
            )
            OUTPUT INSERTED.run_id
            VALUES (?, ?, ?, 'running')
            """,
            source_id,
            source_entity,
            query_keyword,
        )
        run_id = cursor.fetchone().run_id
        conn.commit()

        return str(run_id)


def mark_pipeline_run_success(
    run_id: str,
    records_fetched: int,
    records_inserted: int,
    records_failed: int = 0,
) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE raw.pipeline_runs
            SET
                status = 'success',
                finished_at = SYSUTCDATETIME(),
                records_fetched = ?,
                records_inserted = ?,
                records_failed = ?
            WHERE run_id = ?
            """,
            records_fetched,
            records_inserted,
            records_failed,
            run_id,
        )
        conn.commit()


def mark_pipeline_run_failed(run_id: str, error_message: str) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE raw.pipeline_runs
            SET
                status = 'failed',
                finished_at = SYSUTCDATETIME(),
                error_message = ?
            WHERE run_id = ?
            """,
            error_message,
            run_id,
        )
        conn.commit()
