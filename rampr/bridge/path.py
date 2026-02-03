from __future__ import annotations
from pathlib import Path
import rampr.datasets as ds


def repo_root() -> Path:
    """
    Get out of the current python package directory to rampr directory

    """
    return Path(__file__).resolve().parents[2]


def crosswalk_dir() -> Path:
    """
    <repo>/rampr/data/crosswalks/qcew_to_io
    """
    return repo_root() / "rampr" / "data" / "crosswalks" / "qcew_to_io"


def qcew_to_io_crosswalk_path(version: str = "v1") -> Path:
    """
    Example:
      version="v1" -> qcew_to_io_v1.csv
    """
    p = crosswalk_dir() / f"qcew_to_io_{version}.csv"
    if not p.exists():
        raise FileNotFoundError(f"Crosswalk not found for version={version!r}: {p}")
    return p


def bea_402_sector_codes_path(filename: str = "bea_402_sector_codes.txt") -> Path:
    """
    Resolve the BEA 402 codes file stored alongside the crosswalk in the same directory.
    """
    p = crosswalk_dir() / filename
    if not p.exists():
        raise FileNotFoundError(f"BEA 402 sector codes file not found: {p}")
    return p


def qcew_data_dir() -> Path:
    """
    <repo>/rampr/archive/data/raw
    """
    return repo_root() / "archive" / "data" / "raw" / "employment"



def qcew_all_csv_path(filename: str = "QCEW_All_0_All.csv") -> Path:
    repo_root = Path(__file__).resolve().parents[2]  
    p = repo_root / "archive" / "data" / "raw" / "employment" / filename
    if not p.exists():
        raise FileNotFoundError(f"QCEW CSV file not found: {p}")
    return p
