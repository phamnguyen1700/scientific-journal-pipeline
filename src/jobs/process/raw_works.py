import argparse

from src.config.settings import DEFAULT_BATCH_SIZE
from src.jobs.process.raw_processor import process_pending_raw_entities
from src.load.canonical_loader import (
    upsert_authors,
    upsert_journal,
    upsert_keywords,
    upsert_paper,
    upsert_topics,
)
from src.load.pipeline_run_loader import get_source_id
from src.transform.openalex.works import (
    transform_authors,
    transform_journal,
    transform_keywords,
    transform_paper,
    transform_topics,
)


def handle_raw_work(raw: dict, raw_work_id: str) -> str:
    source_id = get_source_id("OpenAlex")

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

    upsert_topics(
        topics,
        paper_id=paper_id,
        source_id=source_id,
    )

    return f"Processed work: {paper['source_record_id']} | {paper['title']}"


def process_pending_raw_works(limit: int = DEFAULT_BATCH_SIZE) -> None:
    process_pending_raw_entities(
        entity="works",
        limit=limit,
        handle_raw_record=handle_raw_work,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Process pending raw OpenAlex works.")
    parser.add_argument("--limit", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()

    process_pending_raw_works(limit=args.limit)


if __name__ == "__main__":
    main()
