"""Test some basic features"""

import pytest

from common import testDir, AnkiSimple

pytestmark = pytest.mark.filterwarnings("ignore")


def test_decks():
    """Test empty collection"""
    with AnkiSimple() as a:
        assert a.col.decks.count() == 2
        assert a.col.decks.current()["name"] == "NewDeck"
        assert set(a.deck_names) == {"Default", "NewDeck"}

        notes = a.add_notes_from_file(testDir + "/" + "data/deck.md")

        assert notes[0].get_deck() == "Default"
        assert notes[1].get_deck() == "NewDeck"

        # Move note cards to existing deck
        notes[0].set_deck("NewDeck")
        assert notes[0].get_deck() == "NewDeck"

        # Move note cards to new deck
        notes[1].set_deck("DeckTwo")
        assert notes[1].get_deck() == "DeckTwo"

        assert a.col.decks.count() == 3
