"""Test errors and warnings"""

import pytest
from click import Abort

from apyanki.anki import Anki


def test_basepath_is_none():
    """Blah"""
    with pytest.raises(Abort):
        Anki(base_path=None)

    with pytest.raises(Abort):
        Anki(base_path="/non/existing/path")
