from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class DatasetVersionSpec:
    """
    Specification for one dataset version.

    If you provide per-file custom URLs in the registry, base_url can be "".
    """

    version: str
    registry_file: str  # relative to rampr/datasets/_registry/
    record_doi: str
    concept_doi: Optional[str]

    license: str
    license_url: str
    attribution: str
    description: str

    # Optional archive workflow:
    # If archive is set, fetch() downloads that archive and can unpack it.
    archive: Optional[str] = None
    unpack_dir: Optional[str] = None


# ---------------------------------------------------------------------
# Dataset catalog
# ---------------------------------------------------------------------
DATASETS: Dict[str, Dict[str, DatasetVersionSpec]] = {
    "qcew_2024_bea409_allcounties": {
        "v1": DatasetVersionSpec(
            version="v1",
            registry_file="qcew_2024_bea409_allcounties_v1.txt",
            record_doi="10.5281/zenodo.18248513",
            concept_doi=None,
            # IMPORTANT:
            # Set these two fields to match the Zenodo record's license exactly.
            # If you change the Zenodo record to CC BY-SA 4.0, update these accordingly.
            license="CC BY 4.0",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            attribution=(
                "Rey, Sergio (2026). Quarterly Census of Employment and Wages 2024, "
                "409 BEA Sectors, All US Counties. Zenodo. DOI: 10.5281/zenodo.18248513"
            ),
            description=(
                "QCEW 2024 data mapped to 409 BEA sectors for all US counties; "
                "distributed via the rampr Zenodo community."
            ),
            archive="QCEW_All_0_All-409.zip",
            unpack_dir="QCEW_All_0_All-409",
        )
    },
    "bea_make_use_io_tables": {
        "v1": DatasetVersionSpec(
            version="v1",
            registry_file="bea_make_use_18249105_v1.txt",
            record_doi="10.5281/zenodo.18249105",
            concept_doi=None,
            license="CC BY 4.0",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            attribution=(
                "Rey, Sergio (2026). Make-Use Input-Output Tables. Zenodo. "
                "DOI: 10.5281/zenodo.18249105"
            ),
            description=(
                "Mirrored BEA Make/Use IO Excel workbooks used to build national IO models in rampr."
            ),
            archive=None,
            unpack_dir=None,
        )
    },
}
