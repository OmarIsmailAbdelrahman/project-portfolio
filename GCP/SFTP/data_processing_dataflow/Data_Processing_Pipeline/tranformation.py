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

input_path = 'gs://new_remove/test_transformation/result.parquet'
orig = pq.ParquetFile(FileSystems.open(input_path)).schema_arrow

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

def run():
    options = PipelineOptions()
    with beam.Pipeline(options=options) as p:
        # Read data
        records = p | 'Read Parquet' >> ReadFromParquet('gs://new_remove/test_transformation/result.parquet')

        column_values = records | 'Extract Col-Value' >> beam.FlatMap(extract_object_column_values) # for each record check the value type, then send them as pair to match, ex: "(ID,3)"
        
        grouped = column_values | 'Group by Column' >> beam.GroupByKey() # group the values under column name, ex: ID:[3,5,1,6]
        
        # Create mappings for low-cardinality columns
        raw_mappings = grouped | 'Create Mappings' >> beam.Map(create_label_mapping) # this takes the a single tuple that contain the key "column", and iteratable for all values in it, it takes a single column at a time because it's a map function
        label_mappings = raw_mappings | 'Drop Nones' >> beam.Filter(lambda x: x is not None) ## this filter out the columns with no mapping 
        # label_mappings | "print_label" >> beam.Map(print)
        
        # Convert mapping to dict for side input
        mappings_dict = label_mappings | 'To Dict' >> beam.combiners.ToDict() # Convert all the 
        # mappings_dict | 'print' >> beam.Map(print)
        
        mappings_dict2 = mappings_dict | 'test1' >> beam.ParDo(Convert()) 
        # mappings_dict2 | "test2" >> beam.Map(print)
        
        encoded = records | 'Encode Records' >> beam.ParDo(FilterUsingLength(),beam.pvalue.AsList(mappings_dict2))

        encoded | 'Write Compressed Parquet' >> WriteToParquet(
            file_path_prefix='gs://new_remove/test_transformation/output2/encoded',
            schema=schema,            # use the pre-computed schema
            codec='snappy',
            num_shards=1,
            shard_name_template='',
            file_name_suffix='.parquet'
        )
        # encoded | beam.io.WriteToText(
        #           'poc_samples/Data/encoded_sample',
        #           file_name_suffix='.json',
        #           shard_name_template=''
        # )


if __name__ == '__main__':
    run()
