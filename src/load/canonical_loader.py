import json

from src.config.sqlserver import get_connection
from src.load.core.journal_types import get_or_create_journal_type, normalize_type_code
from src.load.pipeline_run_loader import get_source_id


def json_or_none(value) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def bool_or_none(value) -> bool | None:
    if value is None:
        return None
    return bool(value)


def fetch_mapping_id(
    cursor,
    table_name: str,
    id_column: str,
    source_id: str,
    source_record_id: str,
) -> str | None:
    cursor.execute(
        f"""
        SELECT {id_column}
        FROM {table_name}
        WHERE source_id = ?
          AND source_record_id = ?
        """,
        source_id,
        source_record_id,
    )
    row = cursor.fetchone()
    return str(getattr(row, id_column)) if row else None


def upsert_taxonomy_level(
    cursor,
    node: dict | None,
    source_id: str,
    entity_table: str,
    entity_id_column: str,
    entity_name_column: str,
    mapping_table: str,
    parent_column: str | None = None,
    parent_id: str | None = None,
) -> str | None:
    if not node or not node.get("display_name"):
        return None

    source_record_id = node.get("source_record_id")
    source_record_url = node.get("source_record_url")
    display_name = node["display_name"]

    if source_record_id:
        entity_id = fetch_mapping_id(
            cursor,
            mapping_table,
            entity_id_column,
            source_id,
            source_record_id,
        )
        if entity_id:
            cursor.execute(
                f"""
                UPDATE {entity_table}
                SET
                    {entity_name_column} = ?,
                    updated_at = SYSUTCDATETIME()
                WHERE {entity_id_column} = ?
                """,
                display_name,
                entity_id,
            )
            return entity_id

    if parent_column:
        cursor.execute(
            f"""
            SELECT {entity_id_column}
            FROM {entity_table}
            WHERE (
                ({parent_column} = ?)
                OR ({parent_column} IS NULL AND ? IS NULL)
            )
              AND normalized_name = LOWER(LTRIM(RTRIM(?)))
            """,
            parent_id,
            parent_id,
            display_name,
        )
    else:
        cursor.execute(
            f"""
            SELECT {entity_id_column}
            FROM {entity_table}
            WHERE normalized_name = LOWER(LTRIM(RTRIM(?)))
            """,
            display_name,
        )

    row = cursor.fetchone()

    if row:
        entity_id = str(getattr(row, entity_id_column))
    else:
        if parent_column:
            cursor.execute(
                f"""
                INSERT INTO {entity_table} (
                    {parent_column},
                    {entity_name_column},
                    updated_at
                )
                OUTPUT INSERTED.{entity_id_column}
                VALUES (?, ?, SYSUTCDATETIME())
                """,
                parent_id,
                display_name,
            )
        else:
            cursor.execute(
                f"""
                INSERT INTO {entity_table} (
                    {entity_name_column},
                    updated_at
                )
                OUTPUT INSERTED.{entity_id_column}
                VALUES (?, SYSUTCDATETIME())
                """,
                display_name,
            )
        entity_id = str(getattr(cursor.fetchone(), entity_id_column))

    if source_record_id:
        cursor.execute(
            f"""
            IF NOT EXISTS (
                SELECT 1
                FROM {mapping_table}
                WHERE source_id = ?
                  AND source_record_id = ?
            )
            INSERT INTO {mapping_table} (
                {entity_id_column},
                source_id,
                source_record_id,
                source_record_url,
                source_specific_data
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            source_id,
            source_record_id,
            entity_id,
            source_id,
            source_record_id,
            source_record_url,
            json_or_none(node),
        )

    return entity_id


def upsert_journal(journal: dict | None, source_id: str | None = None) -> str | None:
    if not journal or not journal.get("source_record_id"):
        return None

    source_id = source_id or get_source_id("OpenAlex")
    source_record_id = journal["source_record_id"]
    source_record_url = journal.get("source_record_url")
    issn = journal.get("issn") or []
    issn_print = issn[0] if len(issn) > 0 else None
    issn_electronic = issn[1] if len(issn) > 1 else None

    with get_connection() as conn:
        cursor = conn.cursor()
        journal_type = normalize_type_code(journal.get("type"))
        journal_type_id = get_or_create_journal_type(cursor, journal_type)
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
                    journal_type_id = ?,
                    is_open_access = ?,
                    is_in_doaj = ?,
                    is_core = ?,
                    updated_at = SYSUTCDATETIME()
                WHERE journal_id = ?
                """,
                journal.get("display_name") or source_record_id,
                journal.get("issn_l"),
                issn_print,
                issn_electronic,
                journal.get("host_organization_name"),
                journal_type,
                journal_type_id,
                bool_or_none(journal.get("is_oa")),
                bool_or_none(journal.get("is_in_doaj")),
                bool_or_none(journal.get("is_core")),
                journal_id,
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
                    journal_type_id,
                    is_open_access,
                    is_in_doaj,
                    is_core,
                    updated_at
                )
                OUTPUT INSERTED.journal_id
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME())
                """,
                journal.get("display_name") or source_record_id,
                journal.get("issn_l"),
                issn_print,
                issn_electronic,
                journal.get("host_organization_name"),
                journal_type,
                journal_type_id,
                bool_or_none(journal.get("is_oa")),
                bool_or_none(journal.get("is_in_doaj")),
                bool_or_none(journal.get("is_core")),
            )
            journal_id = str(cursor.fetchone().journal_id)
            cursor.execute(
                """
                INSERT INTO core.journal_source_mappings (
                    journal_id,
                    source_id,
                    source_record_id,
                    source_record_url,
                    source_specific_data
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                journal_id,
                source_id,
                source_record_id,
                source_record_url,
                json_or_none(journal),
            )

        conn.commit()
        return journal_id


