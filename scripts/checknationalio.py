#!/usr/bin/env python3
"""
Build BEA-style national IO matrices (A, L, multipliers) from
"After Redefinitions PRO Detail" USE and MAKE Excel workbooks.

Implements the BEA derivation (industry-by-industry, ITA step) where:
  g = V i
  q = U i + e   (commodity output from USE: intermediate + final demand)
  B = U * g^{-1}        (commodity-by-industry direct input coefficients)
  D = V^T * q^{-1}      (industry-by-commodity market shares)
  A = D B               (industry-by-industry direct requirements)
  L = (I - A)^{-1}
  m = column_sums(L)    (Type I / "simple" output multipliers)

Notes
-----
- This script aligns industries by the header-row codes (row 4, columns 2:),
  so USE and MAKE industry ordering matches.
- It extracts the first n_com commodity rows starting at row 5 (0-based),
  which matches the PRO Detail layout for 2017 (typically 402 commodities).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class NationalIO:
    year: int
    industry_codes: pd.Index
    commodity_codes: pd.Index
    A: np.ndarray
    L: np.ndarray
    B: np.ndarray
    D: np.ndarray
    rho: float
    multipliers: np.ndarray


def _safe_inv(v: np.ndarray) -> np.ndarray:
    """Elementwise inverse with zeros mapped to 0."""
    v = np.asarray(v, dtype=float)
    out = np.zeros_like(v)
    m = v > 0
    out[m] = 1.0 / v[m]
    return out


def _read_sheet(path: Path, year: int) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=str(year))


def _extract_aligned_blocks(
    use: pd.DataFrame,
    make: pd.DataFrame,
    *,
    n_com: int,
    n_ind: int,
    header_row: int = 4,
    data_row0: int = 5,
    data_col0: int = 2,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, pd.Index, pd.Index]:
    """
    Return aligned (U, V, q, g, commodity_codes, industry_codes).

    U: commodity × industry (intermediate use only)
    V: commodity × industry (make)
    q: commodity output from USE row sums over all columns >= data_col0 (intermediate + final demand + totals)
    g: industry output from MAKE column sums of V
    """

    # --- Industry codes from header rows (columns starting at data_col0) ---
    use_ind_codes_all = pd.Index(use.iloc[header_row, data_col0:].astype(str))
    make_ind_codes_all = pd.Index(make.iloc[header_row, data_col0:].astype(str))

    # Shared industry codes, keep USE order, then truncate to n_ind
    shared_ind = use_ind_codes_all.intersection(make_ind_codes_all)
    if len(shared_ind) < n_ind:
        raise ValueError(
            f"Only {len(shared_ind)} shared industry codes found; need n_ind={n_ind}. "
            "Check header_row/data_col0 or the workbook format."
        )
    industry_codes = shared_ind[:n_ind]

    # --- Commodity codes from first column in the commodity block ---
    use_com_codes = pd.Index(use.iloc[data_row0 : data_row0 + n_com, 0].astype(str))
    make_com_codes = pd.Index(make.iloc[data_row0 : data_row0 + n_com, 0].astype(str))

    # Align commodities by intersection, keep USE order, then truncate to n_com
    shared_com = use_com_codes.intersection(make_com_codes)
    if len(shared_com) < n_com:
        raise ValueError(
            f"Only {len(shared_com)} shared commodity codes found; need n_com={n_com}. "
            "Check n_com/data_row0 or the workbook format."
        )
    commodity_codes = shared_com[:n_com]

    # --- Build USE intermediate block U (commodity × industry) ---
    use_block = use.iloc[data_row0 : data_row0 + n_com, data_col0:].copy()
    use_block.columns = use_ind_codes_all
    use_block.index = use_com_codes

    U_df = (
        use_block.loc[commodity_codes, industry_codes]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0.0)
    )
    U = U_df.to_numpy()

    # --- Commodity output q from USE: row sums over ALL cols >= data_col0 ---
    # BEA identity: q = U i + e. Summing across the full row (industries + FD + totals)
    # yields total commodity output in the USE table convention.
    q = (
        use_block.loc[commodity_codes, :]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0.0)
        .to_numpy()
        .sum(axis=1)
    )

    # --- Build MAKE block V (commodity × industry) ---
    make_block = make.iloc[data_row0 : data_row0 + n_com, data_col0:].copy()
    make_block.columns = make_ind_codes_all
    make_block.index = make_com_codes

    V_df = (
        make_block.loc[commodity_codes, industry_codes]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0.0)
    )
    V = V_df.to_numpy()

    # Industry output g = V i  (column sums)
    g = V.sum(axis=0)

    return U, V, q, g, commodity_codes, industry_codes


def build_national_io(
    *,
    use_xlsx: Path,
    make_xlsx: Path,
    year: int,
    n_com: int = 402,
    n_ind: int = 402,
) -> NationalIO:
    use = _read_sheet(use_xlsx, year)
    make = _read_sheet(make_xlsx, year)

    U, V, q, g, commodity_codes, industry_codes = _extract_aligned_blocks(
        use, make, n_com=n_com, n_ind=n_ind
    )

    invg = _safe_inv(g)
    invq = _safe_inv(q)

    # B: commodity-by-industry
    B = U * invg  # broadcast divide each industry column by g

    # D: industry-by-commodity (V is commodity×industry, so V.T is industry×commodity)
    D = V.T * invq  # broadcast divide each commodity column by q

    # A: industry-by-industry
    A = D @ B

    # Spectral radius
    rho = float(np.max(np.abs(np.linalg.eigvals(A))))

    # Leontief inverse (will be numerically unstable if rho >= 1)
    I = np.eye(n_ind)
    L = np.linalg.inv(I - A)

    # Type I output multipliers = column sums of L
    multipliers = L.sum(axis=0)

    return NationalIO(
        year=year,
        industry_codes=industry_codes,
        commodity_codes=commodity_codes,
        A=A,
        L=L,
        B=B,
        D=D,
        rho=rho,
        multipliers=multipliers,
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--use", type=Path, required=True, help="Path to IOUse_After_Redefinitions_PRO_Detail.xlsx")
    p.add_argument("--make", type=Path, required=True, help="Path to IOMake_After_Redefinitions_PRO_Detail.xlsx")
    p.add_argument("--year", type=int, default=2017)
    p.add_argument("--n-com", type=int, default=402)
    p.add_argument("--n-ind", type=int, default=402)pp
    p.add_argument("--csv", type=Path, default=None, help="Optional path to write multipliers CSV")
    args = p.parse_args()

    io = build_national_io(
        use_xlsx=args.use,
        make_xlsx=args.make,
        year=args.year,
        n_com=args.n_com,
        n_ind=args.n_ind,
    )

    print(f"Year: {io.year}")
    print(f"rho(A): {io.rho:.12f}")
    print(f"Multipliers: min={io.multipliers.min():.6f}  mean={io.multipliers.mean():.6f}  max={io.multipliers.max():.6f}")

    if args.csv is not None:
        out = pd.DataFrame(
            {"industry_code": io.industry_codes.astype(str), "type1_output_multiplier": io.multipliers}
        )
        out.to_csv(args.csv, index=False)
        print(f"Wrote: {args.csv}")


if __name__ == "__main__":
    main()
