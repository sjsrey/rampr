from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Union
import pandas as pd


@dataclass(frozen=True)
class Crosswalk:
     """
    Container for crosswalk results.
    
    bridge_df : pd.DataFrame
        Bridge table mapping QCEW sectors to IO sectors with weights.
        Contains columns: area_fips, year, qcew_sector, io_sector, weight, 
        and optional io_label, qcew_label.
    io_agg_df : pd.DataFrame
        IO sector aggregated data with employment and wage statistics.
        Contains columns: io_sector, io_label, year, area_fips, 
        tap_estabs_count, tap_wages_est_3, tap_emplvl_est_3.
    """
     bridge_df: pd.DataFrame
     io_agg_df: pd.DataFrame


def _read_qcew_crosswalk_all_and_409(
    qcew_all_csv: Union[str, Path],
    qcew_409_csv: Union[str, Path],
    crosswalk_csv: Union[str, Path],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # read QCEW ALL dataset
    qcew_all = pd.read_csv(Path(qcew_all_csv))
    required_all = ["area_fips", "naics_code", "tap_estabs_count", "tap_wages_est_3", "tap_emplvl_est_3"]
    missing_all = set(required_all) - set(qcew_all.columns)
    if missing_all:
        raise ValueError(f"QCEW ALL missing columns: {sorted(missing_all)}")

    all_cols = required_all + (["year"] if "year" in qcew_all.columns else [])
    qcew_all_col = qcew_all.loc[:, all_cols].copy()

    # read QCEW 409 dataset
    qcew_409 = pd.read_csv(Path(qcew_409_csv))
    required_409 = ["area_fips", "sector_code", "tap_estabs_count", "tap_wages_est_3", "tap_emplvl_est_3"]
    missing_409 = set(required_409) - set(qcew_409.columns)
    if missing_409:
        raise ValueError(f"QCEW 409 missing columns: {sorted(missing_409)}")

    cols_409 = (
        required_409
        + (["year"] if "year" in qcew_409.columns else [])
        + (["sector_name"] if "sector_name" in qcew_409.columns else [])
    )
    qcew_409_col = qcew_409.loc[:, cols_409].copy()

    # read Crosswalk dataset
    xw = pd.read_csv(Path(crosswalk_csv))
    required_xw = ["qcew_sector", "io_sector"]
    missing_xw = set(required_xw) - set(xw.columns)
    if missing_xw:
        raise ValueError(f"Crosswalk missing columns: {sorted(missing_xw)}")

    keep = required_xw + [c for c in ["qcew_label", "io_label"] if c in xw.columns]
    xw_col = xw.loc[:, keep].copy()

    return qcew_all_col, qcew_409_col, xw_col



def build_crosswalk(
    qcew_all_csv: Union[str, Path],
    qcew_409_csv: Union[str, Path],
    crosswalk_csv: Union[str, Path],
    weight_on: Union[str, int, float] = "tap_wages_est_3"
) -> Crosswalk:
    """
    Build a crosswalk from QCEW NAICS sectors to BEA IO sectors with weights.
    Returns
    -------
    Crosswalk
        A dataclass containing:
        - bridge_df: Mapping table with weights for each NAICS-to-IO conversion
        - io_agg_df: Aggregated IO sector data with weighted statistics
     """
    
    df_qcew_all, df_qcew_409, df_crosswalk = _read_qcew_crosswalk_all_and_409(
        qcew_all_csv, qcew_409_csv, crosswalk_csv
    )

    #  crosswalk data cleaning

    key_cols = ["qcew_sector", "io_sector"]
    df_crosswalk = df_crosswalk.dropna(subset=key_cols).copy()
    df_crosswalk["qcew_sector"] = pd.to_numeric(df_crosswalk["qcew_sector"], errors="coerce").astype("Int64")
    df_crosswalk["io_sector"] = df_crosswalk["io_sector"].astype(str).str.strip()
    df_crosswalk = df_crosswalk.dropna(subset=key_cols).copy()

   # Preprocessing QCEW ALL dataset
    df_qcew_all = df_qcew_all.copy()
    df_qcew_all["area_fips"] = df_qcew_all["area_fips"].astype(str).str.zfill(5)
    if "year" not in df_qcew_all.columns:
        df_qcew_all["year"] = -1

    df_qcew_all["naics_code"] = pd.to_numeric(df_qcew_all["naics_code"], errors="coerce").astype("Int64")
    df_qcew_all = df_qcew_all.rename(columns={"naics_code": "qcew_sector"}).copy()

    value_cols = ["tap_wages_est_3", "tap_emplvl_est_3", "tap_estabs_count"]
    for c in value_cols:
        df_qcew_all[c] = pd.to_numeric(df_qcew_all[c], errors="coerce").fillna(0)

    # weight base using the tapestry wage estimations
    if isinstance(weight_on, str):
        if weight_on not in df_qcew_all.columns:
            raise ValueError(f"weight_on column not found in QCEW ALL: {weight_on!r}")
        df_qcew_all["_weight_base"] = pd.to_numeric(df_qcew_all[weight_on], errors="coerce").fillna(0)
    else:
        df_qcew_all["_weight_base"] = float(weight_on)

    # Merge ALL with crosswalk and compute weights
    merged = df_qcew_all.merge(df_crosswalk, on="qcew_sector", how="left")
    merged = merged.dropna(subset=["io_sector"]).copy()

    merged["io_total"] = merged.groupby(["area_fips", "year", "io_sector"])["_weight_base"].transform("sum")
    merged["weight"] = (merged["_weight_base"] / merged["io_total"]).fillna(0)

    # Bridge table
    bridge_cols = ["area_fips", "year", "qcew_sector", "io_sector"]
    if "io_label" in merged.columns:
        bridge_cols.append("io_label")
    if "qcew_label" in merged.columns:
        bridge_cols.append("qcew_label")

    bridge = merged.groupby(bridge_cols, as_index=False)["weight"].sum()
    bridge = bridge.drop_duplicates(subset=["area_fips", "year", "qcew_sector", "io_sector"], keep="first")

    # Aggregate ALL IO using weights
    qcew_for_apply = df_qcew_all[["area_fips", "year", "qcew_sector"] + value_cols].copy()

    applied = qcew_for_apply.merge(
        bridge[["area_fips", "year", "qcew_sector", "io_sector", "weight"] + (["io_label"] if "io_label" in bridge.columns else [])],
        on=["area_fips", "year", "qcew_sector"],
        how="left",
    ).dropna(subset=["io_sector"]).copy()

    for c in value_cols:
        applied[f"{c}_w"] = applied[c] * applied["weight"]

    agg_keys = ["area_fips", "year", "io_sector"]
    if "io_label" in applied.columns:
        agg_keys.append("io_label")

    io_agg_weighted = (
        applied.groupby(agg_keys, as_index=False)
        .agg(
            tap_wages_est_3=("tap_wages_est_3_w", "sum"),
            tap_emplvl_est_3=("tap_emplvl_est_3_w", "sum"),
            tap_estabs_count=("tap_estabs_count_w", "sum"),
        )
    )

    # force desired column order for weighted
    if "io_label" not in io_agg_weighted.columns:
        io_agg_weighted["io_label"] = pd.NA

    io_agg_weighted = io_agg_weighted[
        ["io_sector", "io_label", "year", "area_fips", "tap_estabs_count", "tap_wages_est_3", "tap_emplvl_est_3"]
    ].copy()

    # Fetch missing IO rows directly from QCEW_409
   
    df_409 = df_qcew_409.copy()
    df_409["area_fips"] = df_409["area_fips"].astype(str).str.zfill(5)
    if "year" not in df_409.columns:
        df_409["year"] = -1

    # build desired io fields straight from 409
    df_409_out = pd.DataFrame(
        {
            "io_sector": df_409["sector_code"].astype(str).str.strip(),
            "io_label": df_409["sector_name"] if "sector_name" in df_409.columns else pd.NA,
            "year": df_409["year"],
            "area_fips": df_409["area_fips"],
            "tap_estabs_count": pd.to_numeric(df_409["tap_estabs_count"], errors="coerce").fillna(0),
            "tap_wages_est_3": pd.to_numeric(df_409["tap_wages_est_3"], errors="coerce").fillna(0),
            "tap_emplvl_est_3": pd.to_numeric(df_409["tap_emplvl_est_3"], errors="coerce").fillna(0),
        }
    )

    # Ensure types cleaning
    df_409_out["io_sector"] = df_409_out["io_sector"].astype(str).str.strip()
    df_409_out["area_fips"] = df_409_out["area_fips"].astype(str).str.zfill(5)

    # find missing keys in weighted agg
    key_cols = ["area_fips", "year", "io_sector"]
    keys_weighted = io_agg_weighted[key_cols].drop_duplicates()
    keys_409 = df_409_out[key_cols].drop_duplicates()

    missing_keys = keys_409.merge(keys_weighted, on=key_cols, how="left", indicator=True)
    missing_keys = missing_keys[missing_keys["_merge"] == "left_only"].drop(columns=["_merge"])

    # only append missing rows from 409
    fill_rows = df_409_out.merge(missing_keys, on=key_cols, how="inner").copy()

    # final io_agg_df
    io_agg = pd.concat([io_agg_weighted, fill_rows], ignore_index=True)
    io_agg = io_agg.drop_duplicates(subset=key_cols, keep="first")

    # final ordering (exactly what you requested)
    io_agg = io_agg[
        ["io_sector", "io_label", "year", "area_fips", "tap_estabs_count", "tap_wages_est_3", "tap_emplvl_est_3"]
    ].copy()

    return Crosswalk(bridge_df=bridge, io_agg_df=io_agg)




def load_402_sector_codes(sector_file: Union[str, Path,pd.DataFrame]) -> list[str]:
    """
    Load the BEA 402 IO sector codes from a text file.

    Parameters
    ----------
    sector_file:
        Path to the text file containing sector codes.

    Returns
    -------
    list[str]
        Unique sector codes in the order they appear in the file.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If no valid codes are found after parsing.
    """
    path = Path(sector_file).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Sector code file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Sector code path is not a file: {path}")

    raw_lines = path.read_text(encoding="utf-8").splitlines()

    codes: list[str] = []
    for i, line in enumerate(raw_lines, start=1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        s = "".join(s.split())
        codes.append(s)

    # de-duplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for c in codes:
        if c not in seen:
            unique.append(c)
            seen.add(c)

    if not unique:
        raise ValueError(f"No sector codes found in file: {path}")

    return unique




def align_io_to_bea_402(
    io_agg_df: pd.DataFrame,
    codes_file: Union[str, Path],
    *,
    keep_all_codes: bool = False,
) -> pd.DataFrame:
    """
    Align io_agg_df to the BEA 402 IO sector code universe defined in codes_file.

    Key behavior:
      - Drops rows whose io_sector is not in the codes_file (always).
      - Preserves the exact order of codes_file in the output.
      - If keep_all_codes=True:
          For each (area_fips, year) present, ensures ALL codes appear
          (missing rows are added and filled with zeros for numeric columns).

    Output ordering:
      - Primary: area_fips (if present), then year (if present)
      - Secondary: io_sector in the exact order in codes_file
    """
    if "io_sector" not in io_agg_df.columns:
        raise ValueError("io_agg_df missing required column: 'io_sector'")

    codes = load_402_sector_codes(codes_file)  # preserves file order
    if not codes:
        raise ValueError(f"No codes found in {codes_file}")

    codes_set = set(codes)

    df = io_agg_df.copy()
    df["io_sector"] = df["io_sector"].astype(str).str.strip()

    #Keep only allowed codes discard anything else
    aligned = df[df["io_sector"].isin(codes_set)].copy()

    #Force io_sector to be an ordered categorical 
    aligned["io_sector"] = pd.Categorical(
        aligned["io_sector"], categories=codes, ordered=True
    )

    numeric_cols = ["tap_estabs_count", "tap_wages_est_3", "tap_emplvl_est_3"]

    #  just sought all io_sector codes
    if not keep_all_codes:
        sort_cols = [c for c in ["area_fips", "year"] if c in aligned.columns] + ["io_sector"]
        aligned = aligned.sort_values(sort_cols, kind="stable").reset_index(drop=True)
        return aligned

    #  ensure every area_fips, year have unique 402 codes
    key_cols = [c for c in ["area_fips", "year"] if c in aligned.columns]
    if not key_cols:
        present = set(aligned["io_sector"].astype(str))
        missing_codes = [c for c in codes if c not in present]
        if missing_codes:
            pad = pd.DataFrame({"io_sector": missing_codes})
            for col in aligned.columns:
                if col not in pad.columns:
                    if col in numeric_cols:
                        pad[col] = 0
                    else:
                        pad[col] = pd.NA
            aligned = pd.concat([aligned, pad[aligned.columns]], ignore_index=True)

        aligned["io_sector"] = pd.Categorical(aligned["io_sector"], categories=codes, ordered=True)
        aligned = aligned.sort_values(["io_sector"], kind="stable").reset_index(drop=True)
        return aligned

    # Build full unique (area_fips, year) x codes 
    combos = aligned[key_cols].drop_duplicates().copy()
    all_codes = pd.DataFrame({"io_sector": pd.Categorical(codes, categories=codes, ordered=True)})

    full = combos.merge(all_codes, how="cross")

    # Merge existing onto full grid
    out = full.merge(aligned, on=key_cols + ["io_sector"], how="left")

    # Keep io_sector categorical ,ordered and sorted
    out["io_sector"] = pd.Categorical(out["io_sector"], categories=codes, ordered=True)
    out = out.sort_values(key_cols + ["io_sector"], kind="stable").reset_index(drop=True)

    return out