def upsert_paper(
    paper: dict,
    journal_id: str | None = None,
    source_id: str | None = None,
    raw_work_id: str | None = None,
) -> str:
    source_id = source_id or get_source_id("OpenAlex")
    source_record_id = paper["source_record_id"]
    source_record_url = paper.get("source_record_url")
    open_access = paper.get("open_access") or {}

    with get_connection() as conn:
        cursor = conn.cursor()
        paper_id = fetch_mapping_id(
            cursor,
            "core.paper_source_mappings",
            "paper_id",
            source_id,
            source_record_id,
        )

        params = (
            paper.get("doi"),
            paper.get("title") or paper.get("display_name"),
            paper.get("abstract"),
            paper.get("publication_year"),
            paper.get("publication_date"),
            paper.get("type"),
            paper.get("language"),
            paper.get("cited_by_count"),
            paper.get("referenced_works_count"),
            paper.get("volume"),
            paper.get("issue"),
            paper.get("page"),
            bool_or_none(open_access.get("is_oa")),
            bool_or_none(paper.get("is_retracted")),
            journal_id,
            json_or_none(paper.get("referenced_works")),
            json_or_none(paper.get("related_works")),
            json_or_none(paper.get("abstract_inverted_index")),
            json_or_none(paper.get("counts_by_year")),
        )

        if paper_id:
            cursor.execute(
                """
                UPDATE core.papers
                SET
                    doi = ?,
                    title = ?,
                    abstract = ?,
                    publication_year = ?,
                    publication_date = ?,
                    paper_type = ?,
                    language = ?,
                    cited_by_count = ?,
                    reference_count = ?,
                    volume = ?,
                    issue = ?,
                    page = ?,
                    is_open_access = ?,
                    is_retracted = ?,
                    journal_id = ?,
                    referenced_works = ?,
                    related_works = ?,
                    abstract_inverted_index = ?,
                    counts_by_year = ?,
                    updated_at = SYSUTCDATETIME()
                WHERE paper_id = ?
                """,
                *params,
                paper_id,
            )
        else:
            cursor.execute(
                """
                INSERT INTO core.papers (
                    doi,
                    title,
                    abstract,
                    publication_year,
                    publication_date,
                    paper_type,
                    language,
                    cited_by_count,
                    reference_count,
                    volume,
                    issue,
                    page,
                    is_open_access,
                    is_retracted,
                    journal_id,
                    referenced_works,
                    related_works,
                    abstract_inverted_index,
                    counts_by_year,
                    updated_at
                )
                OUTPUT INSERTED.paper_id
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME())
                """,
                *params,
            )
            paper_id = str(cursor.fetchone().paper_id)
            cursor.execute(
                """
                INSERT INTO core.paper_source_mappings (
                    paper_id,
                    source_id,
                    raw_work_id,
                    source_record_id,
                    source_record_url,
                    source_specific_data
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                paper_id,
                source_id,
                raw_work_id,
                source_record_id,
                source_record_url,
                json_or_none({"primary_topic": paper.get("primary_topic")}),
            )

        conn.commit()
        return paper_id


def upsert_authors(
    authors: list[dict],
    paper_id: str | None = None,
    paper_authors: list[dict] | None = None,
    source_id: str | None = None,
) -> dict[str, str]:
    if not authors:
        return {}

    source_id = source_id or get_source_id("OpenAlex")
    author_ids = {}

    with get_connection() as conn:
        cursor = conn.cursor()

        for author in authors:
            source_record_id = author.get("source_record_id")
            if not source_record_id:
                continue

            author_id = fetch_mapping_id(
                cursor,
                "core.author_source_mappings",
                "author_id",
                source_id,
                source_record_id,
            )

            if author_id:
                cursor.execute(
                    """
                    UPDATE core.authors
                    SET
                        display_name = ?,
                        orcid = ?,
                        raw_author_names = ?,
                        affiliations = ?,
                        last_known_institutions = ?,
                        updated_at = SYSUTCDATETIME()
                    WHERE author_id = ?
                    """,
                    author.get("display_name") or source_record_id,
                    author.get("orcid"),
                    json_or_none(author.get("raw_author_names")),
                    json_or_none(author.get("affiliations")),
                    json_or_none(author.get("institutions")),
                    author_id,
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO core.authors (
                        display_name,
                        orcid,
                        raw_author_names,
                        affiliations,
                        last_known_institutions,
                        updated_at
                    )
                    OUTPUT INSERTED.author_id
                    VALUES (?, ?, ?, ?, ?, SYSUTCDATETIME())
                    """,
                    author.get("display_name") or source_record_id,
                    author.get("orcid"),
                    json_or_none(author.get("raw_author_names")),
                    json_or_none(author.get("affiliations")),
                    json_or_none(author.get("institutions")),
                )
                author_id = str(cursor.fetchone().author_id)
                cursor.execute(
                    """
                    INSERT INTO core.author_source_mappings (
                        author_id,
                        source_id,
                        source_record_id,
                        source_record_url,
                        source_specific_data
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    author_id,
                    source_id,
                    source_record_id,
                    author.get("source_record_url"),
                    json_or_none(author),
                )

            author_ids[source_record_id] = author_id

        if paper_id and paper_authors:
            for index, paper_author in enumerate(paper_authors, start=1):
                source_record_id = paper_author.get("source_record_id")
                author_id = author_ids.get(source_record_id)

                if not author_id:
                    continue

                cursor.execute(
                    """
                    IF NOT EXISTS (
                        SELECT 1
                        FROM core.paper_authors
                        WHERE paper_id = ?
                          AND author_id = ?
                    )
                    INSERT INTO core.paper_authors (
                        paper_id,
                        author_id,
                        author_order,
                        author_position,
                        raw_author_name,
                        is_corresponding
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    paper_id,
                    author_id,
                    paper_id,
                    author_id,
                    index,
                    paper_author.get("author_position"),
                    paper_author.get("raw_author_name"),
                    bool_or_none(paper_author.get("is_corresponding")),
                )

        conn.commit()

    return author_ids


def upsert_keywords(
    keywords: list[dict],
    paper_id: str | None = None,
    source_id: str | None = None,
) -> dict[str, str]:
    if not keywords:
        return {}

    source_id = source_id or get_source_id("OpenAlex")
    keyword_ids = {}

    with get_connection() as conn:
        cursor = conn.cursor()

        for keyword in keywords:
            source_record_id = keyword.get("source_record_id")
            keyword_name = keyword.get("display_name")

            if not source_record_id or not keyword_name:
                continue

            keyword_id = fetch_mapping_id(
                cursor,
                "core.keyword_source_mappings",
                "keyword_id",
                source_id,
                source_record_id,
            )

            if keyword_id:
                cursor.execute(
                    """
                    UPDATE core.keywords
                    SET
                        keyword_name = ?,
                        updated_at = SYSUTCDATETIME()
                    WHERE keyword_id = ?
                    """,
                    keyword_name,
                    keyword_id,
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO core.keywords (
                        keyword_name,
                        updated_at
                    )
                    OUTPUT INSERTED.keyword_id
                    VALUES (?, SYSUTCDATETIME())
                    """,
                    keyword_name,
                )
                keyword_id = str(cursor.fetchone().keyword_id)
                cursor.execute(
                    """
                    INSERT INTO core.keyword_source_mappings (
                        keyword_id,
                        source_id,
                        source_record_id,
                        source_record_url,
                        source_specific_data
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    keyword_id,
                    source_id,
                    source_record_id,
                    keyword.get("source_record_url"),
                    json_or_none(keyword),
                )

            keyword_ids[source_record_id] = keyword_id

            if paper_id:
                cursor.execute(
                    """
                    IF NOT EXISTS (
                        SELECT 1
                        FROM core.paper_keywords
                        WHERE paper_id = ?
                          AND keyword_id = ?
                          AND source_id = ?
                    )
                    INSERT INTO core.paper_keywords (
                        paper_id,
                        keyword_id,
                        score,
                        source_id
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    paper_id,
                    keyword_id,
                    source_id,
                    paper_id,
                    keyword_id,
                    keyword.get("score"),
                    source_id,
                )

        conn.commit()

    return keyword_ids


def upsert_topics(
    topics: list[dict],
    paper_id: str | None = None,
    source_id: str | None = None,
) -> dict[str, str]:
    if not topics:
        return {}

    source_id = source_id or get_source_id("OpenAlex")
    topic_ids = {}

    with get_connection() as conn:
        cursor = conn.cursor()

        for topic in topics:
            source_record_id = topic.get("source_record_id")

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

            topic_id = upsert_taxonomy_level(
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

            if not topic_id:
                continue

            if source_record_id:
                topic_ids[source_record_id] = topic_id

            if paper_id:
                cursor.execute(
                    """
                    IF NOT EXISTS (
                        SELECT 1
                        FROM core.paper_topics
                        WHERE paper_id = ?
                          AND topic_id = ?
                          AND source_id = ?
                    )
                    INSERT INTO core.paper_topics (
                        paper_id,
                        topic_id,
                        score,
                        source_id
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    paper_id,
                    topic_id,
                    source_id,
                    paper_id,
                    topic_id,
                    topic.get("score"),
                    source_id,
                )

        conn.commit()

    return topic_ids
