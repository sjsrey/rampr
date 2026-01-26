from __future__ import annotations
import pytest
from rampr.bridge.io_bridge import build_crosswalk, align_io_to_bea_402
from rampr.bridge.path import bea_402_sector_codes_path, qcew_to_io_crosswalk_path, qcew_all_csv_path
from rampr.datasets import fetch


@pytest.mark.integration
def test_build_crosswalk_with_real_data():
    """Integration test using actual QCEW data."""
    # Fetch QCEW 409 data from Zenodo
    print("\nFetching QCEW 409 data...")
    qcew_409_files = fetch(
        "qcew_2024_bea409_allcounties",
        version="v1"
    )
    qcew_409_csv = qcew_409_files[0]
    
    # Get QCEW All data from local archive
    qcew_all_csv = qcew_all_csv_path()
    
    # Build crosswalk
    print("\nBuilding crosswalk...")
    cw = build_crosswalk(
        qcew_all_csv,
        qcew_409_csv,
        qcew_to_io_crosswalk_path()
    )
    
    # Verify bridge properties
    assert cw.bridge_df is not None
    assert (cw.bridge_df["weight"] >= 0).all()
    assert (cw.bridge_df["weight"] <= 1).all()
    
    # Verify weights sum to 1 per group 
    sums = cw.bridge_df.groupby(["area_fips", "year", "io_sector"])["weight"].sum()
    
    # Only check groups that have non-zero weights because some sectors report zero meaning no sector in those areas
    non_zero_sums = sums[sums > 0]
    assert (non_zero_sums.round(3) == 1.0).all(), f"Found weights not summing to 1: {non_zero_sums[non_zero_sums.round(6) != 1.0]}"

    # Verify IO aggregation is not null or NA
    assert cw.io_agg_df is not None
    
    df_bridge_output = align_io_to_bea_402(
        io_agg_df=cw.io_agg_df,
        codes_file=bea_402_sector_codes_path()
    )
    
    # Verify alignment does not exceed detail io sectors which is  less than 402
    assert df_bridge_output["io_sector"].nunique() <= 402
    