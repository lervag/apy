"""Test some basic features"""
import pytest

from common import testDir, AnkiEmpty, AnkiSimple

pytestmark = pytest.mark.filterwarnings("ignore")


def test_empty_collection():
    """Test empty collection"""
    with AnkiEmpty() as a:
        assert a.col.card_count() == 0
        assert len(a.model_names) == 5


def test_add_basic():
    """Test adding two Basic notes from file"""
    with AnkiEmpty() as a:
        input_file = testDir + "/data/basic.md"
        notes = a.add_notes_from_file(input_file)

        assert a.col.card_count() == 2
        assert a.col.note_count() == 2
        assert notes[1].n.note_type()["name"] == "Basic (type in the answer)"


def test_add_different_models():
    """Test adding with different models"""
    with AnkiSimple() as a:
        n_cards = a.col.card_count()
        a.add_notes_from_file(testDir + "/data/models.md")
        assert a.col.card_count() == n_cards + 6
