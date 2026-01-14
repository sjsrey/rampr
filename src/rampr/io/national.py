from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class NationalIO:
    """
    Core national IO artifacts for a given year.

    A : Direct requirements matrix
    L : Leontief inverse
    B : Commodity-by-industry requirements (U * X^-1)
    D : Industry-by-commodity market shares (V * Q^-1) depending on convention
    """

    year: int
    A: np.ndarray
    L: np.ndarray
    B: np.ndarray
    D: np.ndarray
    commodity_df: pd.DataFrame
    industry_df: pd.DataFrame


def _read_use_make(
    use_xlsx: Union[str, Path],
    make_xlsx: Union[str, Path],
    year: int,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Read BEA-style USE and MAKE excel workbooks (all sheets), extract the year sheet,
    and return structured DataFrames.

    Returns
    -------
    use_df : DataFrame
        Use table flows (rows: commodities, cols: industries and final demand columns depending on file)
    make_df : DataFrame
        Make table flows (rows: commodities, cols: industries)
    commodity_df : DataFrame
        Code/Description for commodities
    industry_df : DataFrame
        Code/Description for industries
    """
    use_sheets = pd.read_excel(Path(use_xlsx), sheet_name=None)
    if str(year) not in use_sheets:
        raise ValueError(
            f"Year sheet {year!r} not found in USE workbook. Available: {list(use_sheets.keys())}"
        )
    use = use_sheets[str(year)]

    # These offsets are taken from your current script. Consider parameterizing
    # if BEA changes templates.
    flows = use.values[5:, 2:]
    row_codes = use.values[5:, 0]
    col_labels = use.iloc[4].values[2:]

    use_df = pd.DataFrame(flows, columns=col_labels, index=row_codes).fillna(0)

    commodity_df = pd.DataFrame(
        use.values[5:, 0:2],
        columns=["Code", "Description"],
    )

    industry_df = pd.DataFrame(
        use.values[3:5, 3:].T,
        columns=["Description", "Code"],
    )

    make_sheets = pd.read_excel(Path(make_xlsx), sheet_name=None)
    if str(year) not in make_sheets:
        raise ValueError(
            f"Year sheet {year!r} not found in MAKE workbook. Available: {list(make_sheets.keys())}"
        )
    make = make_sheets[str(year)]

    make_cols = make.iloc[4].values[2:]
    make_flows = make.values[5:, 2:]
    make_row_codes = make.values[5:, 0]

    make_df = pd.DataFrame(make_flows, columns=make_cols, index=make_row_codes).fillna(
        0
    )

    return use_df, make_df, commodity_df, industry_df


def build_national_io_from_excels(
    *,
    use_xlsx: Union[str, Path],
    make_xlsx: Union[str, Path],
    year: int = 2017,
    n_commodities: int = 400,
    n_industries: int = 402,
) -> NationalIO:
    """
    Build national IO matrices from USE and MAKE Excel workbooks.

    This function reproduces your script logic but makes dimensions explicit and
    avoids path assumptions.

    Notes on conventions:
    - U is commodity-by-industry use (subset rows/cols chosen below)
    - X is industry output (column sums of U-based table per your script)
    - B = U * diag(1/X)
    - Q is industry output for make table (column sums of V per your script)
    - D = V * diag(1/Q)
    - A = D[:-1, :n_commodities] @ B  (as in your script)
    - A then truncated to [:, :n_industries] and L = (I - A)^-1
    """
    use_df, make_df, commodity_df, industry_df = _read_use_make(
        use_xlsx, make_xlsx, year=year
    )

    # Your script slices assume the first n_commodities rows are commodities
    # and first n_industries columns correspond to industries (plus potential extras).
    U = use_df.values[:n_commodities, :]

    # Industry output proxy from use table column sums (script behavior)
    X = use_df.values.sum(axis=0)
    Xd = np.diag(1.0 / (X + (X == 0)))
    B = U @ Xd

    # Make table column sums as Q (script behavior)
    Q = make_df.values.sum(axis=0)
    Qd = np.diag(1.0 / (Q + (Q == 0)))
    D = make_df.values @ Qd

    # Direct requirements matrix (script behavior)
    A = D[:-1, :n_commodities] @ B

    # Truncate/align to industries dimension (script behavior)
    A = A[:, :n_industries]

    I = np.eye(n_industries)
    L = np.linalg.inv(I - A)

    return NationalIO(
        year=year,
        A=A,
        L=L,
        B=B,
        D=D,
        commodity_df=commodity_df,
        industry_df=industry_df,
    )
