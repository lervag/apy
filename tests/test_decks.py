"""Test some basic features"""
import os

import pytest

from apy.anki import Anki


pytestmark = pytest.mark.filterwarnings("ignore")
testDir = os.path.dirname(__file__)
testCol = testDir + '/data/test_base/Test/collection.anki2'


def test_decks():
    """Test empty collection"""
    with Anki(path=testCol) as a:
        assert a.col.decks.count() == 2
        assert a.col.decks.current()['name'] == 'NewDeck'
        assert list(a.deck_names) == ['Default', 'NewDeck']

        notes = a.add_notes_from_file(testDir + '/' + 'data/deck.md')
        a.modified = False

        assert a.col.decks.name(notes[0].n.cards()[0].did) == 'Default'
        assert a.col.decks.name(notes[1].n.cards()[0].did) == 'NewDeck'
