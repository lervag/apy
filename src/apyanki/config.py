"""Simple module to load configuration from file"""

import json
import os
import sys
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Literal, get_args

type MarkdownLatexMode = Literal["mathjax", "latex"]


@dataclass
class Preset:
    """A preset combination of model and tags for `apy add-single`"""

    model: str = "Basic"
    tags: list[str] = field(default_factory=list)


@dataclass
class Config:
    """The apy configuration; field names match the keys in apy.json"""

    base_path: str | None = None
    profile_name: str | None = None
    auto_sync: bool = False
    img_viewers: dict[str, list[str]] = field(
        default_factory=lambda: {"svg": ["display", "-density", "300"]}
    )
    img_viewers_default: list[str] = field(default_factory=lambda: ["feh"])
    markdown_models: list[str] = field(default_factory=lambda: ["Basic"])
    markdown_pygments_style: str = "friendly"
    markdown_latex_mode: MarkdownLatexMode = "mathjax"
    presets: dict[str, Preset] = field(default_factory=dict)
    query: str = "tag:marked OR -flag:0"
    review_show_cards: bool = False
    review_verbose: bool = False
    pngCommands: list[list[str]] | None = None
    svgCommands: list[list[str]] | None = None

    def __post_init__(self) -> None:
        valid_modes = get_args(MarkdownLatexMode.__value__)
        if self.markdown_latex_mode not in valid_modes:
            raise ValueError(
                f"markdown_latex_mode must be one of {valid_modes}, "
                f"got {self.markdown_latex_mode!r}"
            )
        if "default" not in self.presets:
            self.presets["default"] = Preset()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Create config from parsed JSON; raises TypeError/ValueError if invalid"""
        known = {f.name for f in fields(cls)}
        for key in data.keys() - known:
            _warn(f"ignoring unknown config key '{key}'")

        kwargs = {k: v for k, v in data.items() if k in known}
        if "presets" in kwargs:
            kwargs["presets"] = {
                name: Preset(**preset) for name, preset in kwargs["presets"].items()
            }
        return cls(**kwargs)


def get_base_path() -> str | None:
    """Get base path on current system"""
    # If base_path not defined: Look in environment variables
    if path_as_str := os.environ.get("APY_BASE"):
        return path_as_str

    if path_as_str := os.environ.get("ANKI_BASE"):
        return path_as_str

    # Otherwise look in usual paths:
    # https://docs.ankiweb.net/files.html#file-locations
    if (xdg_data_home := os.environ.get("XDG_DATA_HOME")) and (
        path := Path(xdg_data_home) / "Anki2"
    ).exists():
        return str(path)

    if (path := Path.home() / ".local/share/Anki2").exists():
        return str(path)

    if (path := Path.home() / "Library/Application Support/Anki2").exists():
        return str(path)

    return None


def _warn(message: str) -> None:
    print(f"Warning: {message}", file=sys.stderr)


def load_config(cfg_file: Path) -> Config:
    """Load config from file or fall back to defaults if unreadable"""
    config = Config()
    if cfg_file.exists():
        try:
            with cfg_file.open(encoding="utf8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise TypeError("expected a JSON object at the top level")
            config = Config.from_dict(data)
        except (OSError, ValueError, TypeError, AttributeError) as error:
            _warn(f"ignoring unreadable config file {cfg_file}: {error}")

    if config.base_path is None:
        config.base_path = get_base_path()

    # Ensure base path is a proper absolute path
    if config.base_path:
        config.base_path = os.path.abspath(os.path.expanduser(config.base_path))

    return config


cfg_file = Path(os.environ.get("APY_CONFIG", "~/.config/apy/apy.json")).expanduser()
cfg = load_config(cfg_file)
