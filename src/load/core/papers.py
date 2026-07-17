from src.config.sqlserver import get_connection


def fetch_papers_for_crossref_followup(
    limit: int,
    include_checked: bool = False,
) -> list[dict]:
    checked_filter = ""
    if not include_checked:
        checked_filter = """
          AND NOT EXISTS (
              SELECT 1
              FROM enrich.paper_source_checks AS psc
              INNER JOIN raw.api_sources AS src
                  ON src.source_id = psc.source_id
              WHERE psc.paper_id = p.paper_id
                AND src.source_name = 'Crossref'
                AND psc.match_status IN ('matched', 'not_crossref', 'not_found')
          )
        """

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT TOP (?)
                p.paper_id,
                p.doi,
                p.title,
                p.publication_year,
                p.publication_date,
                p.journal_id
            FROM core.papers AS p
            WHERE p.doi IS NOT NULL
              AND LTRIM(RTRIM(p.doi)) <> ''
              {checked_filter}
            ORDER BY COALESCE(p.updated_at, p.created_at) DESC
            """,
            limit,
        )
        rows = cursor.fetchall()

    return [
        {
            "paper_id": str(row.paper_id),
            "doi": row.doi,
            "title": row.title,
            "publication_year": row.publication_year,
            "publication_date": row.publication_date,
            "journal_id": str(row.journal_id) if row.journal_id else None,
        }
        for row in rows
    ]


def fetch_paper_by_doi(doi: str) -> dict | None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT TOP (1)
                paper_id,
                doi,
                title,
                publication_year,
                publication_date,
                journal_id
            FROM core.papers
            WHERE LOWER(LTRIM(RTRIM(doi))) = LOWER(LTRIM(RTRIM(?)))
            ORDER BY COALESCE(updated_at, created_at) DESC
            """,
            doi,
        )
        row = cursor.fetchone()

    if not row:
        return None

    return {
        "paper_id": str(row.paper_id),
        "doi": row.doi,
        "title": row.title,
        "publication_year": row.publication_year,
        "publication_date": row.publication_date,
        "journal_id": str(row.journal_id) if row.journal_id else None,
    }
