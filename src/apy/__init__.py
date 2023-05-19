"""Package for interfacing and manipulating Anki decks"""
import os
from importlib.util import find_spec
from importlib.metadata import version

__version__ = version('apy')


# Reduce rust verbosity, unless already explicitly increased. Anki by default
# sets it to debug
if 'RUST_LOG' not in os.environ:
    os.environ['RUST_LOG'] = 'warn,anki::media=info,anki::sync=info,anki::dbcheck=info'

# Avoid unnecessary Qt5 message
if 'DISABLE_QT5_COMPAT' not in os.environ:
    os.environ['DISABLE_QT5_COMPAT'] = '1'

if find_spec('anki') is None:
    import sys

    _path = os.environ.get('APY_ANKI_PATH', '/usr/share/anki')
    if os.path.isdir(_path):
        sys.path.append(_path)
