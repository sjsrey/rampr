from rampr.bridge import build_crosswalk, align_io_to_bea_402
from rampr.bridge import qcew_to_io_crosswalk_path, bea_402_sector_codes_path, qcew_all_csv_path,crosswalk_dir
from rampr.bridge import impute_missing_sectors
from rampr.datasets import fetch
import pandas as pd

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
 
print("\nBuilding crosswalk...")
cw = build_crosswalk(
    qcew_all_csv,
    qcew_409_csv,
    qcew_to_io_crosswalk_path()
)



# Align to BEA 402 to make sure any area code will have 402 sectors to match io with imputation

print("\nAligning to BEA 402 and imputing missing values together...")
df_bridge = align_io_to_bea_402(io_agg_df=cw.io_agg_df, codes_file=bea_402_sector_codes_path())
df_missing_sectors = crosswalk_dir()/'missing_sectors.csv'
df_imputation = impute_missing_sectors(df_bridge, df_missing_sectors)
df_final_bridge = align_io_to_bea_402(df_imputation, codes_file=bea_402_sector_codes_path())

# checking shape to see they match 402 by filtering with the area_fips
print("\n san diego")
san_diego = '06073'
print(f"{df_final_bridge[df_final_bridge['area_fips'] == san_diego].shape}")
# Save the final bridge with imputation
#df_final_bridge.to_csv('bridge.csv', index=False)