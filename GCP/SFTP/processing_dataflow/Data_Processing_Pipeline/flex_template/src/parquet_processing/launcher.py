"""Defines command line arguments for the pipeline defined in the package."""

# launcher.py

import argparse
import apache_beam as beam   # only if you need to pull in PipelineOptions
from apache_beam.options.pipeline_options import PipelineOptions

from .pipeline import run_pipeline

def run(argv=None):
    parser = argparse.ArgumentParser(
        description="Launch the Parquet→FCS→GCS Dataflow pipeline"
    )

    parser.add_argument(
        "--project",
        default="omar-ismail-test-project",
        help="GCP Project ID"
    )
    parser.add_argument( # gs://new_remove/test_transformation/result.parquet
        "--schema_directory",
        required=True,
        help="Location of the original Parquet schema"
    )
    parser.add_argument( # gs://new_remove/test_transformation/result.parquet
        "--target_file_location",
        required=True,
        help="Target file location in the FCS system"
    )
    parser.add_argument( # gs://new_remove/test_transformation/output2/encoded
        "--result_file_location",
        required=True,
        help="Output file location in GCS"
    )
    parser.add_argument(
        "--pipeline_temp_location",
        default="new_remove",
        help="This is the pipeline temp files location"
    )
    parser.add_argument(
        "--codec",
        default="snappy",
        help="Encoding codec to use (e.g. snappy, gzip)"
    )

    # Split out any Beam‐specific flags (e.g. --runner, --temp_location, etc.)
    known_args, pipeline_args = parser.parse_known_args(argv)

    # Hand off into your pipeline code
    return run_pipeline(
        project=known_args.project,
        schema_directory=known_args.schema_directory,
        target_file_location=known_args.target_file_location,
        result_file_location=known_args.result_file_location,
        pipeline_temp_location=known_args.pipeline_temp_location,
        codec=known_args.codec,
        extra_pipeline_args=pipeline_args,
    )


