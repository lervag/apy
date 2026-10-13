"""Extension to avoid converting markdown within math blocks"""

import re
from typing import override

from markdown import Markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

# Code and math in Markdown text. Code is matched first, so that $ inside
# code is not taken as math. Only the "display" and "inline" groups are math.
MATH_OR_CODE_PATTERN = re.compile(
    r"""
    ^(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^(?P=fence)[ \t]*$   # fenced code block
    | (?<!\\)(?P<ticks>`+)(?:(?!\n[ \t]*\n).)+?(?<!`)(?P=ticks)(?!`)
                                                         # inline code span
    | \$\$(?P<display>.*?)\$\$                             # display math
    | \$(?P<inline>.*?)\$                                  # inline math
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
            display, inline = match.group("display", "inline")
            if display is not None:
                math = self.fmt_display.format(math=display)
            elif inline is not None:
                math = self.fmt_inline.format(math=inline)
            else:
                return match.group(0)
            return self.md.htmlStash.store(math)

        lines_joined = "\n".join(lines)
        lines_processed = MATH_OR_CODE_PATTERN.sub(replacer, lines_joined)
        return lines_processed.split("\n")
