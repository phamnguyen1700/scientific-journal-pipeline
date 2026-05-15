from datetime import datetime, timezone

from bson import ObjectId
from pymongo import UpdateOne

from src.config.mongodb import get_database

db = get_database()


def load_raw_papers(
    raw_items: list[dict],
    source_name: str,
    source_entity: str,
    query_keyword: str,
    pipeline_run_id: ObjectId,
) -> int:
    if not raw_items:
        return 0

    operations = []

    now = datetime.now(timezone.utc)

    for item in raw_items:
        source_record_id = item.get("id")

        if not source_record_id:
            continue

        operations.append(
            UpdateOne(
                {
                    "source_name": source_name,
                    "source_record_id": source_record_id,
                },
                {
                    "$setOnInsert": {
                        "source_name": source_name,
                        "source_entity": source_entity,
                        "source_record_id": source_record_id,
                        "raw_data": item,
                        "fetched_at": now,
                        "processed_status": "pending",
                    },
                    "$set": {
                        "query_keyword": query_keyword,
                        "pipeline_run_id": pipeline_run_id,
                        "last_seen_at": now,
                    },
                },
                upsert=True,
            )
        )

    if not operations:
        return 0

    result = db.raw_papers.bulk_write(
        operations,
        ordered=False,
    )

    return result.upserted_count
