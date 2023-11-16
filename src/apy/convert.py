"""Convert between formats/targets"""

import base64
import re
from typing import Any, Optional
import warnings

from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning, Tag
import click
import markdown
from markdown.extensions.abbr import AbbrExtension
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.def_list import DefListExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.footnotes import FootnoteExtension
from markdownify import markdownify as to_md

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


def markdown_file_to_notes(filename: str) -> list[dict[str, Any]]:
    """Parse notes data from Markdown file

    The following example should adequately specify the syntax.

        //input.md
        model: Basic
        tags: marked

        # Note 1
        ## Front
        Question?

        ## Back
        Answer.

        # Note 2
        tag: silly-tag

        ## Front
        Question?

        ## Back
        Answer

        # Note 3
        model: NewModel
        markdown: false (default is true)

        ## NewFront
        FieldOne

        ## NewBack
        FieldTwo

        ## FieldThree
        FieldThree
    """
    try:
        defaults, notes = _parse_file(filename)
    except KeyError as e:
        click.echo(f"Error {e.__class__} when parsing {filename}!")
        click.echo("This may typically be due to bad Markdown formatting.")
        raise click.Abort()

    # Parse markdown flag
    if "markdown" in defaults:
        defaults["markdown"] = defaults["markdown"] in ("true", "yes")
    elif "md" in defaults:
        defaults["markdown"] = defaults["md"] in ("true", "yes")
        defaults.pop("md")

    # Remove comma from tag list
    if "tags" in defaults:
        defaults["tags"] = defaults["tags"].replace(",", "")

    # Add some explicit defaults (unless added in file)
    defaults = {
        **{
            "model": "Basic",
            "markdown": True,
            "tags": "",
        },
        **defaults,
    }

    # Ensure each note has all necessary properties
    for note in notes:
        # Parse markdown flag
        if "markdown" in note:
            note["markdown"] = note["markdown"] in ("true", "yes")
        elif "md" in note:
            note["markdown"] = note["md"] in ("true", "yes")
            note.pop("md")

        # Remove comma from tag list
        if "tags" in note:
            note["tags"] = note["tags"].replace(",", "")

        note.update({k: v for k, v in defaults.items() if k not in note})

    return notes


