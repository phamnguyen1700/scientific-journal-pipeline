# Crossref Follow-Up Operations

This document describes the Crossref DOI follow-up pipeline. Crossref is used as
a post-OpenAlex checker/enrichment source. It does not overwrite canonical
records in `core.papers`.

## Purpose

The current source-of-record pipeline remains OpenAlex:

```text
OpenAlex -> raw.openalex_* -> transform -> core.*
```

Crossref runs after papers already exist in `core.papers`:

```text
core.papers with DOI
  -> Crossref /works/{doi}/agency
  -> Crossref /works/{doi}
  -> raw.crossref_works
  -> transform/compare
  -> enrich.paper_source_checks
  -> optional core.paper_source_mappings
```

## Endpoints

The MVP uses:

```text
GET https://api.crossref.org/works?rows=0
GET https://api.crossref.org/works/{doi}/agency
GET https://api.crossref.org/works/{doi}
```

Every request sends:

```text
mailto=<CROSSREF_MAILTO>
User-Agent: <CROSSREF_USER_AGENT> (mailto:<CROSSREF_MAILTO>)
```

## Environment

Set these values in `.env`:

```env
CROSSREF_BASE_URL=https://api.crossref.org
CROSSREF_MAILTO=your-team-email@example.com
CROSSREF_USER_AGENT=scientific-journal-pipeline/1.0
CROSSREF_PAGE_DELAY_SECONDS=1
```

`CROSSREF_MAILTO` should be a real team/project email.

## Database Migration

For an existing database, run:

```sql
sql/crossref_followup_migration.sql
```

This creates:

```text
raw.crossref_works
enrich.paper_source_checks
```

It also registers Crossref in:

```text
raw.api_sources
```

## Manual Run

Run the lightweight API healthcheck first:

```powershell
python -m src.jobs.followup.crossref_healthcheck
```

Run a small follow-up batch:

```powershell
python -m src.jobs.followup.crossref_works --limit 20
```

By default, this:

- selects existing `core.papers` with DOI,
- skips papers that already have a successful Crossref check,
- checks DOI agency,
- fetches Crossref work metadata,
- loads raw records into `raw.crossref_works`,
- processes changed raw records into `enrich.paper_source_checks`,
- does not update `core.papers`.

To insert matched DOI mappings into `core.paper_source_mappings`, add:

```powershell
python -m src.jobs.followup.crossref_works --limit 20 --add-mapping
```

The mapping keeps `raw_work_id = NULL` because that column currently references
`raw.openalex_works`.

## Reprocess

Use reprocess after changing Crossref transform or compare logic:

```powershell
python -m src.jobs.reprocess.crossref_raw_works --limit 100
```

Add mappings while reprocessing:

```powershell
python -m src.jobs.reprocess.crossref_raw_works --limit 100 --add-mapping
```

## Airflow

The DAG is separate from OpenAlex:

```text
airflow/dags/crossref_works_followup_dag.py
```

Trigger manually only after the manual run is healthy:

```bash
docker exec -it scientific-journal-airflow-scheduler airflow dags trigger crossref_works_followup
```

Keeping this DAG separate prevents Crossref rate limits or transient API issues
from failing the OpenAlex sync.

## Data Contract

Backend can continue reading from `core` as before.

Crossref outputs are optional operational/enrichment tables:

```text
raw.crossref_works
enrich.paper_source_checks
```

No backend change is required for the first phase.
