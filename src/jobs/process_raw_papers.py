from src.config.mongodb import get_database

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

db = get_database()


def process_pending_raw_papers(limit: int = 100) -> None:

    raw_docs = db.raw_papers.find({"processed_status": "pending"}).limit(limit)

    for raw_doc in raw_docs:

        try:
            raw = raw_doc["raw_data"]

            paper = transform_paper(raw)

            if not paper.get("paper_id") or not paper.get("title"):
                raise ValueError(
                    f"Invalid paper: missing paper_id or title. raw_id={raw_doc['_id']}"
                )

            authors = transform_authors(raw)

            journal = transform_journal(raw)

            keywords = transform_keywords(raw)

            topics = transform_topics(raw)

            # load canonical collections

            upsert_journal(journal)

            upsert_authors(authors)

            upsert_keywords(keywords)

            upsert_topics(topics)

            upsert_paper(paper)

            # mark success

            mark_raw_processed(raw_doc["_id"])

            print(f"Processed: " f"{paper['paper_id']} | " f"{paper['title']}")

        except Exception as error:

            mark_raw_failed(
                raw_doc["_id"],
                str(error),
            )

            print(f"Failed raw paper " f"{raw_doc['_id']}: {error}")
