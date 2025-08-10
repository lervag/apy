from apyanki import fields
from apyanki.config import cfg
from common import AnkiEmpty


def test_mdlatex_to_mathjax() -> None:
    for [in_string, expect] in [
        ["$$block$$", r"\\[block\\]"],
        ["$inline$", r"\\(inline\\)"],
    ]:
        out = fields._mdlatex_to_mathjax(in_string)
        assert out == expect


def test_mdlatex_to_latex() -> None:
    for [in_string, expect] in [
        ["$$block$$", r"[$$]block[/$$]"],
        ["$inline$", r"[$]inline[/$]"],
    ]:
        out = fields._mdlatex_to_latex(in_string)
        assert out == expect


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


def test_markdown_latex_mode_mathjax() -> None:
    """Simple text replacement test for mathjax option"""
    cfg["markdown_latex_mode"] = "mathjax"

    with AnkiEmpty() as a:
        note = a.add_notes_single(
            ["This is $$block$$ math.", "This is $inline$ math."],
            markdown=True,
        )
        print(note.n.fields)
        assert "data-original-markdown" in note.n.fields[0]
        assert "\\[block\\]" in note.n.fields[0]
        assert "\\(inline\\)" in note.n.fields[1]


def test_markdown_latex_mode_latex() -> None:
    """Simple text replacement test for latex option"""
    cfg["markdown_latex_mode"] = "latex"

    with AnkiEmpty() as a:
        note = a.add_notes_single(
            ["This is $$block$$ math.", "This is $inline$ math."],
            markdown=True,
        )
        assert "data-original-markdown" in note.n.fields[0]
        assert "[$$]block[/$$]" in note.n.fields[0]
        assert "[$]inline[/$]" in note.n.fields[1]
