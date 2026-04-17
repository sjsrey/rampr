# rampr/regionalize/mock.py
from __future__ import annotations

import numpy as np
import pandas as pd


def make_mock_employment(
    industries: list[str],
    geos: list[str],
    years: list[int],
    *,
    seed: int = 0,
    nat_industry_size: float = 1_000_000.0,
    nat_industry_skew: float = 1.2,
    region_size_cv: float = 0.35,
    specialization_strength: float = 0.8,
    dominant_industries: dict[str, list[str]] | None = None,
    time_growth_mu: float = 0.01,
    time_growth_sigma: float = 0.02,
    noise_sigma: float = 0.08,
) -> pd.DataFrame:
    """
    Return a tidy employment table with columns:
      geo, year, industry, emp

    Generates coherent national series and regional series that:
      - sum roughly to a plausible national total (not exact by default)
      - have persistent regional specialization
      - have industry-specific time growth + noise

    dominant_industries: optional mapping geo -> list of industries to overweight.
    """
    rng = np.random.default_rng(seed)

    I = len(industries)
    G = len(geos)
    T = len(years)

    # National baseline industry weights (heavy-tailed)
    x = rng.pareto(nat_industry_skew, size=I) + 1.0
    w_ind = x / x.sum()
    nat_base = nat_industry_size * w_ind  # baseline national by industry (level)

    # National time growth factors by industry
    g_ind = rng.normal(time_growth_mu, time_growth_sigma, size=I)
    nat_time = np.exp(np.outer(np.arange(T), g_ind))  # T x I multiplicative

    nat_emp = nat_time * nat_base[None, :]  # T x I

    # Region size weights
    r = rng.lognormal(mean=0.0, sigma=region_size_cv, size=G)
    w_reg = r / r.sum()

    # Persistent specialization: region x industry multipliers
    # centered so average multiplier ~ 1
    spec = rng.normal(0.0, specialization_strength, size=(G, I))
    spec = np.exp(spec)
    spec = spec / spec.mean(axis=0, keepdims=True)

    # Apply dominant industry boosts
    if dominant_industries:
        ind_idx = {k: i for i, k in enumerate(industries)}
        for geo, inds in dominant_industries.items():
            if geo not in geos:
                continue
            gix = geos.index(geo)
            for ind in inds:
                if ind in ind_idx:
                    spec[gix, ind_idx[ind]] *= 2.0  # simple boost

    # Build regional series
    rows = []
    for t, year in enumerate(years):
        # region-industry expected = (national industry) * (region share) * (specialization)
        base = nat_emp[t, :][None, :] * w_reg[:, None] * spec

        # multiplicative noise, keep positive
        eps = rng.normal(0.0, noise_sigma, size=(G, I))
        emp = base * np.exp(eps)

        for g, geo in enumerate(geos):
            rows.append(
                pd.DataFrame(
                    {
                        "geo": geo,
                        "year": year,
                        "industry": industries,
                        "emp": emp[g, :],
                    }
                )
            )

    out = pd.concat(rows, ignore_index=True)
    out["emp"] = out["emp"].clip(lower=0.0)
    return out
