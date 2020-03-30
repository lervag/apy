"""Test batch editing"""
import os

import pytest

from apy.anki import Anki


pytestmark = pytest.mark.filterwarnings("ignore")
testDir = os.path.dirname(__file__)
testCol = testDir + '/data/test_base/Test/collection.anki2'


def test_change_tags():
    """Test empty collection"""
    with Anki(path=testCol, debug=True) as a:
        a.add_notes_from_file(testDir + '/' + 'data/deck.md')

        query = 'tag:test'
        n_original = len(list(a.find_notes(query)))

        a.change_tags(query, 'testendret')
        assert len(list(a.find_notes('tag:testendret'))) == n_original

        a.change_tags(query, 'test', add=False)
        assert len(list(a.find_notes(query))) == 0
