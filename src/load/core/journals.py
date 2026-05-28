from src.config.sqlserver import get_connection
from src.load.canonical_loader import (
    bool_or_none,
    fetch_mapping_id,
    json_or_none,
    upsert_taxonomy_level,
)
from src.load.pipeline_run_loader import get_source_id


def upsert_journal_detail(
    journal: dict,
    source_id: str | None = None,
    raw_source_id: str | None = None,
) -> str | None:
    source_record_id = journal.get("source_record_id")
    if not source_record_id:
        return None

    source_id = source_id or get_source_id("OpenAlex")
    issn = journal.get("issn") or []
    issn_print = issn[0] if len(issn) > 0 else None
    issn_electronic = issn[1] if len(issn) > 1 else None

    params = (
        journal.get("display_name") or source_record_id,
        journal.get("issn_l"),
        issn_print,
        issn_electronic,
        journal.get("host_organization_name"),
        journal.get("type"),
        journal.get("homepage_url"),
        journal.get("country_code"),
        journal.get("works_count"),
        journal.get("cited_by_count"),
        journal.get("oa_works_count"),
        journal.get("h_index"),
        journal.get("i10_index"),
        journal.get("two_year_mean_citedness"),
        bool_or_none(journal.get("is_oa")),
        bool_or_none(journal.get("is_in_doaj")),
        bool_or_none(journal.get("is_core")),
        journal.get("first_publication_year"),
        journal.get("last_publication_year"),
        json_or_none(journal.get("counts_by_year")),
        journal.get("source_created_date"),
        journal.get("source_updated_date"),
    )

    with get_connection() as conn:
        cursor = conn.cursor()
        journal_id = fetch_mapping_id(
            cursor,
            "core.journal_source_mappings",
            "journal_id",
            source_id,
            source_record_id,
        )

        if journal_id:
            cursor.execute(
                """
                UPDATE core.journals
                SET
                    journal_name = ?,
                    issn_l = ?,
                    issn_print = ?,
                    issn_electronic = ?,
                    host_organization_name = ?,
                    journal_type = ?,
                    homepage_url = ?,
                    country_code = ?,
                    works_count = ?,
                    cited_by_count = ?,
                    oa_works_count = ?,
                    h_index = ?,
                    i10_index = ?,
                    two_year_mean_citedness = ?,
                    is_open_access = ?,
                    is_in_doaj = ?,
                    is_core = ?,
                    first_publication_year = ?,
                    last_publication_year = ?,
                    counts_by_year = ?,
                    source_created_date = ?,
                    source_updated_date = ?,
                    updated_at = SYSUTCDATETIME()
                WHERE journal_id = ?
                """,
                *params,
                journal_id,
            )

            if raw_source_id:
                cursor.execute(
                    """
                    UPDATE core.journal_source_mappings
                    SET
                        raw_source_id = ?,
                        source_record_url = ?,
                        source_specific_data = ?
                    WHERE source_id = ?
                      AND source_record_id = ?
                    """,
                    raw_source_id,
                    journal.get("source_record_url"),
                    json_or_none(journal),
                    source_id,
                    source_record_id,
                )
        else:
            cursor.execute(
                """
                INSERT INTO core.journals (
                    journal_name,
                    issn_l,
                    issn_print,
                    issn_electronic,
                    host_organization_name,
                    journal_type,
                    homepage_url,
                    country_code,
                    works_count,
                    cited_by_count,
                    oa_works_count,
                    h_index,
                    i10_index,
                    two_year_mean_citedness,
                    is_open_access,
                    is_in_doaj,
                    is_core,
                    first_publication_year,
                    last_publication_year,
                    counts_by_year,
                    source_created_date,
                    source_updated_date,
                    updated_at
                )
                OUTPUT INSERTED.journal_id
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME())
                """,
                *params,
            )
            journal_id = str(cursor.fetchone().journal_id)
            cursor.execute(
                """
                INSERT INTO core.journal_source_mappings (
                    journal_id,
                    source_id,
                    raw_source_id,
                    source_record_id,
                    source_record_url,
                    source_specific_data
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                journal_id,
                source_id,
                raw_source_id,
                source_record_id,
                journal.get("source_record_url"),
                json_or_none(journal),
            )

        upsert_journal_topics(
            cursor=cursor,
            journal_id=journal_id,
            source_id=source_id,
            topics=journal.get("topics") or [],
            topic_share=journal.get("topic_share") or [],
        )

        conn.commit()
        return journal_id


def upsert_journal_topics(
    cursor,
    journal_id: str,
    source_id: str,
    topics: list[dict],
    topic_share: list[dict],
) -> None:
    by_source_record_id = {}

    for topic in topics:
        source_record_id = topic.get("source_record_id")
        if source_record_id:
            by_source_record_id[source_record_id] = dict(topic)

    for shared_topic in topic_share:
        source_record_id = shared_topic.get("source_record_id")
        if not source_record_id:
            continue

        merged = by_source_record_id.setdefault(source_record_id, dict(shared_topic))
        merged["topic_share"] = shared_topic.get("topic_share")

    for topic in by_source_record_id.values():
        topic_id = upsert_source_topic(cursor, topic, source_id)
        if not topic_id:
            continue

        cursor.execute(
            """
            IF EXISTS (
                SELECT 1
                FROM core.journal_topics
                WHERE journal_id = ?
                  AND topic_id = ?
                  AND source_id = ?
            )
            UPDATE core.journal_topics
            SET
                works_count = ?,
                topic_share = ?
            WHERE journal_id = ?
              AND topic_id = ?
              AND source_id = ?
            ELSE
            INSERT INTO core.journal_topics (
                journal_id,
                topic_id,
                works_count,
                topic_share,
                source_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            journal_id,
            topic_id,
            source_id,
            topic.get("count"),
            topic.get("topic_share"),
            journal_id,
            topic_id,
            source_id,
            journal_id,
            topic_id,
            topic.get("count"),
            topic.get("topic_share"),
            source_id,
        )


def upsert_source_topic(cursor, topic: dict, source_id: str) -> str | None:
    domain_id = upsert_taxonomy_level(
        cursor=cursor,
        node=topic.get("domain"),
        source_id=source_id,
        entity_table="core.research_domains",
        entity_id_column="domain_id",
        entity_name_column="domain_name",
        mapping_table="core.domain_source_mappings",
    )

    field_id = upsert_taxonomy_level(
        cursor=cursor,
        node=topic.get("field"),
        source_id=source_id,
        entity_table="core.research_fields",
        entity_id_column="field_id",
        entity_name_column="field_name",
        mapping_table="core.field_source_mappings",
        parent_column="domain_id",
        parent_id=domain_id,
    )

    subfield_id = upsert_taxonomy_level(
        cursor=cursor,
        node=topic.get("subfield"),
        source_id=source_id,
        entity_table="core.research_subfields",
        entity_id_column="subfield_id",
        entity_name_column="subfield_name",
        mapping_table="core.subfield_source_mappings",
        parent_column="field_id",
        parent_id=field_id,
    )

    return upsert_taxonomy_level(
        cursor=cursor,
        node=topic,
        source_id=source_id,
        entity_table="core.research_topics",
        entity_id_column="topic_id",
        entity_name_column="topic_name",
        mapping_table="core.topic_source_mappings",
        parent_column="subfield_id",
        parent_id=subfield_id,
    )
