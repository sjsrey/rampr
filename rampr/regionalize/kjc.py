from __future__ import annotations
import pandas as pd, numpy as np


def kjc_share(
    make_output: pd.DataFrame,
    emp: pd.DataFrame,
    emp_col: str,
    emp_io_sector_col: str,
    *,
    geo: str | None = None,
    year: int
) -> pd.DataFrame:
    """Kendrick–Jaycox regional output.
    Returns a DataFrame with columns: industry, output (national), region_output, sometimes with
    geo or area_fips 
    """
    
    df, df1 = emp.copy(), make_output.copy()
    
    # Esuring the employment dataset has columns names with geo or area_fips
    geo_col = next((c for c in df.columns
                    if any(x in c.lower() for x in ['geo', 'fips', 'area'])), None)
    
    # Raise concern if no geographic column
    if not geo_col:
        raise ValueError("No geographic column found.")
    
    # normalize the geo or area fips to make sure is 5 digits
    df[geo_col] = df[geo_col].astype(str).str.zfill(5)
    
    # Ensuring the employment data has year in it
    if year is not None and "year" in df.columns:
        df = df[df["year"] == year]
        if df.empty:
            raise ValueError(
                f"No rows found for year={year}. Available years: {sorted(emp['year'].unique())}"
            )
    # checking  output dataset column to see whether it has two columns
    if len(df1.columns) == 2:
        x_i = df1.set_index(df1.columns[0])[df1.columns[1]]
    else:
        raise ValueError("df1 must have exactly 2 columns, name: [Industry, output]")
    
    # filtering the national employment from employment dataframe
    e_i = df.groupby(emp_io_sector_col)[emp_col].sum()
    
    # find the regional share first
    if (geo_col in df.columns) and (geo is not None):
        e_ir = df[df[geo_col] == geo].set_index(emp_io_sector_col)[emp_col]
        share = (e_ir / e_i).reindex(x_i.index)
    else:
        e_ir = df.set_index([geo_col, emp_io_sector_col])[emp_col]
        share = e_ir.div(e_i, level=1).reindex(x_i.index, level=1)
        
        # constraint --> ensuring the total number of regions share-sum constraint <= 1
        sum_share = {}
        for i, v in zip(share.index.get_level_values(1), share.values):
            sum_share[i] = sum_share.get(i, 0.0) + float(v)

        tol = 1e-6
        check = [i for i, tot in sum_share.items() if tot > 1.0 + tol]
        if check:
            msg = [
                f"{i} sum_share={sum_share[i]:.6f} geos=[" +
                ", ".join(f"{g}:{float(s):.6f}" for g, s in share.xs(i, level=1).items()) + "]"
                for i in check
            ]
            raise ValueError("Sum of shares across regions exceeds 1:\n" + "\n".join(msg))
   
   # Constraint Checks for negative share values
    neg = share.values < 0
    if np.any(neg):
        result = share.index[neg].tolist()
        raise ValueError(f"share < 0, not reasonable; we avoid negative ---> {result}")

    pos = share.values > 1
    if np.any(pos):
        result = share.index[pos].tolist()
        raise ValueError(
            f"share > 1: the region's share is greater than the national total, "
            f"which does not conform to the analysis. "
            f"Problem industries: {result}"
        )
    
    # Compute kendrick Jaycox regional share if you filter by geo
    if geo is not None:
        x_ir = share * x_i
        df_out = pd.DataFrame(make_output.values, columns=["industry", "national_output"])
        df_out["regional_output"] = df_out["industry"].map(x_ir)
        return df_out
    # Compute kendrick Jaycox regional share for all the regions in the country if you didnt specify particular geo
    else:
        share.index = share.index.set_names("industry", level=1)

        x_ir = share.mul(x_i, level=1).rename("regional_output").reset_index()

        base_out = make_output.set_axis(["industry", "national_output"], axis=1)
        x_ir["industry"] = x_ir["industry"].astype(str)

        grid = pd.MultiIndex.from_product(
            [df[geo_col].unique(), base_out["industry"]],
            names=[geo_col, "industry"]
        ).to_frame(index=False)

        out_all = (
            grid
            .merge(base_out, on="industry", how="left")
            .merge(x_ir[[geo_col, "industry", "regional_output"]], on=[geo_col, "industry"], how="left")
        )

        return out_all[[geo_col, "industry", "national_output", "regional_output"]]
