def normalize_type_code(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().lower()


def get_or_create_journal_type(cursor, type_code: str | None) -> str | None:
    normalized_type_code = normalize_type_code(type_code)
    if not normalized_type_code:
        return None

    cursor.execute(
        """
        SELECT journal_type_id
        FROM core.journal_types
        WHERE type_code = ?
        """,
        normalized_type_code,
    )
    row = cursor.fetchone()
    if row:
        return str(row.journal_type_id)

    cursor.execute(
        """
        INSERT INTO core.journal_types (
            type_code,
            display_name,
            updated_at
        )
        OUTPUT INSERTED.journal_type_id
        VALUES (?, ?, SYSUTCDATETIME())
        """,
        normalized_type_code,
        normalized_type_code.replace("-", " ").title(),
    )
    return str(cursor.fetchone().journal_type_id)
