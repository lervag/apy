from common import AnkiEmpty


def test_latexTranslateMode_off_simple():
    """Simple text replacement test for off option"""
    with AnkiEmpty() as a:
        note = a.add_notes_single(
            ["This is \\[block\\] math.", "This is \\(inline\\) math."],
            markdown=True,
            latexTranslateMode="off",
        )
        assert "data-original-markdown" in note.n.fields[0]
        assert "\\[block\\]" in note.n.fields[0]
        assert "\\(inline\\)" in note.n.fields[1]


def test_latexTranslateMode_mathjax_simple():
    """Simple text replacement test for mathjax option"""
    with AnkiEmpty() as a:
        note = a.add_notes_single(
            ["This is $$block$$ math.", "This is $inline$ math."],
            markdown=True,
            latexTranslateMode="mathjax",
        )
        assert "data-original-markdown" in note.n.fields[0]
        assert "\\[block\\]" in note.n.fields[0]
        assert "\\(inline\\)" in note.n.fields[1]


def test_latexTranslateMode_latex_simple():
    """Simple text replacement test for latex option"""
    with AnkiEmpty() as a:
        note = a.add_notes_single(
            ["This is [$$]block[/$$] math.", "This is [$]inline[$/] math."],
            markdown=True,
            latexTranslateMode="latex",
        )
        assert "data-original-markdown" in note.n.fields[0]
        assert "\\[block\\]" in note.n.fields[0]
        assert "\\(inline\\)" in note.n.fields[1]
