import argparse

from src.config.settings import DEFAULT_BATCH_SIZE
from src.jobs.enrich.openalex_authors import enrich_openalex_authors
from src.jobs.enrich.openalex_sources import enrich_openalex_sources


def enrich_openalex_all(
    authors_limit: int = DEFAULT_BATCH_SIZE,
    sources_limit: int = DEFAULT_BATCH_SIZE,
    process_after_enrich: bool = True,
) -> None:
    print("\n=== Enriching OpenAlex authors ===")
    enrich_openalex_authors(
        limit=authors_limit,
        process_after_enrich=process_after_enrich,
    )

    print("\n=== Enriching OpenAlex sources ===")
    enrich_openalex_sources(
        limit=sources_limit,
        process_after_enrich=process_after_enrich,
    )

    print("\nOpenAlex enrichment completed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OpenAlex enrichment jobs.")
    parser.add_argument("--authors-limit", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--sources-limit", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--skip-process", action="store_true")
    args = parser.parse_args()

    enrich_openalex_all(
        authors_limit=args.authors_limit,
        sources_limit=args.sources_limit,
        process_after_enrich=not args.skip_process,
    )


if __name__ == "__main__":
    main()
