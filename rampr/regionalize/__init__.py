# rampr/regionalize/__init__.py
"""
Regionalization tools for national input–output tables.

This subpackage provides:
- mock regional employment generators
- location quotient estimators
- methods for regionalizing national IO matrices
"""

from .mock import make_mock_employment

from .lq import (
    slq,
    slq_table,
)

from .regionalize import (
    regionalize_io,
    region_factor_sqrt_slq,
)

__all__ = [
    # mock data
    "make_mock_employment",

    # location quotients
    "slq",
    "slq_table",

    # regionalization
    "regionalize_io",
    "region_factor_sqrt_slq",
]
