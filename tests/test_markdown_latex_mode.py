from bs4 import BeautifulSoup
from common import AnkiEmpty

from apyanki import fields
from apyanki.config import cfg


def test_mathjax_to_mdlatex() -> None:
    for [in_string, expect] in [
        ["\\[block\\]", "$$block$$"],
        ["\\(inline\\)", "$inline$"],
    ]:
        out = fields._mathjax_to_mdlatex(in_string)
        assert out == expect


def test_latex_to_mdlatex() -> None:
    for [in_string, expect] in [
        [r"[$$]block[/$$]", "$$block$$"],
        [r"[$]inline[/$]", "$inline$"],
    ]:
        out = fields._latex_to_mdlatex(in_string)
        assert out == expect


def test_markdown_to_latex_1() -> None:
    cfg["markdown_latex_mode"] = "latex"

    with AnkiEmpty() as a:
        note = a.add_notes_single(
            ["This is $$block$$ math.", "This is $inline$ math."],
            markdown=True,
        )
        assert "data-original-markdown" in note.n.fields[0]
        assert "[$$]block[/$$]" in note.n.fields[0]
        assert "[$]inline[/$]" in note.n.fields[1]


def test_markdown_to_latex_2() -> None:
    cfg["markdown_latex_mode"] = "latex"

    with AnkiEmpty() as a:
        input = r"$\mathbb{R}_+$ and $\mathbb{R}_+$"
        expected = r"[$]\mathbb{R}_+[/$] and [$]\mathbb{R}_+[/$]"

        note = a.add_notes_single([input, ""], markdown=True)
        soup = BeautifulSoup(note.n.fields[0], "html.parser")
        assert soup.text == expected


def test_markdown_to_latex_3() -> None:
    cfg["markdown_latex_mode"] = "latex"

    with AnkiEmpty() as a:
        input = r"$$\mathbb{R}_+$$ and $$\mathbb{R}_+$$"
        expected = r"[$$]\mathbb{R}_+[/$$] and [$$]\mathbb{R}_+[/$$]"

        note = a.add_notes_single([input, ""], markdown=True)
        soup = BeautifulSoup(note.n.fields[0], "html.parser")
        assert soup.text == expected


def test_markdown_to_mathjax_1() -> None:
    cfg["markdown_latex_mode"] = "mathjax"

    with AnkiEmpty() as a:
        note = a.add_notes_single(
            ["This is $$block$$ math.", "This is $inline$ math."],
            markdown=True,
        )
        assert "data-original-markdown" in note.n.fields[0]
        assert "\\[block\\]" in note.n.fields[0]
        assert "\\(inline\\)" in note.n.fields[1]


def test_markdown_to_mathjax_2() -> None:
    cfg["markdown_latex_mode"] = "mathjax"

    with AnkiEmpty() as a:
        input = r"$\mathbb{R}_+$ and $$\mathbb{R}_+$$"
        expected = r"\(\mathbb{R}_+\) and \[\mathbb{R}_+\]"

        note = a.add_notes_single([input, ""], markdown=True)
        soup = BeautifulSoup(note.n.fields[0], "html.parser")
        assert soup.text == expected
