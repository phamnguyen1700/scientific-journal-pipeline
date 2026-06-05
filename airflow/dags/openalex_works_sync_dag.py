from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator


DEFAULT_ARGS = {
    "owner": "dataops",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

OPENALEX_KEYWORDS = [
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "computer vision",
    "natural language processing",
    "data mining",
]


with DAG(
    dag_id="openalex_works_sync",
    description="Sync OpenAlex works and enrich authors/sources into SQL Server.",
    default_args=DEFAULT_ARGS,
    start_date=pendulum.datetime(2026, 6, 1, tz="Asia/Ho_Chi_Minh"),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["openalex", "works", "dataops"],
) as dag:
    sync_openalex_works = BashOperator(
        task_id="sync_openalex_works",
        bash_command=(
            "python -m src.jobs.sync.openalex_works "
            f'--keywords "{",".join(OPENALEX_KEYWORDS)}" '
            "--per-page 25 "
            "--max-pages-per-keyword 1 "
            "--page-delay-seconds 2 "
            "--enrich-authors "
            "--enrich-sources "
            "--enrich-limit 25"
        ),
    )
