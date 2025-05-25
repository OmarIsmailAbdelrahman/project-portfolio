from airflow import DAG
# from airflow.operators.bash import BashOperator
from airflow.providers.google.cloud.operators.dataflow import DataflowStartFlexTemplateOperator

from datetime import datetime, timedelta

def make_flex_name():
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    return f"flex-shudl-{ts}"


# Your static settings
PROJECT_ID            = ""
REGION                = "us-central1"
BUCKET                = ""
SDK_CONTAINER_IMAGE   = f"gcr.io/{PROJECT_ID}/dataflow-flex-template:test2"


with DAG(
    "daily_sftp_to_gcs_v2",
    # start_date=datetime(2025,5,22),
    schedule="@daily",
    catchup=False,
    default_args={"owner":"omar_ismail","retries":1, "retry_delay":timedelta(minutes=10)},
    tags=["personal","dataflow","flex","sftp"]

) as dag:


    launch_flex = DataflowStartFlexTemplateOperator(
        task_id="launch_flex",
        project_id=PROJECT_ID,
        location=REGION,
        gcp_conn_id="google_cloud_default", # Conn Id in Airflow, will require service account from GCP with permissions {Dataflow admin, storage viewer, service account user}
        body={
            "launchParameter": {
                "jobName": make_flex_name(), # Job name
                "containerSpecGcsPath":
                  f"gs://{BUCKET}/dataflow_template_configuration.json", # Flex Template file
                # flex‐template parameters
                "parameters": {
                    "sdk_container_image": SDK_CONTAINER_IMAGE,
                    "project": PROJECT_ID,
                    "secret_name": "",
                    "rclone_remote": "", # RClone remote name
                    "remote_dir": "", # Remote Directory
                    "host": "", # IP
                    "user": "", # user
                    "port": "22",
                    "bucket_name": BUCKET,
                },
            }
        },
    )
