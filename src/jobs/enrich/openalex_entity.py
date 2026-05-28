from collections.abc import Callable

from src.extract.openalex_extractor import fetch_openalex_entity_record
from src.load.pipeline_run_loader import (
    create_pipeline_run,
    mark_pipeline_run_failed,
    mark_pipeline_run_success,
)
from src.load.raw.entities import load_raw_entities


def enrich_openalex_entity(
    entity: str,
    source_record_ids: list[str],
    process_pending_raw: Callable[[int], None] | None = None,
    process_after_enrich: bool = True,
    process_limit: int | None = None,
) -> int:
    source_name = "OpenAlex"

    run_id = create_pipeline_run(
        source_name=source_name,
        source_entity=entity,
        query_keyword=f"enrich:{entity}",
    )

    fetched_count = 0
    failed_count = 0
    raw_items = []

    try:
        for source_record_id in source_record_ids:
            try:
                raw_items.append(
                    fetch_openalex_entity_record(
                        entity=entity,
                        source_record_id=source_record_id,
                    )
                )
                fetched_count += 1
            except Exception as error:
                failed_count += 1
                print(f"Failed to fetch {entity} {source_record_id}: {error}")

        changed_count = load_raw_entities(
            raw_items=raw_items,
            source_name=source_name,
            entity=entity,
            pipeline_run_id=run_id,
        )

        mark_pipeline_run_success(
            run_id=run_id,
            records_fetched=fetched_count,
            records_inserted=changed_count,
            records_failed=failed_count,
        )

        print(
            f"OpenAlex {entity} enrich success: "
            f"selected={len(source_record_ids)}, "
            f"fetched={fetched_count}, "
            f"changed={changed_count}, "
            f"failed={failed_count}"
        )

        if process_after_enrich and changed_count > 0 and process_pending_raw:
            process_pending_raw(process_limit or changed_count)

        return changed_count

    except Exception as error:
        mark_pipeline_run_failed(run_id=run_id, error_message=str(error))
        print(f"OpenAlex {entity} enrich failed: {error}")
        return 0
