# GCP/SFTP

![Project Workflow](images/architecture.png)


## Solution Overview

A VM watches an SFTP endpoint, pushes new files into a GCS bucket, and emits a Pub/Sub event. A Cloud Function filters for finalized objects and writes CSV rows into BigQuery, then republishes a message. Two Dataflow pipelines (one for ingest, one for processing) run as Flex templates, and an Airflow DAG can kick them off on demand or schedule.

### SFTP Ingestion Pipeline

I provisioned a VM with an SSH key pair and opened port 22 (`ufw allow 22`). A startup script uses `inotifywait` to detect incoming files and copy them into GCS. IAM scopes were updated so the VM can write to the bucket. Host-key mismatches were handled via `ssh-keygen -R`. A bucket-notification Pub/Sub topic triggers a Cloud Function that looks for `OBJECT_FINALIZE`, then loads CSVs into BigQuery (logs visible under Debug).

### Dataflow Pipelines & Pub/Sub Chaining

An initial notebook prototype validated ~300–400 events/sec on an e2-small. I discovered that native bucket triggers lack full metadata, so the Cloud Function republishes to a second Pub/Sub topic that feeds Dataflow. CORS settings were tightened in the function, and I relocated Apache Beam imports to global scope to avoid scoping bugs. Load-balanced delivery to a single subscriber explained the apparent race conditions.

### Flex Templates & Custom Container

To eliminate the VM, I evaluated RClone for direct-to-GCS sync and built a custom Docker image bundling RClone into the Beam worker. Matching the SDK harness version (Beam 2.53.0 on Python 3.10) resolved infinite-retry errors. Workers mount a disk for staging, and both pipelines are now packaged as Flex templates for simple `gcloud dataflow flex-template run` deployment.

### Performance Tuning

SSHD limits (`MaxStartups`, `MaxSessions`) and encryption overhead were tuned to sustain multi-MiB/s throughput. Parallel SFTP connections increased rates from ~7 MiB/s to over 200 MiB/s on an e2-medium VM. I monitored with `iftop`, fixed a “no space to write” staging error, and manually adjusted Dataflow autoscaling to avoid cold-start delays and worker-fusion stalls.

### Parquet Processing Pipeline

A downstream pipeline reads Parquet files, applies column-level encoding, and writes back with compression. I addressed a codec mismatch that ballooned file sizes (3 MB → 82 MB) by re-applying the original codec, restoring ~2 MB outputs. Side inputs were refactored to remove bottlenecks, and fusion behavior in Dataflow was confirmed.

### Airflow Orchestration

A local Airflow instance runs a DAG that launches both Flex templates. I leverage the built-in SFTP operator for future file pulls and Dataflow operators for each pipeline, using a service account with Dataflow Admin, Storage Viewer, and Service Account User roles.

## Next Steps

- Introduce automated monitoring & alerts (Cloud Monitoring) for pipeline health  
- Add end-to-end integration tests with ephemeral buckets  
- Expose pipeline parameters (windowing, worker count) for different workloads  
- Extend the DAG with data-quality checks and downstream reporting  
- Evaluate managed transfer services (e.g. Cloud Transfer) as an alternative to SFTP/RClone  
