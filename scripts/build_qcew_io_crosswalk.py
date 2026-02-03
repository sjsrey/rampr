from rampr.bridge import build_crosswalk, align_io_to_bea_402, data_path, impute_missing_sectors
from rampr.datasets import fetch

# Fetch QCEW 409 data from zenodo
print("\nFetching QCEW 409 data...")
qcew_409_files = fetch("qcew_2024_bea409_allcounties", version="v1")
qcew_409_csv = qcew_409_files[0]

# Local QCEW_All_0_All CSV (not on zenodo)
qcew_all_csv = data_path("qcew_all_csv")

print("\nBuilding crosswalk...")
cw = build_crosswalk(
    qcew_all_csv,
    qcew_409_csv,
    data_path("qcew_to_io_crosswalk", version="v1"),
)

print("\nAligning to BEA 402 and imputing missing values together...")
bea_codes = data_path("bea_402_sector_codes")          # default filename
missing_sectors_csv = data_path("crosswalk_dir") / "missing_sectors.csv"  # if you didn't add a key

df_bridge = align_io_to_bea_402(io_agg_df=cw.io_agg_df, codes_file=bea_codes)
df_imputation = impute_missing_sectors(df_bridge, missing_sectors_csv)
df_final_bridge = align_io_to_bea_402(df_imputation, codes_file=bea_codes)

# checking shape to see they match 402 by filtering with the area_fips
print("\nSan Diego")
san_diego = "06073"
print(df_final_bridge[df_final_bridge["area_fips"] == san_diego].shape)

# Save the final bridge with imputation
output_path = data_path("repo_root") / "bridge.csv"
df_final_bridge.to_csv(output_path, index=False)

