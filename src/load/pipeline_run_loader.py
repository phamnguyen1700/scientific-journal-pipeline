from datetime import datetime, timezone

from bson import ObjectId

from src.config.mongodb import get_database

db = get_database()


def create_pipeline_run(
    source_name: str, source_entity: str, query_keyword: str
) -> ObjectId:
    run_doc = {
        "source_name": source_name,
        "source_entity": source_entity,
        "query_keyword": query_keyword,
        "status": "running",
        "started_at": datetime.now(timezone.utc),
        "finished_at": None,
        "records_fetched": 0,
        "records_inserted": 0,
        "records_failed": 0,
        "error_message": None,
    }

    result = db.raw_pipeline_runs.insert_one(run_doc)

    return result.inserted_id


def mark_pipeline_run_success(
    run_id: ObjectId,
    records_fetched: int,
    records_inserted: int,
    records_failed: int = 0,
) -> None:
    db.raw_pipeline_runs.update_one(
        {"_id": run_id},
        {
            "$set": {
                "status": "success",
                "finished_at": datetime.now(timezone.utc),
                "records_fetched": records_fetched,
                "records_inserted": records_inserted,
                "records_failed": records_failed,
            }
        },
    )


def mark_pipeline_run_failed(run_id: ObjectId, error_message: str) -> None:
    db.raw_pipeline_runs.update_one(
        {"_id": run_id},
        {
            "$set": {
                "status": "failed",
                "finished_at": datetime.now(timezone.utc),
                "error_message": error_message,
            }
        },
    )
