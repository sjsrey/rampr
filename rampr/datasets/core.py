from __future__ import annotations

import os
import tarfile
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import pooch
from platformdirs import user_cache_dir


class DatasetError(RuntimeError):
    pass


# ======================================================================================
# In-memory record of fetched results (per Python process)
# ======================================================================================
# Key: (dataset_name, version) -> list[Path] returned by fetch()
_LAST_FETCH: Dict[Tuple[str, str], List[Path]] = {}


def clear_last_fetched() -> None:
    """Clear the in-memory record of fetched paths."""
    _LAST_FETCH.clear()


def last_fetched(
    name: Optional[str] = None,
    version: Optional[str] = None,
) -> Dict[Tuple[str, str], List[Path]]:
    """
    Return the in-memory record of what this process has fetched.

    If `name` is provided, restrict to that dataset (and resolved version).
    """
    if name is None and version is None:
        return {k: list(v) for k, v in _LAST_FETCH.items()}

    if name is None:
        raise DatasetError("If `version` is provided, `name` must also be provided.")

    spec = get_spec(name, version)
    key = (name, spec.version)
    return {key: list(_LAST_FETCH.get(key, []))}


# ======================================================================================
# Cache location
# ======================================================================================
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
    # <cache>/datasets/<name>/<version>/
    return (root / "datasets" / name / version).resolve()


# ======================================================================================
# Registry parsing
# ======================================================================================
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


# ======================================================================================
# Archive handling
# ======================================================================================
def _unpack_archive(archive_path: Path, unpack_to: Path) -> None:
    unpack_to.mkdir(parents=True, exist_ok=True)

    if archive_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(unpack_to)
        return

    aname = archive_path.name.lower()
    if aname.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")):
        with tarfile.open(archive_path, "r:*") as tf:
            tf.extractall(unpack_to)
        return

    raise DatasetError(f"Unsupported archive format: {archive_path.name}")


def _list_files_recursive(root: Path) -> List[Path]:
    return sorted([p for p in root.rglob("*") if p.is_file()])


# ======================================================================================
# Dataset catalog helpers
# ======================================================================================
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
            f"Unknown version {version!r} for dataset {name!r}. "
            f"Available: {sorted(versions.keys())}"
        )
    return versions[version]


def info(name: str, version: Optional[str] = None) -> Dict[str, object]:
    spec = get_spec(name, version)
    d = asdict(spec)
    d["name"] = name
    return d


# ======================================================================================
# Cache inspection (NO downloading)
# ======================================================================================
def list_dataset_files(
    cache_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, List[Path]]:
    """
    List cached dataset files (does NOT download).

    Returns a mapping {dataset_name: [Path, ...]} for datasets/versions that exist
    in the local cache.

    Notes
    -----
    - If multiple versions are cached for a dataset, all are included.
    - Paths are returned for all files under each cached dataset version directory.
    """
    cache_root = (
        Path(cache_dir).expanduser().resolve() if cache_dir else _default_cache_dir()
    )
    datasets_root = cache_root / "datasets"
    if not datasets_root.exists():
        return {}

    out: Dict[str, List[Path]] = {}
    for ds_dir in sorted([p for p in datasets_root.iterdir() if p.is_dir()]):
        files: List[Path] = []
        for ver_dir in sorted([p for p in ds_dir.iterdir() if p.is_dir()]):
            files.extend(_list_files_recursive(ver_dir))
        if files:
            out[ds_dir.name] = sorted(files)
    return out


