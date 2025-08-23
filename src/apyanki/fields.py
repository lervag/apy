"""Functions for manipulating note fields"""

from __future__ import annotations

import base64
import re
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import markdown
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning, Tag
from markdown.extensions.abbr import AbbrExtension
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.def_list import DefListExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.footnotes import FootnoteExtension
from markdownify import markdownify as to_md

from apyanki.config import cfg
from apyanki.markdown_math import MathProtectExtension

if TYPE_CHECKING:
    from anki.models import NotetypeDict

    from apyanki.anki import Anki


warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


def prepare_field_for_cli(
    field: str, use_markdown: bool = False, check_consistency: bool = True
) -> str:
    """Prepare field html for printing to screen"""
    text = convert_field_to_text(field, check_consistency)

    regex_replaces = [
        [r"\[latex\]\s*(.*?)\[/latex\]", r"```tex\n\1\n```"],
        [r"\<div\>\s*(.*?)\s*\</div\>", r"\n\1"],
    ]
    if not use_markdown:
        regex_replaces += [
            [r"<b>(.*?)</b>", r"[bold]\1[/bold]"],
            [r"<i>(.*?)</i>", r"[italic]\1[/italic]"],
            [r"\*\*(.*?)\*\*", r"[bold]\1[/bold]"],
            [r"_(.*?)_", r"[italic]\1[/italic]"],
            [r"`(.*?)`", r"[magenta]\1[/magenta]"],
        ]

    literal_replaces: list[list[str]]
    if use_markdown:
        literal_replaces = [
            [r"[$$]", "`$$"],
            [r"[/$$]", "$$`"],
        ]
    else:
        literal_replaces = [
            [r"[$$]", "$$"],
            [r"[/$$]", "$$"],
        ]

    for pattern, repl in regex_replaces:
        text = re.sub(pattern, repl, text, flags=re.S)

    for source, target in literal_replaces:
        text = text.replace(source, target)

    return text


def prepare_field_for_cli_raw(field: str) -> str:
    """Prepare html for printing to screen in raw format"""
    soup = BeautifulSoup(field.replace("\n", ""), features="html5lib")
    if (
        (first := soup.next)
        and (second := first.next)
        and (third := second.next)
        and isinstance(third, Tag)
    ):
        content = [
            e.prettify() if isinstance(e, Tag) else str(e) for e in third.contents
        ]
        return "".join(["```html\n"] + content + ["\n```"])

    return f"Could not parse!\n{field}"


def convert_field_to_text(field: str, check_consistency: bool = True) -> str:
    """Extract text from field HTML"""
    if check_if_generated_from_markdown(field):
        return _convert_field_to_markdown(field, check_consistency)

    text = _clean_html(field)
    for source, target in [
        ["<br>", "\n"],
        ["<br/>", "\n"],
        ["<br />", "\n"],
    ]:
        text = text.replace(source, target)

    return text.strip()


def convert_text_to_field(text: str, use_markdown: bool) -> str:
    """Convert text to Anki field html."""
    if use_markdown:
        return _convert_markdown_to_field(text)

    # Convert newlines to <br> tags
    text = text.replace("\n", "<br />")
    return _clean_html(text)


def toggle_field_to_markdown(field_or_text: str) -> str:
    """Toggle markdown in field"""
    if check_if_generated_from_markdown(field_or_text):
        return _convert_field_to_markdown(field_or_text)

    return _convert_markdown_to_field(field_or_text)


def check_if_generated_from_markdown(field: str) -> bool:
    """Check if text is a generated HTML"""
    tag = BeautifulSoup(field, "html.parser").find()

    return isinstance(tag, Tag) and "data-original-markdown" in tag.attrs


def check_if_inconsistent_markdown(field: str) -> bool:
    """Check if field html has consistent markdown values"""
    if check_if_generated_from_markdown(field):
        extracted_md = _convert_field_to_markdown(field)
        return field != _convert_markdown_to_field(extracted_md)

    return False


def img_paths_from_field(field_html: str) -> list[Path]:
    """Gather image filenames from <img> tags in field html.

    Note: The returned paths are relative to the Anki media directory.
    """
    soup = BeautifulSoup(field_html, "html.parser")
    return [Path(x["src"]) for x in soup.find_all("img")]


def img_paths_from_field_latex(html: str, ntd: NotetypeDict, anki: Anki) -> list[Path]:
    """Gather the generated LaTeX image filenames from field html.

    Note: The returned paths are relative to the Anki media directory.
    """
    from anki import latex

    proto = anki.col._backend.extract_latex(  # pyright: ignore [reportPrivateUsage]
        text=html, svg=ntd.get("latexsvg", False), expand_clozes=False
    )
    out = latex.ExtractedLatexOutput.from_proto(proto)
    return [Path(ltx.filename) for ltx in out.latex]


