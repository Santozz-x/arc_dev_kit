"""Arc DevKit — Developer tools for the Arc blockchain by Circle."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

from arc_devkit.client import Arc

try:
    __version__ = _version("arc-devkit")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["Arc", "__version__"]
