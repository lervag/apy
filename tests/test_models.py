"""Test model features"""
import os

from apy.anki import Anki


testDir = os.path.dirname(__file__)
testCol = testDir + '/data/test_base/Test/collection.anki2'


def test_rename_model():
    """Test that we can rename models"""
    with Anki(path=testCol, debug=True) as a:
        assert 'MyTest' in a.model_names

        a.rename_model('MyTest', 'NewModelName')

        assert 'NewModelName' in a.model_names
        assert 'MyTest' not in a.model_names
