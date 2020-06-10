"""Simple module to load configuration from file"""
import os
import json
from pathlib import Path

# Parse configuration file (if it exists)
cfg_path = os.environ.get('APY_CONFIG', '~/.config/apy/apy.json')
cfg_file = Path(cfg_path).expanduser()
if cfg_file.exists():
    with cfg_file.open() as f:
        cfg = json.load(f)
else:
    cfg = {}

# Look for base path in environment variables
if 'base' not in cfg:
    cfg['base'] = None
    for var in ['APY_BASE', 'ANKI_BASE']:
        if var in os.environ:
            cfg['base'] = os.environ[var]
            break

# Ensure that cfg has 'profile' and 'path' keys
if 'profile' not in cfg:
    cfg['profile'] = None

if 'path' not in cfg:
    cfg['path'] = None

# Add default preset
preset_def = {
    'model': 'Basic',
    'tags': []
}

if 'presets' not in cfg:
    cfg['presets'] = {'default': preset_def}
elif 'default' not in cfg['presets']:
    cfg['presets']['default'] = preset_def

# Ensure base path is a proper absolute path
if cfg['base']:
    cfg['base'] = os.path.abspath(os.path.expanduser(cfg['base']))

# Set terminal width for output
try:
    cfg['width'] = os.get_terminal_size()[0] - 3
except OSError:
    cfg['width'] = 120
