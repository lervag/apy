"""Test errors and warnings"""
import pytest
import click

from apy.anki import Anki


def test_basepath_is_none():
    """Blah"""
    with pytest.raises(click.Abort):
        Anki(base=None)

    with pytest.raises(click.Abort):
        Anki(base="/non/existing/path")
