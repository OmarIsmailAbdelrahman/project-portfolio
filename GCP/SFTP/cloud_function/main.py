import base64
import functions_framework
from google.cloud import bigquery
from google.cloud import pubsub_v1
import os

# dataflow flex template for result.parquet file 
# ——— NEW IMPORTS ———
from google.auth import default
from google.auth.transport.requests import AuthorizedSession
from datetime import datetime
# ————————————————————————————————————
def launch_flex_dataflow():
    # 1. Get ADC credentials
    creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    authed_sess = AuthorizedSession(creds)

    # 2. Prepare URL and body
    project = "omar-ismail-test-project"
    region  = "us-central1"
    url = (
        f"https://dataflow.googleapis.com/v1b3/projects/{project}"
        f"/locations/{region}/flexTemplates:launch"
    )
    body = {
      "launchParameter": {
        "jobName": f"flex-parquet-{datetime.utcnow():%Y%m%d-%H%M%S}",
        "containerSpecGcsPath": "gs://new_remove/dataflow_template_configuration-parquet-processing.json",
        "environment": {"tempLocation": "gs://new_remove/staging"},
        "parameters": {
          "sdk_container_image": "gcr.io/omar-ismail-test-project/dataflow-flex-template-parquest-processing:test1",
          "project": project,
          "schema_directory": "gs://new_remove/raw/result.parquet",
          "target_file_location": "gs://new_remove/raw/result.parquet",
          "result_file_location": "gs://new_remove/test_transformation/output2/encoded"
        }
      }
    }

    # 3. POST the launch request
    response = authed_sess.post(url, json=body)
    response.raise_for_status()
    return response.json()

# ————————————————————————————————————



client = bigquery.Client()

def load_parquet_to_bq(gcs_uri, dataset_id="my_dataset"):
    """
    Loads a Parquet file from GCS into BigQuery, truncating the target table.
    Example gcs_uri: "gs://new_remove/test_transformation/output2/encoded/encoded.parquet"
    """
    # pull out just the dataset name (drop any “/…” suffix)
    dataset = dataset_id.split('/', 1)[0]
    # table name = filename without “.parquet”
    table = gcs_uri.split('/')[-1].replace('.parquet', '')
    table_id = f"{client.project}.{dataset}.{table}"
    print("the table id is ", table_id)
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    load_job = client.load_table_from_uri(
        gcs_uri,
        table_id,
        job_config=job_config
    )
    load_job.result()  # waits for the load to complete
    print(f"Loaded Parquet into {table_id}")


def load_csv_to_bq(gcs_uri, dataset_id="my_dataset"):
    
    # if dataset_id contains a slash, take only the part before it:
    dataset = dataset_id.split('/', 1)[0]
    table   = gcs_uri.split('/')[-1].replace('.csv', '')
    table_id = f"{client.project}.{dataset}.{table}"
    
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
    )
    
    load_job = client.load_table_from_uri(gcs_uri, table_id, job_config=job_config)
    load_job.result()

def notify_dataflow(file_directory):
    topic_path = f"projects/{client.project}/topics/sftp_dataflow_v2"
    publisher = pubsub_v1.PublisherClient()
    publisher.publish(topic_path, data=file_directory.encode("utf-8"))
    print("Published to Dataflow:", file_directory)

# Triggered from a message on a Cloud Pub/Sub topic.
@functions_framework.cloud_event
def hello_pubsub(cloud_event):
    print("here is the message")

    bucket_id = cloud_event.data["message"]["attributes"]['bucketId']
    object_id = cloud_event.data["message"]["attributes"]['objectId']
    event_type = cloud_event.data["message"]["attributes"]['eventType']

    print("message eventType: ", event_type)
    print("message Object ID:", object_id) # raw/result.parquet
    print("message Bucket ID:", bucket_id)

    # print("cloud event",cloud_event)
    # print("cloud event type", type(cloud_event))
    # print("data keys: ",cloud_event.data.keys()) # ['message', 'subscription']
	# print("message keys", cloud_event.data["message"].keys()) 	# ['attributes', 'data', 'messageId', 'message_id', 'publishTime', 'publish_time']
    # print("message attributes:", cloud_event.data["message"]["attributes"]) 

    if event_type == "OBJECT_FINALIZE":
        file_location = "gs://" + bucket_id + "/" + object_id
        if object_id.endswith(".csv"):
            print("New/Overwrite detected")
            
            # notify_dataflow(file_location)
            try :
                load_csv_to_bq(file_location,object_id[:-4])
                print("Successfully loaded: ", file_location)

            except Exception as e:
                print("Failed to load ",file_location, " into BigQuery: {e}")

        elif object_id.endswith(".parquet"):
            if object_id == "raw/result.parquet":
                print("trigger flex dataflow for result.parquet ")
                print(launch_flex_dataflow())

            elif object_id == "test_transformation/output2/encoded/encoded.parquet":
                try :
                    load_parquet_to_bq(file_location,object_id[:-8])
                    print("Successfully loaded: ",file_location)
                except Exception as e:
                    print("Failed to load ",file_location," into BigQuery: {e}")



    print("here is the message end")