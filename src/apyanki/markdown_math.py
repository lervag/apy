"""Extension to avoid converting markdown within math and LaTeX blocks"""

import html
import re
from typing import override

from markdown import Markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

# Code, raw LaTeX and math in Markdown text. Code is matched first, so that
# e.g. $ inside code is not taken as math. Raw LaTeX blocks are passed to
# Anki's LaTeX renderer, so neither math nor Markdown is processed inside them.
PROTECTED_PATTERN = re.compile(
    r"""
    ^(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^(?P=fence)[ \t]*$
    | (?<!\\)(?P<ticks>`+)(?:(?!\n[ \t]*\n).)+?(?<!`)(?P=ticks)(?!`)
    | (?P<latex>\[latex\].*?\[/latex\])
    | \$\$(?P<display>.*?)\$\$
    | \$(?P<inline>.*?)\$
    """,
    re.DOTALL | re.MULTILINE | re.VERBOSE,
)


class MathProtectExtension(Extension):
    def __init__(self, markdown_latex_mode: str) -> None:
        super().__init__()
        self.markdown_latex_mode: str = markdown_latex_mode

    @override
    def extendMarkdown(self, md: Markdown) -> None:
        md.preprocessors.register(
            MathPreprocessor(md, self.markdown_latex_mode),
            "math_block_processor",
            25,
        )


class MathPreprocessor(Preprocessor):
    """Move math into the HTML stash so markdown leaves it untouched.

    The stashed math is restored by Python-Markdown's own raw HTML
    postprocessor.
    """

    def __init__(self, md: Markdown, markdown_latex_mode: str) -> None:
        super().__init__(md)

        # Apply latex translation based on specified latex mode
        if markdown_latex_mode == "latex":
            self.fmt_display: str = "[$$]{math}[/$$]"
            self.fmt_inline: str = "[$]{math}[/$]"
        else:
            self.fmt_display = r"\[{math}\]"
            self.fmt_inline = r"\({math}\)"

    @override
    def run(self, lines: list[str]) -> list[str]:
        def replacer(match: re.Match[str]) -> str:
            latex, display, inline = match.group("latex", "display", "inline")
            if latex is not None:
                raw = latex
            elif display is not None:
                raw = self.fmt_display.format(math=display)
            elif inline is not None:
                raw = self.fmt_inline.format(math=inline)
            else:
                return match.group(0)
            return self.md.htmlStash.store(html.escape(raw, quote=False))

        lines_joined = "\n".join(lines)
        lines_processed = PROTECTED_PATTERN.sub(replacer, lines_joined)
        return lines_processed.split("\n")
