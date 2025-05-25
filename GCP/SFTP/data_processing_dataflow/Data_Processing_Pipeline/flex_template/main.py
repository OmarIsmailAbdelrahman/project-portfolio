import logging

from src.parquet_processing import launcher # this is the package containing the pipeline

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    launcher.run()