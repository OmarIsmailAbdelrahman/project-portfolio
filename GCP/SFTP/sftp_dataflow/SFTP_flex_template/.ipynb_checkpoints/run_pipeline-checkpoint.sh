#!/bin/bash
cd /app
python pipeline.py \
  --project="omar-ismail-test-project" \
  --secret_name="sftp_default_key" \
  --rclone_remote="myvm" \
  --remote_dir="customer_test_data" \
  --host="34.122.235.37" \
  --user="omar_ismail" \
  --port=22 \
  --bucket_name="new_remove" \
  --prefix="raw"
