"""Defines command line arguments for the pipeline defined in the package."""

# launcher.py

import argparse
import apache_beam as beam   # only if you need to pull in PipelineOptions
from apache_beam.options.pipeline_options import PipelineOptions

from .pipeline import run_pipeline

def run(argv=None):
    parser = argparse.ArgumentParser(description="Launch SFTP→GCS Dataflow job")

    parser.add_argument("--project",
                        default="omar-ismail-test-project",
                        help="GCP Project ID")
    parser.add_argument("--secret_name",
                        default="sftp_default_key",
                        help="Secret Manager secret name for SFTP key")
    parser.add_argument("--rclone_remote",
                        default="myvm",
                        help="Rclone remote name")
    parser.add_argument("--remote_dir",
                        default="customer_test_data",
                        help="Remote directory path")
    parser.add_argument("--host",
                        required=True,
                        help="SFTP host IP or domain")
    parser.add_argument("--user",
                        required=True,
                        help="SFTP username")
    parser.add_argument("--port",
                        type=int,
                        default=22,
                        help="SFTP port")
    parser.add_argument("--bucket_name",
                        default="new_remove",
                        help="Output GCS bucket")
    parser.add_argument("--prefix",
                        default="raw",
                        help="Prefix for output files")

    # This will pull out anything Beam-specific (e.g. --runner, --worker_machine_type, etc.)
    # into pipeline_args, leaving the rest in known_args.
    known_args, pipeline_args = parser.parse_known_args(argv)

    # Now hand off to your pipeline
    return run_pipeline(
        project=known_args.project,
        secret_name=known_args.secret_name,
        rclone_remote=known_args.rclone_remote,
        remote_dir=known_args.remote_dir,
        host=known_args.host,
        user=known_args.user,
        port=known_args.port,
        bucket_name=known_args.bucket_name,
        prefix=known_args.prefix,
        extra_pipeline_args=pipeline_args,
    )
