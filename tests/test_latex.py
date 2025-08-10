from common import AnkiEmpty


def test_latex_translate_mode_off_simple():
    """Simple text replacement test for off option"""
    with AnkiEmpty() as a:
        note = a.add_notes_single(
            ["This is \\[block\\] math.", "This is \\(inline\\) math."],
            markdown=True,
            latex_translate_mode="off",
        )
        assert "data-original-markdown" in note.n.fields[0]
        assert "\\[block\\]" in note.n.fields[0]
        assert "\\(inline\\)" in note.n.fields[1]


def test_latex_translate_mode_mathjax_simple():
    """Simple text replacement test for mathjax option"""
    with AnkiEmpty() as a:
        note = a.add_notes_single(
            ["This is $$block$$ math.", "This is $inline$ math."],
            markdown=True,
            latex_translate_mode="mathjax",
        )
        assert "data-original-markdown" in note.n.fields[0]
        assert "\\[block\\]" in note.n.fields[0]
        assert "\\(inline\\)" in note.n.fields[1]


def test_latex_translate_mode_latex_simple():
    """Simple text replacement test for latex option"""
    with AnkiEmpty() as a:
        note = a.add_notes_single(
            ["This is [$$]block[/$$] math.", "This is [$]inline[$/] math."],
            markdown=True,
            latex_translate_mode="latex",
        )
        assert "data-original-markdown" in note.n.fields[0]
        assert "\\[block\\]" in note.n.fields[0]
        assert "\\(inline\\)" in note.n.fields[1]
