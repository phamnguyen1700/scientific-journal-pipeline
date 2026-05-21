# SQL Server Migration Notes

## Data Flow

```text
Seed keywords
    -> OpenAlex API
    -> raw.pipeline_runs
    -> raw.works
    -> process pending raw records
    -> transform raw JSON
    -> core journals/papers/authors/keywords
    -> source mapping and relation tables
```

## Detailed Flow

1. `src/main.py` reads keywords from `src/config/seed_keywords.py`.
2. For each keyword, `src/jobs/ingest_openalex.py` starts a pipeline run.
3. `src/load/pipeline_run_loader.py` writes the run to `raw.pipeline_runs`.
4. `src/extract/openalex_extractor.py` calls the OpenAlex `/works` API.
5. `src/load/raw_loader.py` stores each raw work in `raw.works`.
6. Raw records are deduplicated by `(source_id, source_record_id)`.
7. `src/jobs/process_raw_papers.py` reads pending records from `raw.works`.
8. `src/transform/normalize_papers.py` converts OpenAlex raw JSON into normalized Python dictionaries.
9. `src/load/canonical_loader.py` writes normalized data into `core.*` tables.
10. On success, `raw.works.processed_status` becomes `processed`.
11. On failure, `raw.works.processed_status` becomes `failed` and `process_error` stores the error.

## Source Mapping Design

SQL Server uses internal GUID primary keys:

```text
core.papers.paper_id
core.authors.author_id
core.journals.journal_id
core.keywords.keyword_id
```

External IDs from OpenAlex or future sources such as Crossref are not stored as primary keys.
They are stored in source mapping tables:

```text
core.paper_source_mappings.source_record_id
core.author_source_mappings.source_record_id
core.journal_source_mappings.source_record_id
core.keyword_source_mappings.source_record_id
```

Example:

```text
core.papers.paper_id = SQL Server GUID
core.paper_source_mappings.source_record_id = W2891503716
```

This keeps the database ready for multiple data sources.

## Main Tables

Raw layer:

```text
raw.api_sources
raw.pipeline_runs
raw.works
```

Core layer:

```text
core.papers
core.paper_source_mappings
core.journals
core.journal_source_mappings
core.authors
core.author_source_mappings
core.paper_authors
core.keywords
core.keyword_source_mappings
core.paper_keywords
```

## What Was Changed

- Replaced MongoDB configuration with SQL Server configuration.
- Removed MongoDB usage from loaders and jobs.
- Added `pyodbc` as the SQL Server driver dependency.
- Added `src/config/sqlserver.py` for SQL Server connection creation.
- Updated `.env` to use SQL Server settings.
- Reworked raw ingestion to write to `raw.pipeline_runs` and `raw.works`.
- Reworked pending raw processing to read from `raw.works`.
- Reworked canonical loading to write to SQL Server `core.*` tables.
- Changed transform output to use source-neutral names:
  - `source_record_id`
  - `source_record_url`
- Added abstract reconstruction from OpenAlex `abstract_inverted_index`.
- Added mapping for paper fields:
  - `abstract`
  - `volume`
  - `issue`
  - `page`
  - `is_retracted`
- Added mapping for journal `is_core`.
- Added mapping for author affiliations.
- Added `src/jobs/reprocess_raw_papers.py` for rebuilding core data from existing raw records.
- Updated `README.md` with setup, run, and reprocess commands.

## Important Commands

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the normal pipeline:

```powershell
python -m src.main
```

Run without activating venv:

```powershell
.\venv\Scripts\python.exe -m src.main
```

Reprocess existing raw data:

```powershell
python -m src.jobs.reprocess_raw_papers
```

Reprocess without activating venv:

```powershell
.\venv\Scripts\python.exe -m src.jobs.reprocess_raw_papers
```

## Normal Pipeline vs Reprocess

Normal pipeline:

```text
OpenAlex API
    -> raw.works
    -> core.*
```

Reprocess:

```text
existing raw.works.raw_data
    -> transform again
    -> update core.*
```

Reprocess does not call the OpenAlex API. It only rebuilds canonical data from raw records already stored in SQL Server.

Use reprocess when:

- transform logic changes
- loader mapping changes
- schema mapping changes
- old core records have missing fields that can be rebuilt from raw JSON

## Current Notes

- `topics` are transformed but not stored yet because the current SQL schema does not include `core.topics` or `core.paper_topics`.
- `concepts`, `locations`, `funders`, `APC`, and citation percentile fields are still available in raw JSON but are not fully mapped to core tables.
- User features from the project requirement are not implemented in this ingestion pipeline yet:
  - authentication
  - bookmarks
  - following journals/topics
  - notifications
  - dashboard reports
  - admin management
- `create_indexes.py` is currently a no-op because SQL indexing is handled separately.

## Files Changed

```text
.env
README.md
requirements.txt
src/config/settings.py
src/config/sqlserver.py
src/config/mongodb.py
src/extract/openalex_extractor.py
src/jobs/ingest_openalex.py
src/jobs/process_raw_papers.py
src/jobs/reprocess_raw_papers.py
src/load/pipeline_run_loader.py
src/load/raw_loader.py
src/load/canonical_loader.py
src/scripts/create_indexes.py
src/transform/normalize_papers.py
```