def _parse_file(filename: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Get data from file"""
    defaults: dict[str, Any] = {}
    notes: list[dict[str, Any]] = []
    note: dict[str, Any] = {}
    codeblock = False
    field = None
    with open(filename, "r", encoding="utf8") as f:
        for line in f:
            if codeblock:
                if field:
                    note["fields"][field] += line
                match = re.match(r"```\s*$", line)
                if match:
                    codeblock = False
                continue

            match = re.match(r"```\w*\s*$", line)
            if match:
                codeblock = True
                if field:
                    note["fields"][field] += line
                continue

            if not field:
                match = re.match(r"(\w+): (.*)", line)
                if match:
                    k, v = match.groups()
                    k = k.lower()
                    if k == "tag":
                        k = "tags"
                    note[k] = v.strip()
                    continue

            match = re.match(r"(#+)\s*(.*)", line)
            if not match:
                if field:
                    note["fields"][field] += line
                continue

            level, title = match.groups()

            if len(level) == 1:
                if note:
                    if field:
                        note["fields"][field] = note["fields"][field].strip()
                        notes.append(note)
                    else:
                        defaults.update(note)

                note = {"title": title, "fields": {}}
                field = None
                continue

            if len(level) == 2:
                if field:
                    note["fields"][field] = note["fields"][field].strip()

                if title in note:
                    click.echo(f"Error when parsing {filename}!")
                    raise click.Abort()

                field = title
                note["fields"][field] = ""

    if note and field:
        note["fields"][field] = note["fields"][field].strip()
        notes.append(note)

    return defaults, notes


def markdown_to_html(md: str) -> str:
    """Convert Markdown to HTML"""
    # Don't convert if md text is really plain
    if re.match(r"[a-zA-Z0-9æøåÆØÅ ,.?+-]*$", md):
        return md

    # Prepare original markdown for restoring
    # Note: convert newlines to <br> to make text readable in the Anki viewer
    original_encoded = base64.b64encode(
        md.replace("\n", "<br />").encode("utf-8")
    ).decode()

    # For convenience: Escape some common LaTeX constructs
    md = md.replace(r"\\", r"\\\\")
    md = md.replace(r"\{", r"\\{")
    md = md.replace(r"\}", r"\\}")
    md = md.replace(r"*}", r"\*}")

    # Fix whitespaces in input
    md = md.replace("\xc2\xa0", " ").replace("\xa0", " ")

    # For convenience: Fix mathjax escaping
    md = md.replace(r"\[", r"\\[")
    md = md.replace(r"\]", r"\\]")
    md = md.replace(r"\(", r"\\(")
    md = md.replace(r"\)", r"\\)")

    html = markdown.markdown(
        md,
        extensions=[
            "tables",
            AbbrExtension(),
            CodeHiliteExtension(
                noclasses=True,
                linenums=False,
                pygments_style="friendly",
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


def plain_to_html(plain: str) -> str:
    """Convert plain text to html"""
    # Minor clean up
    plain = plain.replace(r"&lt;", "<")
    plain = plain.replace(r"&gt;", ">")
    plain = plain.replace(r"&amp;", "&")
    plain = plain.replace(r"&nbsp;", " ")
    plain = re.sub(r"\<b\>\s*\<\/b\>", "", plain)
    plain = re.sub(r"\<i\>\s*\<\/i\>", "", plain)
    plain = re.sub(r"\<div\>\s*\<\/div\>", "", plain)

    # Convert newlines to <br> tags
    plain = plain.replace("\n", "<br />")

    return plain.strip()


def html_to_markdown(html: str) -> str:
    """Extract Markdown from generated HTML"""
    tag = _get_first_tag(BeautifulSoup(html, "html.parser"))
    if not tag:
        return html

    original_markdown = tag["data-original-markdown"]
    if isinstance(original_markdown, list):
        original_markdown = "\n".join(original_markdown)

    encoded_bytes = original_markdown.encode()
    converted = base64.b64decode(encoded_bytes).decode("utf-8")
    return converted.replace("<br>", "\n").replace("<br />", "\n")


def html_to_screen(html: str, pprint: bool = True, parseable: bool = False) -> str:
    """Convert html for printing to screen"""
    if not pprint:
        soup = BeautifulSoup(html.replace("\n", ""), features="html5lib")
        if (
            (first := soup.next)
            and (second := first.next)
            and (third := second.next)
            and isinstance(third, Tag)
            and isinstance(third.contents, list)
        ):
            return "".join(
                [
                    el.prettify() if isinstance(el, Tag) else str(el)
                    for el in third.contents
                ]
            )

        return "Could not parse!\n" + html

    html = re.sub(r"\<style\>.*\<\/style\>", "", html, flags=re.S)

    generated = is_generated_html(html)
    if generated:
        plain = html_to_markdown(html)
        if html != markdown_to_html(plain):
            html_clean = re.sub(r' data-original-markdown="[^"]*"', "", html)
            if parseable:
                plain += "\n\n### Current HTML → Markdown\n" f"{to_md(html_clean)}"
                plain += f"\n### Current HTML\n{html_clean}"
            else:
                plain += "\n"
                plain += click.style(
                    "The current HTML value is inconsistent with Markdown!",
                    fg="red",
                    bold=True,
                )
                plain += "\n" + click.style(html_clean, fg="white")
    else:
        plain = html

    # For convenience: Un-escape some common LaTeX constructs
    plain = plain.replace(r"\\\\", r"\\")
    plain = plain.replace(r"\\{", r"\{")
    plain = plain.replace(r"\\}", r"\}")
    plain = plain.replace(r"\*}", r"*}")

    plain = plain.replace(r"&lt;", "<")
    plain = plain.replace(r"&gt;", ">")
    plain = plain.replace(r"&amp;", "&")
    plain = plain.replace(r"&nbsp;", " ")

    plain = plain.replace("<br>", "\n")
    plain = plain.replace("<br/>", "\n")
    plain = plain.replace("<br />", "\n")
    plain = plain.replace("<div>", "\n")
    plain = plain.replace("</div>", "")

    # For convenience: Fix mathjax escaping (but only if the html is generated)
    if generated:
        plain = plain.replace(r"\[", r"[")
        plain = plain.replace(r"\]", r"]")
        plain = plain.replace(r"\(", r"(")
        plain = plain.replace(r"\)", r")")

    plain = re.sub(r"\<b\>\s*\<\/b\>", "", plain)

    if not parseable:
        plain = re.sub(r"\*\*(.*?)\*\*", click.style(r"\1", bold=True), plain, re.S)

        plain = re.sub(r"\<b\>(.*?)\<\/b\>", click.style(r"\1", bold=True), plain, re.S)

        plain = re.sub(r"_(.*?)_", _italize(r"\1"), plain, re.S)

        plain = re.sub(r"\<i\>(.*?)\<\/i\>", _italize(r"\1"), plain, re.S)

        plain = re.sub(
            r"\<u\>(.*?)\<\/u\>", click.style(r"\1", underline=True), plain, re.S
        )

    return plain.strip()


def is_generated_html(html: str) -> bool:
    """Check if text is a generated HTML"""
    if html is None:
        return False

    tag = _get_first_tag(BeautifulSoup(html, "html.parser"))

    return (
        tag is not None
        and tag.attrs is not None
        and "data-original-markdown" in tag.attrs
    )


def _get_first_tag(tree: BeautifulSoup) -> Optional[Tag]:
    """Get first tag among children of tree"""
    for child in tree.children:
        if isinstance(child, Tag):
            return child

    return None


def _italize(string: str) -> str:
    """Italize string"""
    return "\x1b[3m" + string + "\x1b[0m"
