"""Minimal ``setuptools`` shim exposed as ``astropy_helpers.setuptools_shim``.

This module is imported by :mod:`setup.py` when ``setuptools`` is unavailable.
It provides a very small subset of :func:`setuptools.setup`, delegating to
``distutils.core.setup`` when available and silently discarding keyword
arguments that are only recognised by ``setuptools``.  The module registers
itself in :data:`sys.modules` so that it is accessible via the canonical
``astropy_helpers.setuptools_shim`` import path expected by upstream tooling.
"""

from __future__ import absolute_import

import re
import sys
import warnings

try:  # pragma: no cover -- Python 3 already defines ModuleNotFoundError
    ModuleNotFoundError  # type: ignore[name-defined]
except NameError:  # pragma: no cover
    ModuleNotFoundError = ImportError  # type: ignore[assignment]

try:  # pragma: no cover -- ``distutils`` is available in supported runtimes
    from distutils.core import setup as _DISTUTILS_SETUP
except ImportError:  # pragma: no cover
    _DISTUTILS_SETUP = None

# Register the module under the ``astropy_helpers`` namespace so that callers
# can simply ``import astropy_helpers.setuptools_shim``.
module_name = "astropy_helpers.setuptools_shim"
module_obj = sys.modules.get(__name__)
if module_obj is None:  # pragma: no cover - defensive for importlib loaders
    import types

    module_obj = types.ModuleType(__name__)
    module_obj.__dict__.update(globals())
    sys.modules[__name__] = module_obj

if module_name not in sys.modules:
    sys.modules[module_name] = module_obj

# Keywords understood by ``setuptools`` but rejected by ``distutils``.
_IGNORED_KEYWORDS = {
    "entry_points",
    "extras_require",
    "install_requires",
    "include_package_data",
    "python_requires",
    "setup_requires",
    "use_2to3",
    "zip_safe",
}

_UNSUPPORTED_ARG_RE = re.compile(r"unexpected keyword argument '([^']+)'")


def setup(*args, **kwargs):
    """A very small subset of :func:`setuptools.setup`.

    Parameters
    ----------
    *args, **kwargs
        Arguments passed to ``setup``.  Unsupported keyword arguments are
        quietly discarded so that ``distutils`` can continue without error.
    """

    if _DISTUTILS_SETUP is None:  # pragma: no cover
        raise ModuleNotFoundError(
            "setuptools is required to build this package and distutils is not "
            "available"
        )

    # Remove known ``setuptools``-specific keywords before invoking distutils.
    for key in list(kwargs):
        if key in _IGNORED_KEYWORDS:
            kwargs.pop(key, None)

    while True:
        try:
            return _DISTUTILS_SETUP(*args, **kwargs)
        except TypeError as exc:
            match = _UNSUPPORTED_ARG_RE.search(str(exc))
            if not match:
                raise
            unsupported_key = match.group(1)
            removed = kwargs.pop(unsupported_key, None)
            if removed is None:
                raise
            warnings.warn(
                "Ignoring unsupported distutils keyword: {}".format(unsupported_key),
                RuntimeWarning,
                stacklevel=2,
            )


__all__ = ["setup"]
