"""Implement some basic test fixtures"""

import os
import tempfile
import shutil
import pytest

from apyanki.anki import Anki

testDir = os.path.dirname(__file__)


@pytest.fixture
def collection():
    """Create a temporary Anki collection for testing."""
    tmppath = os.path.join(tempfile.gettempdir(), "tempfile_test.anki2")
    shutil.copy2(testDir + "/data/test_base/Test/collection.anki2", tmppath)

    yield tmppath

    # Clean up after test
    if os.path.exists(tmppath):
        os.remove(tmppath)


class AnkiTest:
    """Create Anki collection wrapper"""

    def __init__(self, anki):
        self.a = anki

    def __enter__(self):
        return self.a

    def __exit__(self, exception_type, exception_value, traceback):
        self.a.__exit__(exception_type, exception_value, traceback)


class AnkiEmpty(AnkiTest):
    """Create Anki collection wrapper for an empty collection"""

    def __init__(self):
        (self.fd, self.name) = tempfile.mkstemp(suffix=".anki2")
        os.close(self.fd)
        os.unlink(self.name)
        super().__init__(Anki(collection_db_path=self.name))


class AnkiSimple(AnkiTest):
    """Create Anki collection wrapper"""

    def __init__(self):
        self.tmppath = os.path.join(tempfile.gettempdir(), "tempfile.anki2")
        shutil.copy2(testDir + "/data/test_base/Test/collection.anki2", self.tmppath)
        super().__init__(Anki(collection_db_path=self.tmppath))

    def __exit__(self, exception_type, exception_value, traceback):
        super().__exit__(exception_type, exception_value, traceback)
        os.remove(self.tmppath)
