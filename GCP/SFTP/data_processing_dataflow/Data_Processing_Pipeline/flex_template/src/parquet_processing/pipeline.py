import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.io.parquetio import ReadFromParquet, WriteToParquet
import typing
import pyarrow as pa
from apache_beam.io.filesystems import FileSystems
import pyarrow.parquet as pq
from apache_beam.transforms.combiners import Sample
import json 

# 1. Extract column-value pairs
def extract_object_column_values(record: dict): # this is 
    for col, val in record.items():
        if isinstance(val, str):  # Candidate for label encoding
            yield (col, val)


# 2. Create label mapping
def create_label_mapping(kv: typing.Tuple[str, typing.Iterable[str]]):
    col, values = kv
    unique_vals = set(values)
    if len(unique_vals) <= 15:
        mapping = {v: i for i, v in enumerate(sorted(unique_vals))}
        return (col, mapping)
    return None  # skip this column

class Convert(beam.DoFn):
    def process(self,record):
        new_mappings = {}
        for k,v in record.items():
            print(k,v)
            new_mappings[k] = v
        return [new_mappings]

# 3. Encode
class FilterUsingLength(beam.DoFn):
    def process(self,record: dict, mappings: list):                
        new_record = record.copy()
        for col, mapping in mappings[0].items():
            val = new_record.get(col)
            if val in mapping:
                new_record[col] = mapping[val]
            elif val is not None:
                new_record[col] = -1  # Unknown
        yield new_record

def infer_schema(parquet_path: str):
    with FileSystems.open(parquet_path) as f:
        return pq.ParquetFile(f).schema_arrow


def run_pipeline(
    project: str,
    schema_directory: str,
    target_file_location: str,
    result_file_location: str,
    codec: str,
    pipeline_temp_location:str,
    extra_pipeline_args: list[str],
):
    # build your PipelineOptions from extra flags + project
    options = PipelineOptions(
        extra_pipeline_args,
        project=project,
        region='us-central1',
        temp_location=f'gs://{pipeline_temp_location}/temp',
    )

    # because no schema is provided for the parquet file
    orig = pq.ParquetFile(FileSystems.open(schema_directory)).schema_arrow

    mapped_cols = [
        'po_priority_common_key',
        'po_to_department_key',
        'po_department_key',
        'po_mode_common_key',
        'po_type_common_key',
        'po_comm_common_key',
        'po_user_department_key',
        'po_encounter_type_common_key',
        'po_prescription_status_common_key',
        'duration_uom_common_key',
        'status_common_key',
        'result_status_common_key',
        'priority_common_key',
        'status_flag',
        'result_type',
        'HLN',
    ]

    schema = pa.schema(
        # first, your newly-int64 columns:
        [pa.field(c, pa.int64()) for c in mapped_cols] +
        # then all the other fields untouched:
        [f for f in orig if f.name not in mapped_cols]
    )

    with beam.Pipeline(options=options) as p:
        # Read data from your input path
        records = p | 'Read Parquet' >> ReadFromParquet(target_file_location)

        column_values = (
            records
            | 'Extract Col-Value'
            >> beam.FlatMap(extract_object_column_values)
        )

        grouped = column_values | 'Group by Column' >> beam.GroupByKey()

        raw_mappings = grouped | 'Create Mappings' >> beam.Map(create_label_mapping)
        label_mappings = raw_mappings | 'Drop Nones' >> beam.Filter(lambda x: x is not None)

        mappings_dict = label_mappings | 'To Dict' >> beam.combiners.ToDict()
        mappings_list = mappings_dict | 'test1' >> beam.ParDo(Convert())

        encoded = records | 'Encode Records' >> beam.ParDo(
            FilterUsingLength(),
            beam.pvalue.AsList(mappings_list)
        )

        encoded | 'Write Compressed Parquet' >> WriteToParquet(
            file_path_prefix=result_file_location.rstrip('/') + '/encoded',
            schema=schema,
            codec=codec,
            num_shards=1,
            shard_name_template='',
            file_name_suffix='.parquet'
        )

