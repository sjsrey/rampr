from __future__ import annotations
import pandas as pd, numpy as np

def slq_table(
    emp: pd.DataFrame,
    emp_col: str,
    io_sector: str,
    geo_col: str,
    *,
    year: int | None = None,
) -> pd.DataFrame:
    """SLQ for all geos x industries (wide) ."""
    df = emp.copy()

    if df[geo_col].dtype != "object":
        df[geo_col] = df[geo_col].astype(str)
    if year is not None and "year" in df.columns:
        df = df[df["year"] == year]

    pivot = df.pivot(index=geo_col, columns=io_sector, values=emp_col)

    reg = pivot.to_numpy()
    reg_tot = reg.sum(axis=1, keepdims=True)
    nat     = reg.sum(axis=0, keepdims=True)
    nat_tot = nat.sum()
    
    lq = (reg / reg_tot) / (nat / nat_tot)

    tab = pd.DataFrame(lq, index=pivot.index, columns=pivot.columns)
    tab.index.name   = geo_col
    tab.columns.name = io_sector
    return tab.reindex(columns=sorted(tab.columns))