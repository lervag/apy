"""Test the CLI"""

import json
import shutil
import tempfile

import pytest
from click.testing import CliRunner

from apyanki.cli import main

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


@pytest.mark.parametrize("infile", ["basic.md", "empty.md"])
def test_cli_update_from_file(infile):
    """Test 'apy update-from-file' for various note file inputs."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdirname:
        shutil.copytree(test_collection_dir, tmpdirname, dirs_exist_ok=True)
        shutil.copy(test_data_dir + infile, tmpdirname)
        result = runner.invoke(
            main, ["-b", tmpdirname, "update-from-file", f"{tmpdirname}/{infile}"]
        )
        assert result.exit_code == 0


def test_cli_add_from_file_alias():
    """Test that 'apy add-from-file' works as an alias for 'update-from-file'."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdirname:
        shutil.copytree(test_collection_dir, tmpdirname, dirs_exist_ok=True)
        # Should work as an alias to update-from-file
        result = runner.invoke(
            main, ["-b", tmpdirname, "add-from-file", test_data_dir + "basic.md"]
        )

        assert result.exit_code == 0


def test_cli_add_single():
    """Test 'apy add-single' with Markdown parser."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdirname:
        shutil.copytree(test_collection_dir, tmpdirname, dirs_exist_ok=True)
        result = runner.invoke(
            main,
            [
                "-b",
                tmpdirname,
                "add-single",
                "-p",
                "This is **strong** question.",
                "This is `code` answer.",
            ],
        )
        assert result.exit_code == 0


def test_external_ids_mode():
    """Test update-from-file with external IDs mode."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdirname:
        shutil.copytree(test_collection_dir, tmpdirname, dirs_exist_ok=True)
        shutil.copy(test_data_dir + "external_ids.md", tmpdirname)
        shutil.copy(test_data_dir + "external_ids.json", tmpdirname)

        result = runner.invoke(
            main,
            ["-b", tmpdirname, "update-from-file", tmpdirname + "/external_ids.md"],
        )

        assert result.exit_code == 0
        assert "Updated/added" in result.output
        assert "nid:" in result.output


def test_external_ids_missing_id_header():
    """Test auto-generation of UUID when id header missing."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdirname:
        shutil.copytree(test_collection_dir, tmpdirname, dirs_exist_ok=True)
        shutil.copy(test_data_dir + "external_ids_auto.md", tmpdirname)

        result = runner.invoke(
            main,
            [
                "-b",
                tmpdirname,
                "update-from-file",
                tmpdirname + "/external_ids_auto.md",
            ],
        )

        assert result.exit_code == 0
        assert "Updated/added" in result.output
        assert "nid:" in result.output


def test_external_ids_conflict_error():
    """Test error when mixing external-ids with nid/cid headers."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdirname:
        shutil.copytree(test_collection_dir, tmpdirname, dirs_exist_ok=True)
        shutil.copy(test_data_dir + "external_ids_conflict.md", tmpdirname)

        result = runner.invoke(
            main,
            [
                "-b",
                tmpdirname,
                "update-from-file",
                tmpdirname + "/external_ids_conflict.md",
            ],
        )

        assert result.exit_code != 0
        assert "Cannot use" in result.output


def test_external_ids_update_file():
    """Test that update-from-file automatically updates the JSON file."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdirname:
        shutil.copytree(test_collection_dir, tmpdirname, dirs_exist_ok=True)
        shutil.copy(test_data_dir + "external_ids.md", tmpdirname)

        json_file = tmpdirname + "/external_ids.json"
        with open(json_file, "w") as f:
            json.dump({}, f)

        result = runner.invoke(
            main,
            ["-b", tmpdirname, "update-from-file", tmpdirname + "/external_ids.md"],
        )

        assert result.exit_code == 0

        with open(json_file, "r") as f:
            updated_ids = json.load(f)

        assert len(updated_ids) > 0
        assert "note1" in updated_ids
        assert "note2" in updated_ids
        assert updated_ids["note1"] != ""
        assert updated_ids["note2"] != ""


def test_link_duplicates():
    """Test that --link-duplicates updates IDs file with existing nid on duplicate."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdirname:
        shutil.copytree(test_collection_dir, tmpdirname, dirs_exist_ok=True)
        shutil.copy(test_data_dir + "duplicate_test.md", tmpdirname)

        external_ids_file = tmpdirname + "/external_ids.json"
        with open(external_ids_file, "w") as f:
            json.dump({}, f)

        result1 = runner.invoke(
            main,
            ["-b", tmpdirname, "update-from-file", tmpdirname + "/duplicate_test.md"],
        )
        assert result1.exit_code == 0

        with open(external_ids_file, "r") as f:
            ids_after_first = json.load(f)

        assert "note1" in ids_after_first
        original_nid = ids_after_first["note1"]

        with open(external_ids_file, "w") as f:
            json.dump({}, f)

        result2 = runner.invoke(
            main,
            [
                "-b",
                tmpdirname,
                "update-from-file",
                "-l",
                tmpdirname + "/duplicate_test.md",
            ],
        )
        assert result2.exit_code == 0
        assert "Dupe detected" in result2.output

        with open(external_ids_file, "r") as f:
            ids_after_link = json.load(f)

        assert ids_after_link["note1"] == original_nid
