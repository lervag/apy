"""Extension to avoid converting markdown within math blocks"""

import re
from typing import override

from markdown import Markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor


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

        self.pattern = re.compile(r"\$\$(.*?)\$\$|\$(.*?)\$", re.DOTALL)

    @override
    def run(self, lines: list[str]) -> list[str]:
        def replacer(match: re.Match[str]) -> str:
            display, inline = match.group(1, 2)
            if isinstance(display, str):
                math = self.fmt_display.format(math=display)
            else:
                assert isinstance(inline, str)
                math = self.fmt_inline.format(math=inline)
            return self.md.htmlStash.store(math)

        lines_joined = "\n".join(lines)
        lines_processed = self.pattern.sub(replacer, lines_joined)
        return lines_processed.split("\n")
