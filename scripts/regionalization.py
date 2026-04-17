import pandas as pd
import numpy as np
from rampr.regionalize.kjc import kjc_share
from rampr.regionalize.msi import emp_imputation
from rampr.regionalize.regionalize import regionalize_io
from rampr.regionalize.lq import slq_table

# reading dataframe
df_output = pd.read_csv('../rampr/archive/data/output/df_output.csv')
Z_nat = pd.read_csv('../rampr/archive/data/output/A.csv')
df_emp = pd.read_csv('../rampr/archive/data/output/bridge_402.csv')

# Kendrick jaycox
df_kjc = kjc_share(df_output,df_emp, 'tap_emplvl_est_3', 'io_sector' ,year=2024)

# finding the 5 missing number in the employment dataframe
emp =  emp_imputation(df_kjc, df_emp, regional_col = "regional_output",national_col = "national_output",
                   emp_col = "tap_emplvl_est_3", emp_sector_col = "io_sector", kjc_sector_col = "industry",           
    geo_col= "area_fips")

# This is the location quotient for all counties
k = slq_table( emp ,"tap_emplvl_est_3",  "io_sector", 'area_fips', year=2024)

# Z_nat was loaded with default integer index (0–401).
# We extract the ordered industry codes from emp and assign them
# to Z_nat's index and columns so sector labels align with the LQ table.
industries = emp['io_sector'].unique().tolist()
Z_nat.index   = industries
Z_nat.columns = industries

# Regionalization 
geo = ["20169", "06073"] # area_fips for saline and San diego
df_reg = regionalize_io(Z_nat, emp,'tap_emplvl_est_3', 'io_sector', 'area_fips',
                        geo=geo,method="sqrt_slq")

# Dictionary containing regionalized Z matrices keyed by area_fips
for fips, z in df_reg.items():
    print(f"{fips}: {z.shape}")
