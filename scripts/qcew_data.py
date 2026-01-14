import rampr.datasets as ds

# List what rampr knows about
print(ds.list_datasets())

# Download and unpack the dataset
paths = ds.fetch("qcew_2024_bea409_allcounties", version="v1")
print(paths[:10])

# Get cache directory
cache_dir = ds.path("qcew_2024_bea409_allcounties", version="v1")
print(cache_dir)

# Get metadata / license / DOI
print(ds.info("qcew_2024_bea409_allcounties", version="v1")["record_doi"])