def _search_cache_for_filename(
    filename: str,
    *,
    dataset: Optional[str] = None,
    version: Optional[str] = None,
    cache_dir: Optional[Union[str, Path]] = None,
    case_insensitive: bool = True,
) -> List[Path]:
    """
    Search the on-disk cache for files whose basename matches `filename`.
    Does NOT download.

    If dataset/version provided, restrict search to that dataset/version cache dir.
    """
    cache_root = (
        Path(cache_dir).expanduser().resolve() if cache_dir else _default_cache_dir()
    )
    target = filename.casefold() if case_insensitive else filename

    candidates: List[Path] = []
    if dataset is not None:
        spec = get_spec(dataset, version)
        base = _dataset_cache_dir(dataset, spec.version, cache_dir=cache_root)
        if base.exists():
            candidates = _list_files_recursive(base)
    else:
        datasets_root = cache_root / "datasets"
        if datasets_root.exists():
            candidates = _list_files_recursive(datasets_root)

    matches: List[Path] = []
    for p in candidates:
        name = p.name.casefold() if case_insensitive else p.name
        if name == target:
            matches.append(p)

    return sorted(matches)


# ======================================================================================
# Public path resolution helpers
# ======================================================================================
def get_path_by_filename(
    filename: str,
    *,
    dataset: Optional[str] = None,
    version: Optional[str] = None,
    unique: bool = True,
    case_insensitive: bool = True,
    cache_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """
    Resolve a file by filename without requiring the caller to pass state.

    Search order
    ------------
    1) In-memory index populated by fetch() in the current Python process.
    2) On-disk cache scan (NO downloading).

    Parameters
    ----------
    filename
        Basename to search for (e.g. "QCEW_All_0_All.csv").
    dataset, version
        Restrict search to a specific dataset/version.
    unique
        If True (default), require exactly one match.
    case_insensitive
        If True (default), match filename case-insensitively.
    cache_dir
        Optional override for cache root (or RAMPR_DATA_DIR env var).

    Returns
    -------
    Path
    """
    # --- 1) in-memory ---
    target = filename.casefold() if case_insensitive else filename
    matches: List[Path] = []

    if dataset is not None:
        spec = get_spec(dataset, version)
        key = (dataset, spec.version)
        for p in _LAST_FETCH.get(key, []):
            name = p.name.casefold() if case_insensitive else p.name
            if name == target:
                matches.append(p)
    else:
        for paths in _LAST_FETCH.values():
            for p in paths:
                name = p.name.casefold() if case_insensitive else p.name
                if name == target:
                    matches.append(p)

    # --- 2) cache scan (no downloads) ---
    if not matches:
        matches = _search_cache_for_filename(
            filename,
            dataset=dataset,
            version=version,
            cache_dir=cache_dir,
            case_insensitive=case_insensitive,
        )

    if not matches:
        scope = "cache"
        if dataset is not None:
            resolved = get_spec(dataset, version).version
            scope = f"cache for dataset={dataset!r}, version={resolved!r}"
        raise DatasetError(f"{filename!r} not found in {scope}.")

    if unique and len(matches) > 1:
        raise DatasetError(f"Multiple matches for {filename!r}: {matches}")

    return matches[0]


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


# ======================================================================================
# Fetch (download) API
# ======================================================================================
def fetch(
    name: str,
    version: Optional[str] = None,
    files: Optional[Sequence[str]] = None,
    cache_dir: Optional[Union[str, Path]] = None,
    unpack: bool = True,
) -> List[Path]:
    """
    Download dataset content into the local cache and return local Paths.

    Side-effect:
      - Records returned Paths in an in-memory index (_LAST_FETCH), enabling
        get_path_by_filename() without passing state.
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

        archive_local_str = pooch.retrieve(
            url=archive_url,
            known_hash=registry[archive_entry],
            path=str(base),
            fname=archive_entry,
            progressbar=True,
        )
        archive_local = Path(archive_local_str)

        if not unpack or not getattr(spec, "unpack_dir", None):
            result = [archive_local]
            _LAST_FETCH[(name, spec.version)] = list(result)
            return result

        unpack_to = base / spec.unpack_dir

        # Idempotent unpack
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
            _LAST_FETCH[(name, spec.version)] = list(selected)
            return selected

        result = _list_files_recursive(unpack_to)
        _LAST_FETCH[(name, spec.version)] = list(result)
        return result

    # ----------------------------
    # Non-archive workflow
    # ----------------------------
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

    result = [Path(pup.fetch(f)) for f in wanted]
    _LAST_FETCH[(name, spec.version)] = list(result)
    return result
