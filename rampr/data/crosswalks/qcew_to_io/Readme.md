## Dataset Columns from qcew_to_io_v1.csv ()

- `qcew_sector` (required)
- `io_sector` (required)
- `qcew_label` (optional)
- `io_label` (optional)

Note: Computed weight using python module below


## Module: io_bridge.py
S
This module contains 4 functions:

### 1. `_read_and_validate_csv()`
**Arguments**: 
- `qcew_to_io_v1.csv`
- `QCEW_All_0_All.csv`
- `QCEW_ALL_409.csv`

**Purpose**: Reads all datasets and validates that required columns are present. Raises `ValueError` exception if required columns are missing.

---

### 2. `build_crosswalk()`
**Arguments**: 
- `qcew_to_io_v1.csv`
- `QCEW_All_0_All.csv`
- `QCEW_ALL_409.csv`

**Note**: I used **wages** to build the weights, not employment.

**Process**: 
- Builds weights by merging datasets
- Weight calculation: each sector is divided by total sector weight (provided it has wages)
- If wage is zero, weight is set to zero (avoids ZeroDivision error)
- Merges with `QCEW_All_0_All.csv`, then aggregates weights
- Ensures weights are between 0 and 1
- For sectors not in this merge, progressively moves to `QCEW_ALL_409.csv` to fetch missing sectors with their wages, employment, and FIPS codes
- Maintains unique sectors with no duplicates

---

### 3. `load_402_sector_codes()`
**Arguments**: `bea_402_sector_codes.txt`

**Rationale**: 
After the second function, I rechecked the make_df and use_df IO sectors. My function's output was not sorted in order, which would affect the already-built national IO tables. 

For example, national IO reports sectors as 1, 2, 3, 4, 5...10, but my built crosswalk produced 1, 2, 5, 6, 8...10. Therefore, I needed to align it to follow 1, 2, 3, 4, 5...10, otherwise it would affect regionalization.

I created a `.txt` file with IO sector codes in the correct order. This function reads `io_sector_code.txt`.

---

### 4. `align_io_to_bea_402()`
**Arguments**: 
- Aggregated dataframe from `build_crosswalk()` return
- `io_sector_code.txt`

**Purpose**: 
Ensures the final crosswalk output matches BEA sectors in the correct order.

For example:
- BEA sectors: [1, 2, 3, 4, 5...10]
- Final crosswalk output: [1, 2, 3, 4, 5...10]

This is the final output we want.

---

## test_bridge_io.py

This validates the previous functions and ensures they work correctly:

1. **Weight bounds**: Validated that weights are between 0 ≤ weight ≤ 1
2. **Weight summation**: Validated that all weights in sectors are grouped uniquely per sector and area_fips with no duplication. The summation should be:
   - 1 per sector (for sectors with reported wages)
   - 0 per sector (for sectors with no reported wages)
3. **Sector count**: Validated that all sectors in each area_fips should be ≤ 402

**Test Result**: ✅ All tests passed

---

## build_qcew_io_crosswalk.py

This runs all functions starting from function #2.

**Output**: 397 unique rows

**Issue**: There are **5 missing sectors** (should be 402 total)

---

## Issues

### Missing Sectors

The following sectors are missing and not present in the QCEW sectors:
```python
[
    '333314': 'Optical instrument and lens manufacturing',
    '333316': 'Photographic and photocopying equipment manufacturing',
    '335911': 'Storage battery manufacturing',
    '335912': 'Primary battery manufacturing',
    '515200': 'Cable and other subscription programming'
]
```

These sectors are not in the qcew_sectors dataset.