"""Simple module to load configuration from file"""
import os
import json
from pathlib import Path


cfg_path = os.environ.get('APY_CONFIG', '~/.config/apy/apy.json')
cfg_file = Path(cfg_path).expanduser()
if cfg_file.exists():
    with cfg_file.open() as f:
        cfg = json.load(f)
else:
    cfg = {}

if 'base' not in cfg:
    cfg['base'] = None
    for var in ['APY_BASE', 'ANKI_BASE']:
        if var in os.environ:
            cfg['base'] = os.path.abspath(os.environ[var])
            break
