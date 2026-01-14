import os
import pytest
from pathlib import Path

import rampr.datasets as ds
from rampr.datasets.core import DatasetError


DATASET = "qcew_2024_bea409_allcounties"
VERSION = "v1"


@pytest.mark.integration
def test_qcew_dataset_download(tmp_path, monkeypatch):
    """
    Integration test: verify that the QCEW dataset can be downloaded
    from Zenodo, unpacked, and accessed locally.

    Uses an isolated cache directory so user caches are untouched.
    """
    # Force rampr to use a temporary cache directory
    monkeypatch.setenv("RAMPR_DATA_DIR", str(tmp_path))

    # Attempt fetch
    try:
        paths = ds.fetch(DATASET, version=VERSION)
    except Exception as exc:
        pytest.skip(f"Zenodo download unavailable: {exc}")

    # Basic sanity checks
    assert paths, "fetch() returned no files"
    for p in paths[:10]:
        assert isinstance(p, Path)
        assert p.exists()
        assert p.stat().st_size > 0

    # Verify cache layout
    cache_root = ds.path(DATASET, version=VERSION)
    assert cache_root.exists()
    assert cache_root.is_dir()

    # If this is an archive-based dataset, check unpack_dir
    spec = ds.get_spec(DATASET, version=VERSION)
    if getattr(spec, "unpack_dir", None):
        unpack_dir = cache_root / spec.unpack_dir
        assert unpack_dir.exists()
        assert any(unpack_dir.rglob("*")), "Unpacked directory is empty"
