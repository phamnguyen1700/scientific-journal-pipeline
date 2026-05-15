from src.config.mongodb import get_database

db = get_database()


def create_indexes() -> None:

    # =========================
    # raw_papers
    # =========================

    db.raw_papers.create_index(
        [
            ("source_name", 1),
            ("source_record_id", 1),
        ],
        unique=True,
        name="uniq_source_record",
    )

    db.raw_papers.create_index(
        "processed_status",
        name="idx_processed_status",
    )

    db.raw_papers.create_index(
        "pipeline_run_id",
        name="idx_pipeline_run_id",
    )

    db.raw_papers.create_index(
        "fetched_at",
        name="idx_fetched_at",
    )

    # =========================
    # papers
    # =========================

    db.papers.create_index(
        "paper_id",
        unique=True,
        name="uniq_paper_id",
    )

    db.papers.create_index(
        "doi",
        sparse=True,
        name="idx_doi",
    )

    db.papers.create_index(
        "publication_year",
        name="idx_publication_year",
    )

    db.papers.create_index(
        "cited_by_count",
        name="idx_cited_by_count",
    )

    db.papers.create_index(
        "authors.author_id",
        name="idx_author_id",
    )

    db.papers.create_index(
        "journal.journal_id",
        name="idx_journal_id",
    )

    db.papers.create_index(
        "keywords.keyword_id",
        name="idx_keyword_id",
    )

    db.papers.create_index(
        "topics.topic_id",
        name="idx_topic_id",
    )

    db.papers.create_index(
        [("title", "text")],
        name="text_title",
    )

    # =========================
    # authors
    # =========================

    db.authors.create_index(
        "author_id",
        unique=True,
        name="uniq_author_id",
    )

    db.authors.create_index(
        [("display_name", "text")],
        name="text_author_name",
    )

    db.authors.create_index(
        "orcid",
        sparse=True,
        name="idx_orcid",
    )

    # =========================
    # journals
    # =========================

    db.journals.create_index(
        "journal_id",
        unique=True,
        name="uniq_journal_id",
    )

    db.journals.create_index(
        "display_name",
        name="idx_journal_name",
    )

    db.journals.create_index(
        "issn_l",
        sparse=True,
        name="idx_issn_l",
    )

    # =========================
    # keywords
    # =========================

    db.keywords.create_index(
        "keyword_id",
        unique=True,
        name="uniq_keyword_id",
    )

    db.keywords.create_index(
        "display_name",
        name="idx_keyword_name",
    )

    # =========================
    # research_topics
    # =========================

    db.research_topics.create_index(
        "topic_id",
        unique=True,
        name="uniq_topic_id",
    )

    db.research_topics.create_index(
        "display_name",
        name="idx_topic_name",
    )

    print("Indexes created successfully")


if __name__ == "__main__":
    create_indexes()
