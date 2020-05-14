"""Test some basic features"""
import pytest

from common import testDir, AnkiSimple

pytestmark = pytest.mark.filterwarnings("ignore")


def test_decks():
    """Test empty collection"""
    with AnkiSimple() as a:
        assert a.col.decks.count() == 2
        assert a.col.decks.current()['name'] == 'NewDeck'
        assert list(a.deck_names) == ['Default', 'NewDeck']

        notes = a.add_notes_from_file(testDir + '/' + 'data/deck.md')

        assert a.col.decks.name(notes[0].n.cards()[0].did) == 'Default'
        assert a.col.decks.name(notes[1].n.cards()[0].did) == 'NewDeck'
