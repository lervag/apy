"""Simple module to load configuration from file"""

import json
import os
from pathlib import Path
from typing import Any, Optional


def get_base_path() -> Optional[str]:
    """Get base path on current system"""
    # If base_path not defined: Look in environment variables
    if path_as_str := os.environ.get("APY_BASE"):
        return path_as_str

    if path_as_str := os.environ.get("ANKI_BASE"):
        return path_as_str

    # Otherwise look in usual paths:
    # https://docs.ankiweb.net/files.html#file-locations
    if xdg_data_home := os.environ.get("XDG_DATA_HOME"):
        if (path := Path(xdg_data_home) / "Anki2").exists():
            return str(path)

    if (path := Path.home() / ".local/share/Anki2").exists():
        return str(path)

    if (path := Path.home() / "Library/Application Support/Anki2").exists():
        return str(path)

    return None


# Parse configuration file (if it exists)
cfg: dict[str, Any]
cfg_path = os.environ.get("APY_CONFIG", "~/.config/apy/apy.json")
cfg_file = Path(cfg_path).expanduser()
if cfg_file.exists():
    with cfg_file.open(encoding="utf8") as f:
        cfg = json.load(f)
else:
    cfg = {}


CFG_DEFAULT_VALUES: dict[str, Any] = {
    "base_path": None,
    "img_viewers": {
        "svg": ["display", "-density", "300"],
    },
    "img_viewers_default": ["feh"],
    "markdown_models": ["Basic"],
    "markdown_pygments_style": "friendly",
    "presets": {},
    "profile_name": None,
    "query": "tag:marked OR -flag:0",
    "review_show_cards": False,
}

# Ensure that cfg has required keys
for required, default in CFG_DEFAULT_VALUES.items():
    if required not in cfg:
        cfg[required] = default


if cfg["base_path"] is None:
    cfg["base_path"] = get_base_path()


# Ensure base path is a proper absolute path
if cfg["base_path"]:
    cfg["base_path"] = os.path.abspath(os.path.expanduser(cfg["base_path"]))


# Ensure that default preset is defined
if "default" not in cfg["presets"]:
    cfg["presets"]["default"] = {
        "model": "Basic",
        "tags": [],
    }
