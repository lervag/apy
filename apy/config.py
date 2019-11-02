"""Simple module to load configuration from file"""
import json
from pathlib import Path


cfg_file = Path('~/.config/apy/apy.json').expanduser()
if cfg_file.exists():
    with cfg_file.open() as f:
        cfg = json.load(f)
else:
    cfg = {}
