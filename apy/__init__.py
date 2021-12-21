"""Package for interfacing and manipulating Anki decks"""
__version__ = '0.8.1'

import os


# Reduce rust verbosity, unless already explicitly increased. Anki by default
# sets it to debug
if "RUST_LOG" not in os.environ:
    os.environ["RUST_LOG"] \
        = "warn,anki::media=info,anki::sync=info,anki::dbcheck=info"

try:
    import anki
except ImportError:
    import sys

    _path = os.environ.get('APY_ANKI_PATH', '/usr/share/anki')
    if os.path.isdir(_path):
        sys.path.append(_path)
