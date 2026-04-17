# rampr/regionalize/__init__.py
"""
Regionalization tools for national input–output tables.

This subpackage provides:
- Kendrick-Jaycox share estimation
- location quotient estimators
- methods for regionalizing national IO matrices
"""

from .kjc import kjc_share
from .msi import kjc_imputation, emp_imputation
from .lq import slq_table

from .regionalize import (
    regionalize_io,
    region_factor_sqrt_slq,
)

__all__ = [
    # Kendrick-Jaycox
    "kjc_share",
    # Employment imputation for missing sectors
    'emp_imputation',
    'kjc_imputation',
    # location quotients
    "slq_table",

    # regionalization
    "regionalize_io",
    "region_factor_sqrt_slq",
]
