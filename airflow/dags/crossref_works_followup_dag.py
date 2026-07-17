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


with DAG(
    dag_id="crossref_works_followup",
    description="Run Crossref DOI follow-up checks for existing core papers.",
    default_args=DEFAULT_ARGS,
    start_date=pendulum.datetime(2026, 7, 1, tz="Asia/Ho_Chi_Minh"),
    schedule="0 4 * * 1",
    catchup=False,
    max_active_runs=1,
    tags=["crossref", "works", "followup", "dataops"],
) as dag:
    crossref_works_followup = BashOperator(
        task_id="crossref_works_followup",
        bash_command=(
            "cd /opt/airflow && "
            "python -m src.jobs.followup.crossref_works "
            "--limit 100 "
            "--page-delay-seconds 1"
        ),
    )
