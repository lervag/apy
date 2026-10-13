import pytest
from bs4 import BeautifulSoup

from apyanki import fields
from apyanki.config import cfg
from tests.common import AnkiEmpty


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


def test_markdown_to_mathjax_many() -> None:
    cfg["markdown_latex_mode"] = "mathjax"

    with AnkiEmpty() as a:
        input = " ".join(f"${i}$" for i in range(12))
        expected = " ".join(rf"\({i}\)" for i in range(12))

        note = a.add_notes_single([input, ""], markdown=True)
        soup = BeautifulSoup(note.n.fields[0], "html.parser")
        assert soup.text == expected


def test_markdown_to_mathjax_empty() -> None:
    cfg["markdown_latex_mode"] = "mathjax"

    with AnkiEmpty() as a:
        input = "a $$$$ b"
        expected = r"a \[\] b"

        note = a.add_notes_single([input, ""], markdown=True)
        soup = BeautifulSoup(note.n.fields[0], "html.parser")
        assert soup.text == expected


@pytest.mark.parametrize(
    ("mode", "input", "expected"),
    [
        ("latex", r"$$a \\ b$$", r"[$$]a \\ b[/$$]"),
        ("latex", r"$a \{ b \}$", r"[$]a \{ b \}[/$]"),
        ("latex", r"$\{x : x_{i*}\}$", r"[$]\{x : x_{i*}\}[/$]"),
        ("mathjax", r"$$a \\ b$$", r"\[a \\ b\]"),
        ("mathjax", r"$a \{ b \}$", r"\(a \{ b \}\)"),
    ],
)
def test_markdown_math_keeps_backslashes(mode: str, input: str, expected: str) -> None:
    """LaTeX escapes inside $-math must be passed through unchanged"""
    cfg["markdown_latex_mode"] = mode

    with AnkiEmpty() as a:
        note = a.add_notes_single([input, ""], markdown=True)
        soup = BeautifulSoup(note.n.fields[0], "html.parser")
        assert soup.text == expected


def test_markdown_escapes_latex_outside_math() -> None:
    """MathJax delimiters written directly in Markdown still work"""
    cfg["markdown_latex_mode"] = "mathjax"

    with AnkiEmpty() as a:
        input = r"\[ a \\ b \] and $c \\ d$"
        expected = r"\[ a \\ b \] and \(c \\ d\)"

        note = a.add_notes_single([input, ""], markdown=True)
        soup = BeautifulSoup(note.n.fields[0], "html.parser")
        assert soup.text == expected


@pytest.mark.parametrize(
    ("input", "expected"),
    [
        ("Use `echo $HOME $PATH` here", "Use echo $HOME $PATH here"),
        ("Use ``echo `$a` $b`` here", "Use echo `$a` $b here"),
        (r"Use `a\\b` and `f(x*})`", r"Use a\\b and f(x*})"),
        (
            '```\nprintf("a\\\\n");\nx = {\\(y\\)}\n```',
            'printf("a\\\\n");\nx = {\\(y\\)}\n',
        ),
        ("$a$ `$b$` $c$", "[$]a[/$] $b$ [$]c[/$]"),
        (r"Not code: \`$x$\`", "Not code: `[$]x[/$]`"),
        ("Tick ` alone\n\nthen $x$ and `y`", "Tick ` alone\nthen [$]x[/$] and y"),
    ],
)
def test_markdown_code_is_left_untouched(input: str, expected: str) -> None:
    """Math conversion and LaTeX escapes must not touch code"""
    cfg["markdown_latex_mode"] = "latex"

    with AnkiEmpty() as a:
        note = a.add_notes_single([input, ""], markdown=True)
        soup = BeautifulSoup(note.n.fields[0], "html.parser")
        assert soup.text == expected


@pytest.mark.parametrize("mode", ["latex", "mathjax"])
@pytest.mark.parametrize(
    ("input", "expected"),
    [
        (
            "[latex]\n\\begin{align*}\n  a_i &= b \\\\\n  c &= *d*\n\\end{align*}\n[/latex]",
            "[latex]\n\\begin{align*}\n  a_i &= b \\\\\n  c &= *d*\n\\end{align*}\n[/latex]",
        ),
        ("[latex]let $u$ be $x_1 < y$[/latex]", "[latex]let $u$ be $x_1 < y$[/latex]"),
        ("**Q** [latex]$x$[/latex]", "Q [latex]$x$[/latex]"),
    ],
)
def test_markdown_latex_blocks_are_raw(mode: str, input: str, expected: str) -> None:
    """[latex]…[/latex] blocks are passed to Anki without any processing"""
    cfg["markdown_latex_mode"] = mode

    with AnkiEmpty() as a:
        note = a.add_notes_single([input, ""], markdown=True)
        soup = BeautifulSoup(note.n.fields[0], "html.parser")
        assert soup.text == expected


@pytest.mark.parametrize(
    ("mode", "expected"),
    [("latex", "[$]a<b[/$] and [$]c<d[/$]"), ("mathjax", r"\(a<b\) and \(c<d\)")],
)
def test_markdown_math_with_less_than(mode: str, expected: str) -> None:
    """Math with < must not be parsed as an HTML tag"""
    cfg["markdown_latex_mode"] = mode

    with AnkiEmpty() as a:
        note = a.add_notes_single(["$a<b$ and $c<d$", ""], markdown=True)
        soup = BeautifulSoup(note.n.fields[0], "html.parser")
        assert soup.text == expected
