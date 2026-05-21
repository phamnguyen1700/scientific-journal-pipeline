from src.config.sqlserver import get_connection
from src.jobs.process_raw_papers import process_pending_raw_papers


def queue_raw_papers_for_reprocess(
    limit: int | None = None,
    source_record_id: str | None = None,
) -> int:
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
                UPDATE raw.works
                SET
                    processed_status = 'pending',
                    process_error = NULL
                WHERE raw_work_id IN (
                    SELECT TOP (?) raw_work_id
                    FROM raw.works
                    WHERE {' AND '.join(filters)}
                    ORDER BY fetched_at ASC
                )
                """,
                *params,
            )
        else:
            cursor.execute(
                f"""
                UPDATE raw.works
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


def reprocess_raw_papers(
    limit: int | None = None,
    source_record_id: str | None = None,
) -> int:
    queued_count = queue_raw_papers_for_reprocess(
        limit=limit,
        source_record_id=source_record_id,
    )

    if queued_count > 0:
        process_pending_raw_papers(limit=queued_count)

    return queued_count


if __name__ == "__main__":
    reprocess_raw_papers()
