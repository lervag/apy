"""Test some basic features"""

import pytest

from common import testDir, AnkiSimple

pytestmark = pytest.mark.filterwarnings("ignore")


def test_decks():
    """Test empty collection"""
    with AnkiSimple() as a:
        assert a.col.decks.count() == 3
        assert set(a.deck_names) == {"Default", "NewDeck", "Deck with spaces"}
        assert a.col.decks.current()["name"] == "NewDeck"

        notes = a.add_notes_from_file(testDir + "/" + "data/deck.md")

        assert notes[0].get_deck() == "Default"
        assert notes[1].get_deck() == "NewDeck"

        # Move note cards to existing deck
        notes[0].set_deck("NewDeck")
        assert notes[0].get_deck() == "NewDeck"

        # Move note cards to new deck
        notes[1].set_deck("DeckTwo")
        assert notes[1].get_deck() == "DeckTwo"

        assert a.col.decks.count() == 4

        a.col.decks.set_current(a.deck_name_to_id["Deck with spaces"])
        # assert a.col.decks.current()["name"] == "NewDeck"
        # a.list_cards("", {})

        for cid in a.col.find_cards(""):
            card = a.col.get_card(cid)
            print((card.id, card.did))
