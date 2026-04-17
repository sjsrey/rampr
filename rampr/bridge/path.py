from __future__ import annotations
from pathlib import Path


def data_path(
    name: str,
    *,
    version: str = "v1",
    filename: str | None = None,
) -> Path:
    """
    One function for all paths.

    name options:
      - "repo_root"
      - "crosswalk_dir"
      - "qcew_to_io_crosswalk"
      - "bea_402_sector_codes"
      - "qcew_data_dir"
      - "qcew_all_csv"
    """
    repo = Path(__file__).expanduser().resolve().parents[2]

    if name == "repo_root":
        return repo

    if name == "crosswalk_dir":
        return repo / "rampr" / "data" / "crosswalks" / "qcew_to_io"

    if name == "qcew_to_io_crosswalk":
        p = data_path("crosswalk_dir") / f"qcew_to_io_{version}.csv"
        if not p.exists():
            raise FileNotFoundError(f"Crosswalk not found for version={version!r}: {p}")
        return p

    if name == "bea_402_sector_codes":
        fname = filename or "bea_402_sector_codes.txt"
        p = data_path("crosswalk_dir") / fname
        if not p.exists():
            raise FileNotFoundError(f"BEA 402 sector codes file not found: {p}")
        return p

    if name == "qcew_data_dir":
        return repo / "archive" / "data" / "raw" / "employment"

    if name == "qcew_all_csv":
        fname = filename or "QCEW_All_0_All.csv"
        p = data_path("qcew_data_dir") / fname
        if not p.exists():
            raise FileNotFoundError(f"QCEW CSV file not found: {p}")
        return p

    raise ValueError(f"Unknown path name: {name!r}")
