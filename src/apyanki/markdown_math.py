"""Extension to avoid converting markdown within math blocks"""

from __future__ import annotations

import re

from markdown import Markdown
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor

START_MARKER = "\x02"  # start of text
END_MARKER = "\x03"  # end of text


class MathProtectExtension(Extension):
    def __init__(self, markdown_latex_mode: str) -> None:
        super().__init__()
        self.markdown_latex_mode: str = markdown_latex_mode

    def extendMarkdown(
        self, md: Markdown
    ) -> None:  # pyright: ignore[reportImplicitOverride]
        math_preprocessor = MathPreprocessor(md, self.markdown_latex_mode)
        math_postprocessor = MathPostprocessor(md, math_preprocessor.placeholders)

        md.preprocessors.register(math_preprocessor, "math_block_processor", 25)
        md.postprocessors.register(math_postprocessor, "math_block_restorer", 25)


class MathPreprocessor(Preprocessor):
    def __init__(self, md: Markdown, markdown_latex_mode: str) -> None:
        super().__init__(md)
        self.counter: int = 0
        self.placeholders: dict[str, str] = {}

        # Apply latex translation based on specified latex mode
        if markdown_latex_mode == "latex":
            self.fmt_display: str = "[$$]{math}[/$$]"
            self.fmt_inline: str = "[$]{math}[/$]"
        else:
            self.fmt_display = r"\[{math}\]"
            self.fmt_inline = r"\({math}\)"

    def run(
        self, lines: list[str]
    ) -> list[str]:  # pyright: ignore[reportImplicitOverride]
        def replacer(match: re.Match[str]) -> str:
            placeholder = f"{START_MARKER}MATH-PLACEHOLDER-{self.counter}{END_MARKER}"
            self.counter += 1

            if matched := match.group(1):
                self.placeholders[placeholder] = self.fmt_display.format(math=matched)
            elif matched := match.group(2):
                self.placeholders[placeholder] = self.fmt_inline.format(math=matched)

            return placeholder

        pattern = re.compile(r"\$\$(.*?)\$\$|\$(.*?)\$", re.DOTALL)
        lines_joined = "\n".join(lines)
        lines_processed = pattern.sub(replacer, lines_joined)
        return lines_processed.split("\n")


class MathPostprocessor(Postprocessor):
    def __init__(self, md: Markdown, placeholders: dict[str, str]) -> None:
        super().__init__(md)
        self.placeholders: dict[str, str] = placeholders

    def run(self, text: str) -> str:  # pyright: ignore[reportImplicitOverride]
        def replacer(match: re.Match[str]) -> str:
            # NOTE: the default argument `match.group(0)` is provided, in the
            # unlikely case that the user provides input that matches the
            # pattern
            return self.placeholders.get(match.group(0), match.group(0))

        return re.sub(
            rf"{START_MARKER}MATH-PLACEHOLDER-\d+{END_MARKER}",
            replacer,
            text,
        )
