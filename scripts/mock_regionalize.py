import pandas as pd
import numpy as np

from rampr.regionalize.mock import make_mock_employment
from rampr.regionalize.lq import slq_table
from rampr.regionalize.regionalize import regionalize_io

n_industries = 409

industries = [
    f"I{i:03d}" for i in range(1, n_industries + 1)
]  # stand-in for BEA 409 codes
geos = ["06073", "06059", "06037"]  # e.g., county FIPS
years = [2020, 2021, 2022, 2023]

emp = make_mock_employment(
    industries, geos, years, dominant_industries={"06073": ["I002", "I007"]}, seed=42
)

# mock a national intermediate matrix
rng = np.random.default_rng(0)
Z_nat = pd.DataFrame(
    rng.lognormal(mean=2.0, sigma=0.7, size=(len(industries), len(industries))),
    index=industries,
    columns=industries,
)

# LQs for 2023
print(slq_table(emp, year=2023).round(2))

# Regionalize for San Diego (06073), 2023
Z_sd = regionalize_io(Z_nat, emp, geo="06073", year=2023, method="sqrt_slq")
print(Z_sd.head())
