"""Test the CLI"""
import tempfile
import shutil

import pytest
from click.testing import CliRunner

from apy.cli import main

test_data_dir = "tests/data/"
test_collection_dir = test_data_dir + "test_base/"


def test_cli_base_directory():
    """Simple tests for base directory option."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdirname:
        # Fail if base directory is invalid
        result = runner.invoke(main, ["-b", tmpdirname])
        assert result.exit_code != 0

        # Succeed if base directory is valid
        shutil.copytree(test_collection_dir, tmpdirname, dirs_exist_ok=True)
        result = runner.invoke(main, ["-b", tmpdirname])
        assert result.exit_code == 0


# List of files that apy add-from-file should be able to successfully parse
note_files_input = [
    "basic.md",
    "empty.md",
]


@pytest.mark.parametrize(
    "note_files", [test_data_dir + file for file in note_files_input]
)
def test_cli_add_from_file(note_files):
    """Test 'apy add-from-file' for various note file inputs."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdirname:
        shutil.copytree(test_collection_dir, tmpdirname, dirs_exist_ok=True)
        result = runner.invoke(main, ["-b", tmpdirname, "add-from-file", note_files])

        assert result.exit_code == 0
