"""OpenSees feature detection helpers used by FEM tests and toggles."""

from __future__ import annotations

import importlib
from functools import lru_cache


@lru_cache(maxsize=1)
def get_shell_dkgt_support() -> tuple[bool, str]:
    """Check whether the running OpenSeesPy build supports ShellDKGT.

    Returns:
        (is_supported, detail_message)
    """
    try:
        ops = importlib.import_module("openseespy.opensees")
    except ImportError:
        return False, "OpenSeesPy not installed"

    def _call(name: str, *args: object) -> object:
        func = getattr(ops, name, None)
        if not callable(func):
            raise RuntimeError(f"OpenSees missing callable: {name}")
        return func(*args)

    try:
        _call("wipe")
        _call("model", "basic", "-ndm", 3, "-ndf", 6)

        _call("node", 1, 0.0, 0.0, 0.0)
        _call("node", 2, 1.0, 0.0, 0.0)
        _call("node", 3, 0.0, 1.0, 0.0)

        _call("nDMaterial", "ElasticIsotropic", 1, 3.0e10, 0.2)
        _call("section", "PlateFiber", 1, 1, 0.2)

        _call("element", "ShellDKGT", 1, 1, 2, 3, 1)
        return True, "ShellDKGT available"
    except Exception as exc:  # pragma: no cover - depends on local OpenSees build
        message = str(exc).strip() or exc.__class__.__name__
        if "unknown element type" in message.lower() or "shelldkgt" in message.lower():
            return False, f"ShellDKGT unavailable: {message}"
        return False, f"ShellDKGT probe failed: {message}"
    finally:
        try:
            _call("wipe")
        except Exception:
            pass
