from rampr.bridge.io_bridge import build_crosswalk, align_io_to_bea_402
from rampr.bridge.path import qcew_to_io_crosswalk_path, bea_402_sector_codes_path, qcew_all_csv_path
from rampr.datasets import fetch

# Fetch QCEW 409 data from zenodo
print("n\Fetching QCEW 409 data...")
qcew_409_files = fetch(
    "qcew_2024_bea409_allcounties",
    version="v1"
)
qcew_409_csv = qcew_409_files[0]

# Get QCEW_All_0_All CSV data from local archive directory ,
# this data was not on zenodo
qcew_all_csv = qcew_all_csv_path()

# Build crosswalk 
print("\nBuilding crosswalk...")
cw = build_crosswalk(
    qcew_all_csv,
    qcew_409_csv,
    qcew_to_io_crosswalk_path()
)


print(f"Bridge shape: {cw.bridge_df.shape}")
print(f"IO aggregated shape: {cw.io_agg_df.shape}")

# Align to BEA 402 to make sure any area code will have 402 sectors to match io
# this output gives the actual bridge output
print("\nAligning to BEA 402...")
df_bridge_output = align_io_to_bea_402(io_agg_df=cw.io_agg_df, codes_file=bea_402_sector_codes_path())

# save
#df_bridge_output.to_csv('bridge_crosswalk.csv', index = False)

# This give non unique numbers of 397 
print(f"\nDone! Aligned {len(df_bridge_output)} rows with {df_bridge_output['io_sector'].nunique()} unique IO sectors")
print(f"\nFirst few rows:")
print(df_bridge_output.head())
