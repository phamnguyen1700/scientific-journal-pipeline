# AWS EC2 Deployment Notes

This document captures the current deployment path for the Scientific Journal Pipeline.

## Current Target

- AWS EC2 Ubuntu
- Docker Compose
- SQL Server 2022 container
- Python pipeline container
- Airflow will be added after the pipeline container is verified on EC2

## Repository Layout

```text
src/                    Pipeline source code
docs/                   Handover and operation documents
sql/database_ver7.sql   Fresh database bootstrap script
Dockerfile              Python pipeline image
docker-compose.yml      SQL Server and pipeline services
.env.example            Environment variable template
requirements.txt        Python dependencies
```

## Database Bootstrap

Run `sql/database_ver7.sql` against the SQL Server instance from SSMS or another SQL Server client.

The script creates the pipeline database, schemas, core tables, raw tables, ops tables, constraints, and seed records required by the pipeline.

## Runtime Users

- `sa`: admin only.
- `pipeline_user`: used by the Python pipeline. It writes to `raw`, `core`, and `ops`.
- `backend_user`: used by the backend API. It should read from `core` only.

## EC2 Security Group

Use IP-restricted inbound rules.

```text
22    SSH         your IP /32
1433  SQL Server  your IP and backend team IPs /32
8080  Airflow     your IP /32, later when Airflow is added
```

Do not open SQL Server with `0.0.0.0/0`.

## Local Test Against Cloud DB

Use `pipeline_user` in `.env`, then run:

```powershell
python -m src.jobs.sync.openalex_works --keywords "machine learning" --per-page 25 --max-pages-per-keyword 1 --page-delay-seconds 2 --enrich-authors --enrich-sources --enrich-limit 25
```

## Watermark Modes

- `initial`: no watermark yet, crawl keyword normally without an updated-date lower bound.
- `resume`: previous run stopped with a cursor, continue the same crawl window.
- `incremental`: completed previous window, crawl from the stored `last_to_updated_date`.

## Backup Marker

The first verified cloud backup is named:

```text
scientific_journal_tracking_db_pipeline_ready.bak
```

It means the database is ready for pipeline usage. Backend-specific tables can be added later.
