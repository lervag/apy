"""Package for interfacing and manipulating Anki decks"""
try:
    import ankixx
except ImportError:
    import os
    import sys

    _path = os.environ.get('APY_ANKI_PATH', '/usr/share/anki')
    if os.path.isdir(_path):
        sys.path.append(_path)
