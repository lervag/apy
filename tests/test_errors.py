"""Test errors and warnings"""
import pytest
from click import Abort

from apy.anki import Anki


def test_basepath_is_none():
    """Blah"""
    with pytest.raises(Abort):
        Anki(base=None)

    with pytest.raises(Abort):
        Anki(base="/non/existing/path")
