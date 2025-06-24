"""Package for interfacing and manipulating Anki decks"""

import os
from importlib.metadata import version

__version__ = version("apyanki")


# Reduce rust verbosity, unless already explicitly increased. Anki by default
# sets it to debug
if "RUST_LOG" not in os.environ:
    os.environ["RUST_LOG"] = "warn,anki::media=info,anki::sync=info,anki::dbcheck=info"