#
# Private functions
#


def _convert_field_to_markdown(field: str, check_consistency: bool = False) -> str:
    """Extract generated markdown text from field HTML"""
    tag = BeautifulSoup(field, "html.parser").find()
    if not isinstance(tag, Tag):
        return field

    original_markdown = tag["data-original-markdown"]
    if isinstance(original_markdown, list):
        original_markdown = "\n".join(original_markdown)

    text = base64.b64decode(original_markdown.encode()).decode().replace("<br />", "\n")

    if check_consistency and field != _convert_markdown_to_field(text):
        html_clean = re.sub(r' data-original-markdown="[^"]*"', "", field)
        consistency_text = f"\n\n### Current HTML → Markdown\n{to_md(html_clean)}"
        consistency_text += f"\n### Current HTML\n```html\n{html_clean}\n```"
    else:
        consistency_text = ""

    # Apply latex translation based on specified latex mode
    if cfg["markdown_latex_mode"] == "latex":
        text = _latex_to_mdlatex(text)
    else:
        text = _mathjax_to_mdlatex(text)

    return text + consistency_text


def _convert_markdown_to_field(text: str) -> str:
    """Convert Markdown to field HTML"""

    # Return input text if it only contains allowed characters
    if re.fullmatch(r"[a-zA-Z0-9æøåÆØÅ ,.?+-]*", text):
        return text

    # Prepare original markdown for restoring
    # Note: convert newlines to <br> to make text readable in the Anki viewer
    original_encoded = base64.b64encode(text.replace("\n", "<br />").encode()).decode()

    # For convenience: Escape some common LaTeX constructs
    text = text.replace(r"\\", r"\\\\")
    text = text.replace(r"\{", r"\\{")
    text = text.replace(r"\}", r"\\}")
    text = text.replace(r"*}", r"\*}")

    # Fix whitespaces in input
    text = text.replace("\xc2\xa0", " ").replace("\xa0", " ")

    # For convenience: Fix mathjax escaping
    text = text.replace(r"\[", r"\\[")
    text = text.replace(r"\]", r"\\]")
    text = text.replace(r"\(", r"\\(")
    text = text.replace(r"\)", r"\\)")

    html = markdown.markdown(
        text,
        extensions=[
            "tables",
            AbbrExtension(),
            CodeHiliteExtension(
                noclasses=True,
                linenums=False,
                pygments_style=cfg["markdown_pygments_style"],
                guess_lang=False,
            ),
            DefListExtension(),
            FencedCodeExtension(),
            FootnoteExtension(),
            MathProtectExtension(cfg["markdown_latex_mode"]),
        ],
        output_format="html",
    )

    # Parse HTML and attach original markdown
    soup = BeautifulSoup(html or "<div>&nbsp;</div>", "html.parser")
    root = soup.find()
    if isinstance(root, Tag):
        root["data-original-markdown"] = original_encoded

    return str(soup)


def _latex_to_mdlatex(text: str) -> str:
    """Replace [$$]…[/$$] and [$]…[/$] with $$…$$ and $…$"""
    pattern = re.compile(
        r"""
        (\[\$\$\])(.*?)\[/\$\$\]   # match [$$]…[/$$]
        |                          # or
        (\[\$\])(.*?)\[/\$\]       # match [$]…[/$]
        """,
        re.DOTALL | re.VERBOSE,
    )

    def replacer(match: re.Match[str]) -> str:
        if match.group(1):
            return f"$${match.group(2)}$$"
        elif match.group(3):
            return f"${match.group(4)}$"
        return match.group(0)

    return pattern.sub(replacer, text)


def _mathjax_to_mdlatex(text: str) -> str:
    """Replace \\[…\\] and \\(…\\) with $$…$$ and $…$"""
    text = re.sub(r"\\\[(.*?)\\\]", r"$$\1$$", text, flags=re.DOTALL)
    text = re.sub(r"\\\((.*?)\\\)", r"$\1$", text, flags=re.DOTALL)
    return text


def _clean_html(text: str) -> str:
    """Clean up html text"""
    text = text.replace(r"&lt;", "<")
    text = text.replace(r"&gt;", ">")
    text = text.replace(r"&amp;", "&")
    text = text.replace(r"&nbsp;", " ")
    text = re.sub(r"\<b\>\s*\<\/b\>", "", text)
    text = re.sub(r"\<i\>\s*\<\/i\>", "", text)
    text = re.sub(r"\<div\>\s*\<\/div\>", "", text)
    return text.strip()
