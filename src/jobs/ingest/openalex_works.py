from src.extract.openalex_extractor import fetch_works_by_keyword

from src.load.pipeline_run_loader import (
    create_pipeline_run,
    mark_pipeline_run_success,
    mark_pipeline_run_failed,
)

from src.load.raw.entities import load_raw_entities


def run_openalex_raw_ingestion(
    keyword: str,
    per_page: int = 5,
) -> int:

    source_name = "OpenAlex"
    source_entity = "works"

    run_id = create_pipeline_run(
        source_name=source_name,
        source_entity=source_entity,
        query_keyword=keyword,
    )

    try:
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
            f"Raw ingestion success: "
            f"fetched={len(raw_items)}, "
            f"inserted={inserted_count}"
        )

        return inserted_count

    except Exception as error:

        mark_pipeline_run_failed(
            run_id=run_id,
            error_message=str(error),
        )

        print(f"Pipeline failed: {error}")

        return 0
