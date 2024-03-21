"""Test model features"""

from common import AnkiSimple


def test_rename_model():
    """Test that we can rename models"""
    with AnkiSimple() as a:
        assert "MyTest" in a.model_names

        a.rename_model("MyTest", "NewModelName")

        assert "NewModelName" in a.model_names
        assert "MyTest" not in a.model_names
