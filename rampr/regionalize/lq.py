# rampr/regionalize/lq.py
from __future__ import annotations

import pandas as pd


def slq(emp: pd.DataFrame, *, geo: str, year: int | None = None) -> pd.Series:
    """
    Simple LQ per industry for a given geo (and optional year).

    emp columns: geo, year (optional), industry, emp
    Returns a Series indexed by industry.
    """
    df = emp.copy()
    if year is not None and "year" in df.columns:
        df = df[df["year"] == year]

    reg = df[df["geo"] == geo].groupby("industry")["emp"].sum()
    nat = df.groupby("industry")["emp"].sum()

    reg_tot = reg.sum()
    nat_tot = nat.sum()

    # align industries
    reg = reg.reindex(nat.index).fillna(0.0)
    lq = (reg / reg_tot) / (nat / nat_tot)
    return lq


def slq_table(emp: pd.DataFrame, *, year: int | None = None) -> pd.DataFrame:
    """SLQ for all geos x industries (wide)."""
    geos = emp["geo"].unique()
    inds = emp["industry"].unique()
    out = []
    for g in geos:
        s = slq(emp, geo=g, year=year)
        s.name = g
        out.append(s)
    tab = pd.concat(out, axis=1).T
    tab.index.name = "geo"
    tab = tab.reindex(columns=sorted(inds))
    return tab
