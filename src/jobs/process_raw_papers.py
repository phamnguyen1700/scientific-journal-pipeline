import json

from src.config.sqlserver import get_connection
from src.load.pipeline_run_loader import get_source_id
from src.transform.normalize_papers import (
    transform_paper,
    transform_authors,
    transform_journal,
    transform_keywords,
    transform_topics,
)

from src.load.canonical_loader import (
    upsert_paper,
    upsert_authors,
    upsert_journal,
    upsert_keywords,
    upsert_topics,
    mark_raw_processed,
    mark_raw_failed,
)


def fetch_pending_raw_papers(limit: int) -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT TOP (?) raw_work_id, raw_data
            FROM raw.works
            WHERE processed_status = 'pending'
            ORDER BY fetched_at ASC
            """,
            limit,
        )
        return cursor.fetchall()


def process_pending_raw_papers(limit: int = 100) -> None:
    raw_docs = fetch_pending_raw_papers(limit)
    source_id = get_source_id("OpenAlex")

    for raw_doc in raw_docs:
        raw_work_id = str(raw_doc.raw_work_id)

        try:
            raw = json.loads(raw_doc.raw_data)

            paper = transform_paper(raw)

            if not paper.get("source_record_id") or not paper.get("title"):
                raise ValueError(
                    f"Invalid paper: missing source_record_id or title. raw_id={raw_work_id}"
                )

            authors = transform_authors(raw)
            journal = transform_journal(raw)
            keywords = transform_keywords(raw)
            topics = transform_topics(raw)

            journal_id = upsert_journal(journal, source_id=source_id)

            paper_id = upsert_paper(
                paper,
                journal_id=journal_id,
                source_id=source_id,
                raw_work_id=raw_work_id,
            )

            upsert_authors(
                authors,
                paper_id=paper_id,
                paper_authors=paper.get("authors", []),
                source_id=source_id,
            )

            upsert_keywords(
                keywords,
                paper_id=paper_id,
                source_id=source_id,
            )

            upsert_topics(topics)

            mark_raw_processed(raw_work_id)

            print(f"Processed: {paper['source_record_id']} | {paper['title']}")

        except Exception as error:
            mark_raw_failed(
                raw_work_id,
                str(error),
            )

            print(f"Failed raw paper {raw_work_id}: {error}")
