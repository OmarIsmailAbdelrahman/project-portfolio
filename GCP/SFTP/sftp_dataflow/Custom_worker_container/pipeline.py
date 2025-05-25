import os
import subprocess
import csv
import tempfile

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions



class RcloneMixin:
    def _prepare_rclone(self):
        import tempfile
      # PROJECT, SECRET, REMOTE, BUCKET configuration
        PROJECT       = 'omar-ismail-test-project'
        SECRET_NAME   = 'sftp_default_key'
        RCLONE_REMOTE = 'myvm' # you must setup the rclone for it to work
        REMOTE_DIR    = 'customer_test_data'

        HOST          = '34.69.92.10'
        USER          = 'omar_ismail'
        PORT          = 22
        GCS_BUCKET    = 'new_remove'
        from google.cloud import secretmanager
        # 1) Fetch key from Secret Manager
        client = secretmanager.SecretManagerServiceClient()
        name   = f"projects/{PROJECT}/secrets/{SECRET_NAME}/versions/latest"
        key_str = client.access_secret_version(request={"name": name}) \
                        .payload.data.decode('utf-8')

        # 2) Write key to secure temp file
        self.key_path = os.path.join(tempfile.gettempdir(), 'sftp_key')
        print(f"key location: {self.key_path}")
        with open(self.key_path, 'w') as f:
            f.write(key_str)
        os.chmod(self.key_path, 0o600)

        # 3) Write a minimal rclone.conf
        self.conf_path = os.path.join(tempfile.gettempdir(), 'rclone.conf')
        conf = f"""
[{RCLONE_REMOTE}]
type = sftp
host = {HOST}
user = {USER}
port = {PORT}
key_file = {self.key_path}
"""
        with open(self.conf_path, 'w') as f:
            f.write(conf.strip() + "\n")
        print("rclone configuration directory", self.conf_path)

class ListFiles(RcloneMixin, beam.DoFn):
    def setup(self):
        self._prepare_rclone()
    def process(self, _):
        import subprocess
        RCLONE_REMOTE = 'myvm' # you must setup the rclone for it to work
        REMOTE_DIR    = 'customer_test_data'
        print("fetch list of files")
        out = subprocess.check_output([
            'rclone', '--config', self.conf_path,
            'lsf', f"{RCLONE_REMOTE}:{REMOTE_DIR}"
        ]).decode('utf-8').splitlines()
        print("finish fetching", out)

        for fname in out:
            if fname.endswith('.csv'):
                print(f"Found csv: {fname}")
                yield fname
            if fname.endswith('.parquet'):
                print(f"Found parquet: {fname}")
                yield fname
            


class FetchWithRclone(RcloneMixin, beam.DoFn):
    def setup(self):
        import tempfile, socket, logging

        self._prepare_rclone()
        self.tmpdir = tempfile.mkdtemp()
        
        # per-worker logger → writes to <tmpdir>/<hostname>.log
        self.worker_id = socket.gethostname()
        self.logfile = os.path.join(self.tmpdir, f"{self.worker_id}.log")
        handler = logging.FileHandler(self.logfile)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger = logging.getLogger(self.worker_id)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(handler)

    def process(self, filename):
        import subprocess
        RCLONE_REMOTE = 'myvm' # you must setup the rclone for it to work
        REMOTE_DIR    = 'customer_test_data'
        local_path = os.path.join(self.tmpdir, filename)
        print(f"the new tmp file in {local_path}")
        print(f"copying from {RCLONE_REMOTE}:{REMOTE_DIR}/{filename}")
        subprocess.run([
            'rclone', '--config', self.conf_path,
            'copyto',
            f"{RCLONE_REMOTE}:{REMOTE_DIR}/{filename}",
            local_path
        ], check=True)
        self.logger.info(filename)
        print(f"finished copying {local_path}")
        yield local_path
    def teardown(self):
            # at worker shutdown you can inspect self.logfile
            # or (if bucket_name given) upload it to GCS:
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket("remove_later123")
        blob = bucket.blob(f"dataflow_testing/{os.path.basename(self.logfile)}")
        blob.upload_from_filename(self.logfile)


# class CopyToGCS(beam.DoFn):
#     def __init__(self, target_uri):
#         self.target_uri = target_uri
#     def process(self, local_path):

#         from apache_beam.io.filesystems import FileSystems
#         print(f"moving file {local_path} to {self.target_uri}{local_path.split('/')[-1]}")
#         FileSystems.copy([local_path], [self.target_uri+local_path.split('/')[-1]])
#         yield local_path


class UploadToGCS(beam.DoFn):
    def __init__(self, bucket_name, prefix=""):
        self.bucket_name = bucket_name
        self.prefix = prefix.strip("/")

    def setup(self):
        from google.cloud import storage
        self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)

    def process(self, local_path):
        import os
        filename = os.path.basename(local_path)
        if self.prefix:
            blob_path = f"{self.prefix}/{filename}"
        else:
            blob_path = filename

        blob = self.bucket.blob(blob_path)
        blob.upload_from_filename(local_path)

        os.remove(local_path)
        gcs_uri = f"gs://{self.bucket_name}/{blob_path}"
        print(f"moved file {local_path} to {gcs_uri}")
        yield gcs_uri



# def parse_csv(local_path):
#     import csv
#     with open(local_path, newline='') as f:
#         for row in csv.DictReader(f):
#             yield row


def run():
    project_id = 'omar-ismail-test-project'
    options = PipelineOptions(
        # streaming=True,
        project=project_id,
        region='us-central1',
        temp_location='gs://remove_later123/temp',
        # service_account_email='dataflow-worker@omar-ismail-test-project.iam.gserviceaccount.com'
    )

    with beam.Pipeline(options=options) as p:
        files = (
            p
            | 'Init'      >> beam.Create([None])
            | 'ListFiles' >> beam.ParDo(ListFiles())
            | 'Reshuffle' >> beam.Reshuffle()

        )

        fetched = files | 'FetchOne' >> beam.ParDo(FetchWithRclone())

        _ = fetched | 'SaveRaw' >> beam.ParDo(
            UploadToGCS(bucket_name="new_remove", prefix="raw"))
            # note: you can parameterize per-filename if needed

        # _ = fetched | 'ParseCSV' >> beam.FlatMap(parse_csv) 


if __name__ == '__main__':
    run()
