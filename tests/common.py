"""Implement some basic test fixtures"""

import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType

import pytest

from apyanki.anki import Anki

testDir = os.path.dirname(__file__)


@pytest.fixture
def collection() -> Iterator[str]:
    """Create a temporary Anki collection for testing."""
    tmppath = os.path.join(tempfile.gettempdir(), "tempfile_test.anki2")
    shutil.copy2(testDir + "/data/test_base/Test/collection.anki2", tmppath)

    yield tmppath

    # Clean up after test
    tmpfile = Path(tmppath)
    if tmpfile.exists():
        tmpfile.unlink()


class AnkiTest:
    """Create Anki collection wrapper"""

    def __init__(self, anki: Anki) -> None:
        self.a = anki

    def __enter__(self) -> Anki:
        return self.a

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.a.__exit__(exception_type, exception_value, traceback)


class AnkiEmpty(AnkiTest):
    """Create Anki collection wrapper for an empty collection"""

    def __init__(self) -> None:
        (self.fd, self.name) = tempfile.mkstemp(suffix=".anki2")
        os.close(self.fd)
        Path(self.name).unlink()
        super().__init__(Anki(collection_db_path=self.name))


class AnkiSimple(AnkiTest):
    """Create Anki collection wrapper"""

    def __init__(self) -> None:
        self.tmppath = os.path.join(tempfile.gettempdir(), "tempfile.anki2")
        shutil.copy2(testDir + "/data/test_base/Test/collection.anki2", self.tmppath)
        super().__init__(Anki(collection_db_path=self.tmppath))

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        super().__exit__(exception_type, exception_value, traceback)
        Path(self.tmppath).unlink()
