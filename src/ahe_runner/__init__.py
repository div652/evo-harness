"""Deprecated alias of ``evoharness``, the project's name since 0.10.0.

``import ahe_runner`` and ``from ahe_runner.X import Y`` keep working: every
``ahe_runner.X`` module is the ``evoharness.X`` module itself, so classes,
exceptions, and module state are shared.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys
import warnings

warnings.warn(
    "the ahe_runner package is deprecated; import evoharness instead",
    DeprecationWarning,
    stacklevel=2,
)

_OLD = "ahe_runner"
_NEW = "evoharness"


class _AliasLoader(importlib.abc.Loader):
    def __init__(self, target: str) -> None:
        self.target = target

    def create_module(self, spec):  # type: ignore[no-untyped-def]
        return importlib.import_module(self.target)

    def exec_module(self, module) -> None:  # type: ignore[no-untyped-def]
        return None


class _AliasFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):  # type: ignore[no-untyped-def]
        if not fullname.startswith(_OLD + "."):
            return None
        real = _NEW + fullname[len(_OLD) :]
        if importlib.util.find_spec(real) is None:
            return None
        return importlib.util.spec_from_loader(fullname, _AliasLoader(real))


if not any(isinstance(finder, _AliasFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _AliasFinder())

_package = importlib.import_module(_NEW)
globals().update(
    {name: value for name, value in vars(_package).items() if not name.startswith("__")}
)
__version__ = _package.__version__
