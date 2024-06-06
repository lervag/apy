"""Functions for manipulating note fields"""

from __future__ import annotations
import base64
from pathlib import Path
import re
from typing import Optional, TYPE_CHECKING
import warnings

from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning, Tag
import markdown
from markdown.extensions.abbr import AbbrExtension
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.def_list import DefListExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.footnotes import FootnoteExtension
from markdownify import markdownify as to_md

from apyanki.config import cfg

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
        and isinstance(third.contents, list)
    ):
        content = [
            e.prettify() if isinstance(e, Tag) else str(e) for e in third.contents
        ]
        return "".join(["```html\n"] + content + ["\n```"])

    return f"Could not parse!\n{field}"


def prepare_field_for_cli_oneline(field: str) -> str:
    """Prepare field html for printing to screen on one line"""
    text = prepare_field_for_cli(field, check_consistency=False)

    text = text.replace("\n", " ")
    text = re.sub(r"\s\s+", " ", text)
    return text


def convert_field_to_text(field: str, check_consistency: bool = True) -> str:
    """Extract text from field HTML"""
    # Remove the style block, which can be present if field is taken directly from
    # a note card via card.question() or card.answer().
    field = re.sub(r"\<style\>.*\<\/style\>", "", field, flags=re.S)

    if check_if_generated_from_markdown(field):
        return _convert_field_to_markdown(field, check_consistency)

    text = _clean_html(field)
    text = re.sub(r"\<style\>.*\<\/style\>", "", field, flags=re.S)
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
    tag = _get_first_tag(BeautifulSoup(field, "html.parser"))

    return (
        tag is not None
        and tag.attrs is not None
        and "data-original-markdown" in tag.attrs
    )


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
    # pylint: disable=import-outside-toplevel
    from anki import latex

    # pylint: disable=protected-access
    proto = anki.col._backend.extract_latex(
        text=html, svg=ntd.get("latexsvg", False), expand_clozes=False
    )
    out = latex.ExtractedLatexOutput.from_proto(proto)
    return [Path(ltx.filename) for ltx in out.latex]


#
# Private functions
#


def _convert_field_to_markdown(field: str, check_consistency: bool = False) -> str:
    """Extract generated markdown text from field HTML"""
    tag = _get_first_tag(BeautifulSoup(field, "html.parser"))
    if not tag:
        return field

    original_markdown = tag["data-original-markdown"]
    if isinstance(original_markdown, list):
        original_markdown = "\n".join(original_markdown)

    text = (
        base64.b64decode(original_markdown.encode())
        .decode("utf-8")
        .replace("<br />", "\n")
    )

    if check_consistency and field != _convert_markdown_to_field(text):
        html_clean = re.sub(r' data-original-markdown="[^"]*"', "", field)
        text += f"\n\n### Current HTML → Markdown\n{to_md(html_clean)}"
        text += f"\n### Current HTML\n```html\n{html_clean}\n```"

    # For convenience: Fix mathjax escaping
    # converted = converted.replace(r"\[", r"[")
    # converted = converted.replace(r"\]", r"]")
    # converted = converted.replace(r"\(", r"(")
    # converted = converted.replace(r"\)", r")")

    return text


def _convert_markdown_to_field(text: str) -> str:
    """Convert Markdown to field HTML"""
    # Don't convert if md text is really plain
    if re.match(r"[a-zA-Z0-9æøåÆØÅ ,.?+-]*$", text):
        return text

    # Prepare original markdown for restoring
    # Note: convert newlines to <br> to make text readable in the Anki viewer
    original_encoded = base64.b64encode(
        text.replace("\n", "<br />").encode("utf-8")
    ).decode()

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
        ],
        output_format="html",
    )

    html_tree = BeautifulSoup(html, "html.parser")

    # Find html tree root tag
    tag = _get_first_tag(html_tree)
    if not tag:
        if not html:
            # Add space to prevent input field from shrinking in UI
            html = "&nbsp;"
        html_tree = BeautifulSoup(f"<div>{html}</div>", "html.parser")
        tag = _get_first_tag(html_tree)

    if tag:
        # Store original_encoded as data-attribute on tree root
        tag["data-original-markdown"] = original_encoded

    return str(html_tree)


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


def _get_first_tag(tree: BeautifulSoup) -> Optional[Tag]:
    """Get first tag among children of tree"""
    for child in tree.children:
        if isinstance(child, Tag):
            return child

    return None
