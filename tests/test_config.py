"""Test configuration file loading"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from apyanki.config import Config, Preset


def run_config_import(config_path: str) -> subprocess.CompletedProcess[str]:
    """Import apyanki.config in a fresh interpreter with APY_CONFIG set."""
    env = dict(os.environ)
    env["APY_CONFIG"] = config_path
    return subprocess.run(
        [sys.executable, "-c", "import apyanki.config; print('import ok')"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )


def test_corrupt_config_warns_instead_of_crashing() -> None:
    """A corrupt config file must not crash every apy invocation."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as config_file:
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


def test_config_from_dict_parses_presets_and_defaults() -> None:
    """Presets become Preset objects, missing keys get defaults."""
    config = Config.from_dict(
        {"query": "tag:leech", "presets": {"cloze": {"model": "Cloze"}}}
    )
    assert config.query == "tag:leech"
    assert config.presets["cloze"] == Preset(model="Cloze", tags=[])
    assert config.presets["default"] == Preset()
    assert config.img_viewers_default == ["feh"]
    assert config.pngCommands is None


def test_config_defaults_are_not_shared() -> None:
    """Mutable defaults must not leak between instances."""
    first = Config()
    first.markdown_models.append("Cloze")
    assert Config().markdown_models == ["Basic"]


def test_unknown_config_key_warns(capsys: pytest.CaptureFixture[str]) -> None:
    config = Config.from_dict({"no_such_key": 1, "auto_sync": True})
    assert config.auto_sync
    assert "no_such_key" in capsys.readouterr().err


def test_invalid_preset_falls_back_to_defaults(tmp_path: Path) -> None:
    config_file = tmp_path / "apy.json"
    config_file.write_text(json.dumps({"query": "x", "presets": {"a": {"bad": 1}}}))
    proc = run_config_import(str(config_file))
    assert "import ok" in proc.stdout
    assert "Warning" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_invalid_markdown_latex_mode_is_rejected() -> None:
    with pytest.raises(ValueError, match="markdown_latex_mode"):
        _ = Config.from_dict({"markdown_latex_mode": "tex"})
