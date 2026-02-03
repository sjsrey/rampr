# rampr/regionalize/regionalize.py
from __future__ import annotations

import numpy as np
import pandas as pd
from .lq import slq


def region_factor_sqrt_slq(
    emp: pd.DataFrame,
    *,
    geo: str,
    industries: list[str],
    year: int | None = None,
    cap: float = 1.0,
) -> pd.DataFrame:
    """phi_ij = min(cap, sqrt(SLQ_i * SLQ_j))
    Returns a DataFrame indexed/columned by industries.

    Notes
    -----
    Following the literature’s emphasis on incorporating
    both supplying and purchasing industries (Miller & Blair, 2009)
    and on avoiding the upward bias of naïve location-quotient methods
    (Flegg & Webber, 1997; Round, 1983), we construct a conservative
    regionalization factor based on the geometric mean of
    industry-specific SLQs. This approach symmetrically accounts for
    supply and demand specialization while damping extreme values.
    """
    lqi = slq(emp, geo=geo, year=year).reindex(industries).fillna(0.0).to_numpy()
    phi = np.sqrt(np.outer(lqi, lqi))
    phi = np.minimum(phi, cap)
    return pd.DataFrame(phi, index=industries, columns=industries)


def regionalize_io(
    Z_nat: pd.DataFrame,
    emp: pd.DataFrame,
    *,
    geo: str,
    year: int | None = None,
    method: str = "sqrt_slq",
    cap: float = 1.0,
) -> pd.DataFrame:
    """
    Regionalize a national intermediate transactions matrix (BEA 409-style).

    Z_nat: square DataFrame with industries as index/columns.
    emp: tidy employment table.
    """
    industries = list(Z_nat.index)
    if list(Z_nat.columns) != industries:
        raise ValueError(
            "Z_nat must be square with same industry ordering in index and columns."
        )

    if method == "sqrt_slq":
        phi = region_factor_sqrt_slq(
            emp, geo=geo, industries=industries, year=year, cap=cap
        )
    else:
        raise ValueError(f"Unknown method: {method}")

    Z_reg = Z_nat * phi
    return Z_reg
