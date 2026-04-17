# rampr/regionalize/regionalize.py
from __future__ import annotations

import numpy as np
import pandas as pd
from .lq import slq_table


def region_factor_sqrt_slq(
    emp: pd.DataFrame,
    emp_col: str,
    io_sector: str,
    geo_col: str,
    *,
    geo: str | list[str],
    industries: list[str],
    year: int | None = None,
    cap: float = 1.0,
) -> pd.DataFrame | dict[str, pd.DataFrame]:
    """phi_ij = min(cap, sqrt(SLQ_i * SLQ_j))
    Returns a DataFrame indexed/columned by industries.

    Note
    -----
    Following the literature's emphasis on incorporating
    both supplying and purchasing industries (Miller & Blair, 2009)
    and on avoiding the upward bias of naïve location-quotient methods
    (Flegg & Webber, 1997; Round, 1983), we construct a conservative
    regionalization factor based on the geometric mean of
    industry-specific SLQs. This approach symmetrically accounts for
    supply and demand specialization while damping extreme values.
    """
    lq = slq_table(emp, emp_col, io_sector, geo_col, year=year)

    def _phi(g: str) -> pd.DataFrame:
        lqi = (
            lq.loc[g]
            .reindex(industries)
            .fillna(0.0)
            .to_numpy()
        )
        phi = np.minimum(np.sqrt(np.outer(lqi, lqi)), cap)
        return pd.DataFrame(phi, index=industries, columns=industries)

    if isinstance(geo, str):
        return _phi(geo)
    return {g: _phi(g) for g in geo}


def regionalize_io(
    Z_nat: pd.DataFrame,
    emp: pd.DataFrame,
    emp_col: str,
    io_sector: str,
    geo_col: str,
    *,
    geo: str | list[str],
    year: int | None = None,
    method: str = "sqrt_slq",
    cap: float = 1.0,
) -> pd.DataFrame | dict[str, pd.DataFrame]:
    """
    Regionalize a national intermediate transactions matrix (BEA 402).

    Z_nat : square DataFrame with industries as index/columns.
    emp   : employment table.
    geo   : single geo string or list of geo strings.
    """
    industries = list(Z_nat.index)
    if list(Z_nat.columns) != industries:
        raise ValueError(
            "Z_nat must be square with same industry ordering in index and columns."
        )
    if method == "sqrt_slq":
        phi = region_factor_sqrt_slq(emp, emp_col, io_sector,geo_col ,geo=geo,industries=industries,year=year,cap=cap)
    else:
        raise ValueError(f"Unknown method: {method}")

    if isinstance(phi, dict):
        return {g: Z_nat * phi[g] for g in phi}
    return Z_nat * phi