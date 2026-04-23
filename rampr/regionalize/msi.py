from __future__ import annotations
import pandas as pd, numpy as np


def kjc_imputation(df_kjc: pd.DataFrame, *, geo_col: str, regional_col: str, national_col: str) -> pd.DataFrame:
    """
    Impute missing regional values via a geo-level national scaling factor.
    Falls back to a global scale if a geography has no observed data.
    """
    df = df_kjc.copy()

    miss = df[regional_col].isna()

    sums = (df.loc[~miss].groupby(geo_col, sort=False)[[regional_col, national_col]].sum())

    scale = sums[regional_col] / sums[national_col]

    df["_scale"] = df[geo_col].map(scale)

    df.loc[miss, regional_col] = (df.loc[miss, national_col] * df.loc[miss, "_scale"])

    scale = (df.loc[~miss, regional_col].sum() / df.loc[~miss, national_col].sum()
             if (~miss).any() else 0.0)
    df[regional_col] = df[regional_col].fillna(df[national_col] * scale)

    return df.drop(columns=["_scale"])


def emp_imputation(
    df_kjc: pd.DataFrame,
    emp_df: pd.DataFrame,
    *,
    regional_col: str,
    national_col: str,
    emp_col: str,
    emp_sector_col: str,
    kjc_sector_col: str,
    geo_col: str,
) -> pd.DataFrame:
    """
    Impute missing employment for sectors absent across all geographies.

    Applies ``kjc_imputation`` first, then estimates missing employment
    using a regional employment-to-output ratio (theta_r = Er/Xr)
    derived from sectors with known data.
    """
    # imputing the Kjc for the 5 missing sectors
    df  = kjc_imputation(df_kjc, geo_col=geo_col, regional_col=regional_col, national_col=national_col)
    df1 = emp_df.copy()

    # normalise geo_col dtype in both DataFrames before any merge
    df[geo_col]  = df[geo_col].astype(str).str.zfill(5)
    df1[geo_col] = df1[geo_col].astype(str).str.zfill(5)

    # Rename sector columns to a common key
    out = df.rename(columns={kjc_sector_col: "io_sector"})
    emp = df1.rename(columns={emp_sector_col: "io_sector"})
    emp = emp[[geo_col, "io_sector", emp_col]]

    # Merge outputs + employment
    m = out.merge(emp, on=[geo_col, "io_sector"], how="left")

    # Pivot for NumPy matrices
    Xr_w = (
        m.pivot(index=geo_col, columns="io_sector", values=regional_col)
        .sort_index()
        .sort_index(axis=1)
    )
    Er_w = (
        m.pivot(index=geo_col, columns="io_sector", values=emp_col)
        .reindex(index=Xr_w.index, columns=Xr_w.columns)
    )
    Xr, Er = Xr_w.to_numpy(), Er_w.to_numpy()

    # Find sectors missing employment for ALL regions
    miss_cols = np.where(np.isnan(Er).all(axis=0))[0]

    # Compute (emp/output ratio) from known sectors
    known   = ~np.isnan(Er)
    Er_sum  = np.sum(np.where(known, Er, 0.0), axis=1)
    Xr_sum  = np.sum(np.where(known, Xr, 0.0), axis=1)
    theta_r = np.divide(Er_sum, Xr_sum, out=np.zeros_like(Er_sum), where=(Xr_sum != 0))

    # Fill missing sectors for every region
    Er_filled = Er.copy()
    Er_filled[:, miss_cols] = theta_r[:, None] * Xr[:, miss_cols]
    Er_filled[:, miss_cols] = np.maximum(Er_filled[:, miss_cols], 0)

    # Return table of filled employment
    fips = Xr_w.index.to_numpy()
    sec5 = Xr_w.columns[miss_cols].to_numpy()
    vals = Er_filled[:, miss_cols]

    df_filled = pd.DataFrame({
        geo_col:      np.repeat(fips, len(sec5)),
        "io_sector":  np.tile(sec5, len(fips)),
        "emp_filled": vals.reshape(-1),
    })

    df_filled = df_filled.rename(columns={"io_sector": emp_sector_col})

    emp_df_output = df1.merge(df_filled, on=[geo_col, emp_sector_col], how="left")
    emp_df_output[emp_col] = emp_df_output[emp_col].fillna(emp_df_output["emp_filled"])
    emp_df_output = emp_df_output.drop(columns=["emp_filled"])

    return emp_df_output