"""Test batch editing"""
import pytest

from common import testDir, AnkiSimple

pytestmark = pytest.mark.filterwarnings('ignore')


def test_change_tags():
    """Test empty collection"""
    with AnkiSimple() as a:
        a.add_notes_from_file(testDir + '/' + 'data/deck.md')

        query = 'tag:test'
        n_original = len(list(a.find_notes(query)))

        a.change_tags(query, 'testendret')
        assert len(list(a.find_notes('tag:testendret'))) == n_original

        a.change_tags(query, 'test', add=False)
        assert len(list(a.find_notes(query))) == 0
