import subprocess
import sys
from pathlib import Path

import pytest

from src.fem.opensees_capabilities import get_shell_dkgt_support


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.slow
@pytest.mark.integration
def test_gate0_benchmark_30floors_completes() -> None:
    pytest.importorskip("openseespy.opensees", reason="OpenSeesPy not available")
    cmd = [
        sys.executable,
        "scripts/benchmark.py",
        "--floors",
        "30",
        "--timeout",
        "600",
    ]
    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=1200,
        check=False,
    )
    output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    assert result.returncode == 0, output


def test_gate0_shell_dkgt_probe_supports_skip_contract(require_shell_dkgt: str) -> None:
    assert "available" in require_shell_dkgt.lower()


def test_gate0_shell_dkgt_probe_returns_diagnostic_message() -> None:
    supported, detail = get_shell_dkgt_support()
    assert isinstance(supported, bool)
    assert isinstance(detail, str)
    assert detail
