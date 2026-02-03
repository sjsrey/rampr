import pandas as pd
import numpy as np
from sklearn.impute import KNNImputer
from dataclasses import dataclass
from typing import Union
from pathlib import Path
from tqdm import tqdm

@dataclass(frozen=True)
class ImputationConfig:
    """Configuration for KNN imputation"""
    targets: tuple = ('tap_estabs_count', 'tap_wages_est_3', 'tap_emplvl_est_3')
    k_neighbors: int = 5
    sector_levels: tuple = (3, 4, 5, 6)
    area_weight: int = 5

def impute_missing_sectors(df_input: Union[str, Path, pd.DataFrame], 
                           missing_sectors_input: Union[str, Path, pd.DataFrame], 
                           config: ImputationConfig = ImputationConfig()):
    """
    Load CSVs or DataFrames, add missing sectors, and impute using KNN.
    
    Parameters:
    -----------
    df_input : str, Path, or pd.DataFrame
        Path to main CSV file OR DataFrame with columns: year, area_fips, io_sector, io_label, 
        tap_estabs_count, tap_wages_est_3, tap_emplvl_est_3
    missing_sectors_input : str, Path, or pd.DataFrame
        Path to CSV OR DataFrame with columns: io_sector, io_label (sectors to add)
    config : ImputationConfig
        Configuration object for imputation parameters
    
    Returns:
    --------
    DataFrame with missing sectors added and imputed
    """
    # Load data with corrected handling
    if isinstance(df_input, pd.DataFrame):
        df = df_input.copy()
    else:
        
        df_path = str(df_input) if isinstance(df_input, Path) else df_input
        df = pd.read_csv(df_path)
    
    if isinstance(missing_sectors_input, pd.DataFrame):
        missing_sectors = missing_sectors_input.copy()
    else:
        
        missing_path = str(missing_sectors_input) if isinstance(missing_sectors_input, Path) else missing_sectors_input
        missing_sectors = pd.read_csv(missing_path)
    
    # Ensure io_sector is string
    missing_sectors['io_sector'] = missing_sectors['io_sector'].astype(str).str.strip()
    df['io_sector'] = df['io_sector'].astype(str).str.strip()
   
    # Step 1: Add missing sectors
    keys = df[['year', 'area_fips']].drop_duplicates()
    
    to_add = keys.merge(
        missing_sectors[['io_sector', 'io_label']].drop_duplicates(),
        how='cross'
    )
    
    existing = df[['year', 'area_fips', 'io_sector']].drop_duplicates()
    to_add = to_add.merge(
        existing,
        on=['year', 'area_fips', 'io_sector'],
        how='left',
        indicator=True
    ).query('_merge == "left_only"').drop(columns='_merge')
    
    num_cols = list(config.targets)
    for c in num_cols:
        to_add[c] = np.nan
    
    df2 = pd.concat([df, to_add[df.columns]], ignore_index=True)
    
    # Step 2: Impute using KNN
    df2_imputed = df2.copy()
    targets = list(config.targets)
    K = config.k_neighbors
    
    # Prepare sector and area features
    sec = df2_imputed['io_sector'].astype(str).str.strip().str.upper().str[:6]
    df2_imputed['_sec'] = sec
    for L in config.sector_levels:
        df2_imputed[f'_p{L}'] = sec.str[:L]
    df2_imputed['_area'] = pd.to_numeric(df2_imputed['area_fips'].astype(str).str.strip(), errors='coerce') / 10000
    
    def get_pool(sec_val):
        for L in (6, 5, 4, 3):
            pm = df2_imputed['_sec'].str[:L].eq(sec_val[:L])
            if pm.sum() >= K+1 and all(df2_imputed.loc[pm, c].notna().any() for c in targets):
                return pm
        return None
    
    def impute_sector(sec_val):
        gmask = df2_imputed['_sec'].eq(sec_val)
        if not df2_imputed.loc[gmask, targets].isna().any().any():
            return
        
        pm = get_pool(sec_val)
        if pm is None:
            return
        
        pool = df2_imputed.loc[pm, ['_area'] + [f'_p{L}' for L in config.sector_levels] + targets].copy()
        
        # Build features: one-hot sectors + weighted area + log targets
        X_cat = pd.get_dummies(pool[[f'_p{L}' for L in config.sector_levels]], dummy_na=True)
        X_area = pd.DataFrame({f'_a{i}': pool['_area'] for i in range(config.area_weight)}, index=pool.index)
        X = pd.concat([X_cat, X_area, np.log1p(pool[targets])], axis=1)
        
        # Impute
        X_imp = pd.DataFrame(KNNImputer(n_neighbors=K, weights='distance').fit_transform(X), index=X.index, columns=X.columns)
        filled = np.expm1(X_imp.loc[gmask, targets]).clip(lower=0)
        
        for c in targets:
            m = df2_imputed.loc[gmask, c].isna()
            df2_imputed.loc[gmask & m, c] = filled.loc[m, c]
    
    for s in tqdm(df2_imputed['_sec'].unique()):
        impute_sector(s)
    
    df2_imputed.drop(columns=['_sec', '_area'] + [f'_p{L}' for L in config.sector_levels], inplace=True)
    
    return df2_imputed