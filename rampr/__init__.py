from importlib.metadata import version as _version

from .bridge import build_crosswalk


__all__ = ["__version__"]

try:
    __version__ = _version("rampr")
except Exception:
    __version__ = "0+unknown"
