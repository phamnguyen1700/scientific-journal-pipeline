from pymongo import UpdateOne

from src.config.mongodb import get_database

db = get_database()


def upsert_paper(paper: dict) -> None:
    db.papers.update_one(
        {"paper_id": paper["paper_id"]},
        {"$set": paper},
        upsert=True,
    )


def upsert_authors(authors: list[dict]) -> None:
    if not authors:
        return

    ops = [
        UpdateOne(
            {"author_id": author["author_id"]},
            {"$set": author},
            upsert=True,
        )
        for author in authors
        if author.get("author_id")
    ]

    if ops:
        db.authors.bulk_write(ops, ordered=False)


def upsert_journal(journal: dict | None) -> None:
    if not journal:
        return

    db.journals.update_one(
        {"journal_id": journal["journal_id"]},
        {"$set": journal},
        upsert=True,
    )


def upsert_keywords(keywords: list[dict]) -> None:
    if not keywords:
        return

    ops = [
        UpdateOne(
            {"keyword_id": keyword["keyword_id"]},
            {"$set": keyword},
            upsert=True,
        )
        for keyword in keywords
    ]

    db.keywords.bulk_write(ops, ordered=False)


def upsert_topics(topics: list[dict]) -> None:
    if not topics:
        return

    ops = [
        UpdateOne(
            {"topic_id": topic["topic_id"]},
            {"$set": topic},
            upsert=True,
        )
        for topic in topics
    ]

    db.research_topics.bulk_write(ops, ordered=False)


def mark_raw_processed(raw_id) -> None:
    db.raw_papers.update_one(
        {"_id": raw_id},
        {"$set": {"processed_status": "processed"}},
    )


def mark_raw_failed(raw_id, error_message: str) -> None:
    db.raw_papers.update_one(
        {"_id": raw_id},
        {
            "$set": {
                "processed_status": "failed",
                "process_error": error_message,
            }
        },
    )
