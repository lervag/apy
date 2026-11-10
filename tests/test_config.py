"""Test configuration file loading"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run_config_import(config_path: str) -> subprocess.CompletedProcess[str]:
    """Import apyanki.config in a fresh interpreter with APY_CONFIG set."""
    env = dict(os.environ)
    env["APY_CONFIG"] = config_path
    return subprocess.run(
        [sys.executable, "-c", "import apyanki.config; print('import ok')"],
        capture_output=True,
        text=True,
        env=env,
    )


def test_corrupt_config_warns_instead_of_crashing() -> None:
    """A corrupt config file must not crash every apy invocation."""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False
    ) as config_file:
        config_file.write("{invalid json")
        config_path = config_file.name
    try:
        proc = run_config_import(config_path)
    finally:
        Path(config_path).unlink()
    assert proc.returncode == 0
    assert "import ok" in proc.stdout
    assert "Warning" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_missing_config_is_still_fine() -> None:
    """A missing config file keeps working as before."""
    proc = run_config_import(
        str(Path(tempfile.gettempdir()) / "apy-no-such-config.json")
    )
    assert proc.returncode == 0
    assert "import ok" in proc.stdout
