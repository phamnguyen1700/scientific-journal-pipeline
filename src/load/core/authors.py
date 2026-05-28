from src.config.sqlserver import get_connection
from src.load.canonical_loader import fetch_mapping_id, json_or_none
from src.load.pipeline_run_loader import get_source_id


def upsert_author_detail(
    author: dict,
    source_id: str | None = None,
    raw_author_id: str | None = None,
) -> str | None:
    source_record_id = author.get("source_record_id")
    if not source_record_id:
        return None

    source_id = source_id or get_source_id("OpenAlex")

    with get_connection() as conn:
        cursor = conn.cursor()
        author_id = fetch_mapping_id(
            cursor,
            "core.author_source_mappings",
            "author_id",
            source_id,
            source_record_id,
        )

        params = (
            author.get("display_name") or source_record_id,
            author.get("full_name"),
            author.get("orcid"),
            author.get("works_count"),
            author.get("cited_by_count"),
            author.get("h_index"),
            author.get("i10_index"),
            author.get("two_year_mean_citedness"),
            json_or_none(author.get("raw_author_names")),
            json_or_none(author.get("display_name_alternatives")),
            json_or_none(author.get("affiliations")),
            json_or_none(author.get("last_known_institutions")),
            json_or_none(author.get("topics")),
            json_or_none(author.get("topic_share")),
            json_or_none(author.get("x_concepts")),
            json_or_none(author.get("counts_by_year")),
            author.get("works_api_url"),
            author.get("source_created_date"),
            author.get("source_updated_date"),
        )

        if author_id:
            cursor.execute(
                """
                UPDATE core.authors
                SET
                    display_name = ?,
                    full_name = ?,
                    orcid = ?,
                    works_count = ?,
                    cited_by_count = ?,
                    h_index = ?,
                    i10_index = ?,
                    two_year_mean_citedness = ?,
                    raw_author_names = ?,
                    display_name_alternatives = ?,
                    affiliations = ?,
                    last_known_institutions = ?,
                    topics = ?,
                    topic_share = ?,
                    x_concepts = ?,
                    counts_by_year = ?,
                    works_api_url = ?,
                    source_created_date = ?,
                    source_updated_date = ?,
                    updated_at = SYSUTCDATETIME()
                WHERE author_id = ?
                """,
                *params,
                author_id,
            )

            if raw_author_id:
                cursor.execute(
                    """
                    UPDATE core.author_source_mappings
                    SET
                        raw_author_id = ?,
                        source_record_url = ?,
                        source_specific_data = ?
                    WHERE source_id = ?
                    AND source_record_id = ?
                    """,
                    raw_author_id,
                    author.get("source_record_url"),
                    json_or_none(author),
                    source_id,
                    source_record_id,
                )
        else:
            cursor.execute(
                """
                INSERT INTO core.authors (
                    display_name,
                    full_name,
                    orcid,
                    works_count,
                    cited_by_count,
                    h_index,
                    i10_index,
                    two_year_mean_citedness,
                    raw_author_names,
                    display_name_alternatives,
                    affiliations,
                    last_known_institutions,
                    topics,
                    topic_share,
                    x_concepts,
                    counts_by_year,
                    works_api_url,
                    source_created_date,
                    source_updated_date,
                    updated_at
                )
                OUTPUT INSERTED.author_id
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME())
                """,
                *params,
            )
            author_id = str(cursor.fetchone().author_id)
            cursor.execute(
                """
                INSERT INTO core.author_source_mappings (
                    author_id,
                    source_id,
                    raw_author_id,
                    source_record_id,
                    source_record_url,
                    source_specific_data
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                author_id,
                source_id,
                raw_author_id,
                source_record_id,
                author.get("source_record_url"),
                json_or_none(author),
            )

        conn.commit()
        return author_id
