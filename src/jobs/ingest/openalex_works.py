from src.extract.openalex_extractor import fetch_works_by_keyword

from src.load.pipeline_run_loader import (
    create_pipeline_run,
    mark_pipeline_run_success,
    mark_pipeline_run_failed,
)

from src.load.ops.job_runs import (
    attach_pipeline_run,
    log_job,
    mark_job_run_failed,
    mark_job_run_success,
    start_job_run,
)
from src.load.ops.watermarks import mark_watermark_started, mark_watermark_success
from src.load.raw.entities import load_raw_entities
from src.utils.console import error as console_error
from src.utils.console import success as console_success


def run_openalex_raw_ingestion(
    keyword: str,
    per_page: int = 5,
) -> int:

    source_name = "OpenAlex"
    source_entity = "works"
    job_run_id = start_job_run(
        job_name="openalex_ingest_works",
        job_type="ingest",
        source_name=source_name,
        source_entity=source_entity,
        scope_type="keyword",
        scope_value=keyword,
        batch_size=per_page,
        metadata={"keyword": keyword, "per_page": per_page},
    )

    run_id = create_pipeline_run(
        source_name=source_name,
        source_entity=source_entity,
        query_keyword=keyword,
    )
    attach_pipeline_run(job_run_id, run_id)
    mark_watermark_started(
        source_name=source_name,
        source_entity=source_entity,
        scope_type="keyword",
        scope_value=keyword,
        metadata={"per_page": per_page, "job_run_id": job_run_id},
    )

    try:
        log_job(
            job_run_id,
            f"Fetching OpenAlex works for keyword: {keyword}",
            source_entity=source_entity,
            metadata={"keyword": keyword, "per_page": per_page},
        )
        raw_items = fetch_works_by_keyword(
            keyword=keyword,
            per_page=per_page,
        )

        inserted_count = load_raw_entities(
            raw_items=raw_items,
            source_name=source_name,
            entity=source_entity,
            query_keyword=keyword,
            pipeline_run_id=run_id,
        )

        mark_pipeline_run_success(
            run_id=run_id,
            records_fetched=len(raw_items),
            records_inserted=inserted_count,
        )

        print(
            console_success(
                f"Raw ingestion success: "
                f"fetched={len(raw_items)}, "
                f"inserted={inserted_count}"
            )
        )
        log_job(
            job_run_id,
            (
                f"Raw ingestion success: fetched={len(raw_items)}, "
                f"changed={inserted_count}"
            ),
            source_entity=source_entity,
            metadata={
                "keyword": keyword,
                "fetched": len(raw_items),
                "changed": inserted_count,
            },
        )
        mark_job_run_success(
            job_run_id=job_run_id,
            records_in=per_page,
            records_out=inserted_count,
            records_failed=0,
            metadata={"fetched": len(raw_items), "keyword": keyword},
        )
        mark_watermark_success(
            source_name=source_name,
            source_entity=source_entity,
            scope_type="keyword",
            scope_value=keyword,
            last_processed_record_id=raw_items[-1].get("id") if raw_items else None,
            metadata={
                "per_page": per_page,
                "fetched": len(raw_items),
                "changed": inserted_count,
                "job_run_id": job_run_id,
                "pipeline_run_id": run_id,
            },
        )

        return inserted_count

    except Exception as error:

        mark_pipeline_run_failed(
            run_id=run_id,
            error_message=str(error),
        )

        print(console_error(f"Pipeline failed: {error}"))
        log_job(
            job_run_id,
            f"OpenAlex works ingestion failed for keyword: {keyword}",
            log_level="error",
            source_entity=source_entity,
            error_detail=str(error),
            metadata={"keyword": keyword, "per_page": per_page},
        )
        mark_job_run_failed(
            job_run_id=job_run_id,
            error_message=str(error),
            records_in=per_page,
            records_out=0,
            records_failed=per_page,
            metadata={"keyword": keyword},
        )

        return 0
