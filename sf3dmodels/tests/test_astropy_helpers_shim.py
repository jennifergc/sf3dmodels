from __future__ import absolute_import

import importlib.util
import sys
from pathlib import Path

import builtins
import types


def _module_not_found_error():  # pragma: no cover - helper for Python 2 compat
    try:
        return ModuleNotFoundError  # type: ignore[name-defined]
    except NameError:  # pragma: no cover
        return ImportError


def test_setup_py_uses_shim_when_setuptools_missing(monkeypatch):
    from sf3dmodels import _setuptools_shim as shim

    recorded = {}

    def fake_setup(*args, **kwargs):
        recorded["called"] = True
        recorded["kwargs"] = kwargs

    monkeypatch.setattr(shim, "setup", fake_setup)

    for modname in [m for m in sys.modules if m.startswith("setuptools")]:
        monkeypatch.delitem(sys.modules, modname, raising=False)

    missing_exc = _module_not_found_error()
    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name.startswith("setuptools"):
            raise missing_exc("No module named '{}'".format(name))
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import, raising=False)
    monkeypatch.setattr(sys, "argv", ["setup.py", "build"])

    # Provide lightweight stand-ins for the pieces of astropy_helpers that
    # setup.py expects to import so the module can be executed safely.
    fake_astropy_helpers = types.ModuleType("astropy_helpers")
    fake_astropy_helpers.__path__ = []
    fake_setup_helpers = types.ModuleType("astropy_helpers.setup_helpers")
    fake_git_helpers = types.ModuleType("astropy_helpers.git_helpers")
    fake_version_helpers = types.ModuleType("astropy_helpers.version_helpers")
    fake_ah_bootstrap = types.ModuleType("ah_bootstrap")
    fake_distutils = types.ModuleType("distutils")
    fake_distutils.__path__ = []
    fake_distutils_core = types.ModuleType("distutils.core")
    fake_distutils_version = types.ModuleType("distutils.version")

    class _LooseVersion(object):
        def __init__(self, version):
            self.version = version

        def __lt__(self, other):  # pragma: no cover - simple shim
            return str(self.version) < str(getattr(other, "version", other))

    fake_distutils_core.setup = lambda *a, **k: None
    fake_distutils_version.LooseVersion = _LooseVersion
    fake_distutils.core = fake_distutils_core
    fake_distutils.version = fake_distutils_version

    from collections import defaultdict

    def _get_package_info():
        return {
            "package_data": defaultdict(list),
            "packages": [],
            "package_dir": {},
            "ext_modules": [],
        }

    fake_setup_helpers.register_commands = lambda *a, **k: {}
    fake_setup_helpers.get_debug_option = lambda *a, **k: False
    fake_setup_helpers.get_package_info = _get_package_info
    fake_git_helpers.get_git_devstr = lambda *a, **k: ""
    fake_version_helpers.generate_version_py = lambda *a, **k: None

    for name, module in {
        "astropy_helpers": fake_astropy_helpers,
        "astropy_helpers.setup_helpers": fake_setup_helpers,
        "astropy_helpers.git_helpers": fake_git_helpers,
        "astropy_helpers.version_helpers": fake_version_helpers,
        "astropy_helpers.setuptools_shim": shim,
        "ah_bootstrap": fake_ah_bootstrap,
        "distutils": fake_distutils,
        "distutils.core": fake_distutils_core,
        "distutils.version": fake_distutils_version,
    }.items():
        if name in sys.modules:
            monkeypatch.delitem(sys.modules, name, raising=False)
        monkeypatch.setitem(sys.modules, name, module)

    setup_path = Path(__file__).resolve().parents[2] / "setup.py"
    module_name = "sf3dmodels_setup_for_test"
    spec = importlib.util.spec_from_file_location(module_name, str(setup_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    finally:
        sys.modules.pop(module_name, None)

    assert recorded.get("called", False), "Shim setup was not invoked"


def test_shim_ignores_setuptools_only_keywords(monkeypatch):
    from sf3dmodels import _setuptools_shim  # ensures alias registration
    from astropy_helpers import setuptools_shim as shim

    captured = {}

    def fake_distutils_setup(*args, **kwargs):
        captured["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(shim, "_DISTUTILS_SETUP", fake_distutils_setup)

    result = shim.setup(name="pkg", entry_points={"console_scripts": []})

    assert result == "ok"
    assert captured["kwargs"] == {"name": "pkg"}
