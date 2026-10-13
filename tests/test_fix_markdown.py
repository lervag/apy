"""Test fixing inconsistent Markdown fields"""

import shutil
import tempfile

import pytest
from typer.testing import CliRunner

from apyanki.anki import Anki
from apyanki.cli import main
from apyanki.fields import (
    check_if_inconsistent_markdown,
    convert_text_to_field,
    fix_inconsistent_markdown,
)

pytestmark = pytest.mark.filterwarnings("ignore")

MARKDOWN = """\
**Question** with [a link](https://example.com)

```
def f():
    return 1
```
"""


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("<strong>", '<strong style="color: red">'),
        ("<strong>Question</strong>", "<strong>Question </strong>"),
    ],
)
def test_fix_markup_changes(old: str, new: str) -> None:
    """Changes to the markup only are fixed"""
    field = convert_text_to_field(MARKDOWN, use_markdown=True)
    changed = field.replace(old, new)

    assert check_if_inconsistent_markdown(changed)
    assert fix_inconsistent_markdown(changed) == field


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("Question", "Changed question"),
        ("https://example.com", "https://example.org"),
        ("    return 1", "return 1"),
    ],
)
def test_keep_content_changes(old: str, new: str) -> None:
    """Changes to text, link targets or code are not fixed"""
    field = convert_text_to_field(MARKDOWN, use_markdown=True)
    changed = field.replace(old, new)

    assert check_if_inconsistent_markdown(changed)
    assert fix_inconsistent_markdown(changed) is None


@pytest.mark.parametrize("text", ["Plain text", "<b>Plain HTML</b>", MARKDOWN])
def test_keep_consistent_fields(text: str) -> None:
    """Consistent and non-Markdown fields are returned unchanged"""
    field = convert_text_to_field(text, use_markdown=text == MARKDOWN)
    assert fix_inconsistent_markdown(field) == field


def test_cli_fix_markdown() -> None:
    """Test 'apy fix-markdown' with and without --dry-run"""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdirname:
        shutil.copytree("tests/data/test_base/", tmpdirname, dirs_exist_ok=True)
        collection = f"{tmpdirname}/Test/collection.anki2"

        def count_inconsistent() -> int:
            with Anki(collection_db_path=collection) as a:
                return sum(
                    check_if_inconsistent_markdown(field)
                    for note in a.find_notes("deck:*")
                    for field in note.n.fields
                )

        n_before = count_inconsistent()
        assert n_before > 0

        args = ["-b", tmpdirname, "fix-markdown", "deck:*"]
        result = runner.invoke(main, [*args, "--dry-run"])
        assert result.exit_code == 0
        assert "Would fix" in result.output
        assert count_inconsistent() == n_before

        result = runner.invoke(main, args)
        assert result.exit_code == 0
        assert "Fixed" in result.output
        n_after = count_inconsistent()
        assert n_after < n_before

        result = runner.invoke(main, [*args, "--dry-run"])
        assert "Would fix 0 fields" in result.output
        assert count_inconsistent() == n_after
