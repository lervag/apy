"""Simple module to load configuration from file"""
import json
import os
from pathlib import Path


def get_base_path():
    # If base not defined: Look in environment variables
    if path := os.environ.get('APY_BASE'):
        return path

    if path := os.environ.get('ANKI_BASE'):
        return path

    # Otherwise look in usual paths:
    # https://docs.ankiweb.net/files.html#file-locations
    if (path := Path.home() / '.local/share/Anki2').exists():
        return str(path)

    if xdg_data_home := os.environ.get('XDG_DATA_HOME'):
        if (path := Path(xdg_data_home) / 'Anki2').exists():
            return str(path)

    return None


# Parse configuration file (if it exists)
cfg_path = os.environ.get('APY_CONFIG', '~/.config/apy/apy.json')
cfg_file = Path(cfg_path).expanduser()
if cfg_file.exists():
    with cfg_file.open(encoding='utf8') as f:
        cfg = json.load(f)
else:
    cfg = {}


# Ensure that cfg has required keys
for required, default in [
    ('base', None),
    (
        'img_viewers',
        {
            'svg': ['display', '-density', '300'],
        },
    ),
    ('img_viewers_default', ['feh']),
    ('markdown_models', ['Basic']),
    ('presets', {}),
    ('profile', None),
    ('query', 'tag:marked OR -flag:0'),
]:
    if required not in cfg:
        cfg[required] = default


if cfg['base'] is None:
    cfg['base'] = get_base_path()


# Ensure base path is a proper absolute path
if cfg['base']:
    cfg['base'] = os.path.abspath(os.path.expanduser(cfg['base']))


# Ensure that default preset is defined
if 'default' not in cfg['presets']:
    cfg['presets']['default'] = {
        'model': 'Basic',
        'tags': [],
    }


# Set terminal width for output
try:
    cfg['width'] = os.get_terminal_size()[0] - 3
except OSError:
    cfg['width'] = 120
