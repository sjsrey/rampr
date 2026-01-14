from __future__ import annotations

import os
import tarfile
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import pooch
from platformdirs import user_cache_dir


class DatasetError(RuntimeError):
    pass


# ----------------------------
# Cache location
# ----------------------------
def _default_cache_dir() -> Path:
    """
    Cache root for downloaded datasets.

    Override with:
      - RAMPR_DATA_DIR=/path/to/cache
    """
    override = os.environ.get("RAMPR_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()

    return Path(user_cache_dir(appname="rampr", appauthor=False)).resolve()


def _dataset_cache_dir(
    name: str, version: str, cache_dir: Optional[Path] = None
) -> Path:
    root = cache_dir or _default_cache_dir()
    # ~/.cache/rampr/datasets/<name>/<version>/
    return (root / "datasets" / name / version).resolve()


# ----------------------------
# Registry parsing
# ----------------------------
def _registry_path(registry_file: str) -> Path:
    here = Path(__file__).resolve().parent
    p = here / "_registry" / registry_file
    if not p.exists():
        raise DatasetError(f"Registry file not found in package: {p}")
    return p


def _read_registry(registry_file: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Parse a pooch registry file.

    Supported line formats (whitespace separated):
      1) filename  hash
      2) filename  hash  url

    Examples:
      data.parquet  sha256:....
      data.zip      md5:....  https://.../data.zip?download=1

    Returns
    -------
    registry: filename -> hash
    urls: filename -> url (optional)
    """
    reg_path = _registry_path(registry_file)
    registry: Dict[str, str] = {}
    urls: Dict[str, str] = {}

    for raw in reg_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        if len(parts) not in (2, 3):
            raise DatasetError(f"Invalid registry line in {reg_path}: {raw!r}")

        fname, h = parts[0], parts[1]
        registry[fname] = h

        if len(parts) == 3:
            urls[fname] = parts[2]

    return registry, urls


# ----------------------------
# Archive handling
# ----------------------------
def _unpack_archive(archive_path: Path, unpack_to: Path) -> None:
    unpack_to.mkdir(parents=True, exist_ok=True)

    if archive_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(unpack_to)
        return

    # tar, tar.gz, tgz, tar.bz2, tar.xz
    aname = archive_path.name.lower()
    if aname.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")):
        with tarfile.open(archive_path, "r:*") as tf:
            tf.extractall(unpack_to)
        return

    raise DatasetError(f"Unsupported archive format: {archive_path.name}")


def _list_files_recursive(root: Path) -> List[Path]:
    return sorted([p for p in root.rglob("*") if p.is_file()])


# ----------------------------
# Dataset catalog helpers
# ----------------------------
def list_datasets() -> Dict[str, List[str]]:
    from .specs import DATASETS

    return {name: sorted(versions.keys()) for name, versions in DATASETS.items()}


def get_spec(name: str, version: Optional[str] = None):
    from .specs import DATASETS

    if name not in DATASETS:
        raise DatasetError(
            f"Unknown dataset {name!r}. Available: {sorted(DATASETS.keys())}"
        )

    versions = DATASETS[name]
    if version is None:
        version = sorted(versions.keys())[-1]

    if version not in versions:
        raise DatasetError(
            f"Unknown version {version!r} for dataset {name!r}. Available: {sorted(versions.keys())}"
        )
    return versions[version]


def info(name: str, version: Optional[str] = None) -> Dict[str, object]:
    spec = get_spec(name, version)
    d = asdict(spec)
    d["name"] = name
    return d


def path(
    name: str,
    version: Optional[str] = None,
    file: Optional[str] = None,
    cache_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """
    Return a local cache path without downloading.

    - If file is None: returns the dataset version cache directory.
    - If file is provided:
        - for archive datasets, treat as relative to unpack_dir (if declared),
          otherwise relative to cache dir.
        - errors if missing.
    """
    spec = get_spec(name, version)
    cache_dir_path = Path(cache_dir).expanduser().resolve() if cache_dir else None
    base = _dataset_cache_dir(name, spec.version, cache_dir=cache_dir_path)

    if file is None:
        return base

    if getattr(spec, "archive", None) and getattr(spec, "unpack_dir", None):
        p = (base / spec.unpack_dir / file).resolve()
    else:
        p = (base / file).resolve()

    if not p.exists():
        raise DatasetError(
            f"File not found in cache: {p}. "
            f"Run fetch({name!r}, version={spec.version!r}) first."
        )
    return p


def fetch(
    name: str,
    version: Optional[str] = None,
    files: Optional[Sequence[str]] = None,
    cache_dir: Optional[Union[str, Path]] = None,
    unpack: bool = True,
) -> List[Path]:
    """
    Download dataset content into the local cache and return local Paths.

    Key behavior for Zenodo archives:
      - Uses pooch.retrieve() for the archive file to reliably follow redirects
        and verify hashes (Zenodo often 302s to signed object storage URLs).
      - Optionally unpacks into <cache>/<unpack_dir>.
    """
    spec = get_spec(name, version)
    cache_dir_path = Path(cache_dir).expanduser().resolve() if cache_dir else None
    base = _dataset_cache_dir(name, spec.version, cache_dir=cache_dir_path)
    base.mkdir(parents=True, exist_ok=True)

    registry, urls = _read_registry(spec.registry_file)

    # ----------------------------
    # Archive workflow
    # ----------------------------
    if getattr(spec, "archive", None):
        archive_entry = spec.archive
        if archive_entry not in registry:
            raise DatasetError(
                f"Spec declares archive={archive_entry!r} but it is not present in the registry."
            )

        archive_url = urls.get(archive_entry)
        if not archive_url:
            raise DatasetError(
                f"No download URL found for archive {archive_entry!r} in registry {spec.registry_file!r}."
            )

        # Use retrieve directly for reliability with Zenodo redirects and large files.
        archive_local_str = pooch.retrieve(
            url=archive_url,
            known_hash=registry[archive_entry],
            path=str(base),
            fname=archive_entry,
            progressbar=True,
        )
        archive_local = Path(archive_local_str)

        if not unpack or not getattr(spec, "unpack_dir", None):
            return [archive_local]

        unpack_to = base / spec.unpack_dir

        # Idempotent unpack: only unpack if directory doesn't exist or is empty
        if not unpack_to.exists() or not any(unpack_to.iterdir()):
            _unpack_archive(archive_local, unpack_to)

        # If specific files requested, interpret as relative to unpack_dir
        if files:
            selected: List[Path] = []
            for rel in files:
                p = (unpack_to / rel).resolve()
                if not p.exists():
                    raise DatasetError(
                        f"Requested file not found in unpacked archive: {rel!r}. Looked for: {p}"
                    )
                selected.append(p)
            return selected

        return _list_files_recursive(unpack_to)

    # ----------------------------
    # Non-archive workflow
    # ----------------------------
    # For non-archive datasets, use pooch.create() with per-file URLs if provided.
    pup = pooch.create(
        path=str(base),
        base_url="",
        registry=registry,
        urls=urls or None,
        retry_if_failed=3,
        allow_updates=False,
    )

    if files is None:
        wanted = list(registry.keys())
    else:
        missing = [f for f in files if f not in registry]
        if missing:
            raise DatasetError(
                f"Requested file(s) not in registry for {name} {spec.version}: {missing}. "
                f"Available: {sorted(registry.keys())}"
            )
        wanted = list(files)

    return [Path(pup.fetch(f)) for f in wanted]
