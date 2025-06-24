"""Global console instance for CLI output"""

from typing import Any

import click
import readchar
from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt


class ApyConsole(Console):
    """A slightly enriched console for apy"""

    def wait_for_keypress(self) -> None:
        """Wait for keypress to continue."""
        console.print(
            "[white]Press [italic]any key[/italic] to continue ... [/white]", end=""
        )
        _ = readchar.readchar()

    def prompt(self, prompt: str, **kwargs: Any) -> str:
        """Prompt for string."""
        p = Prompt(console=self)
        return p.ask(prompt, **kwargs)

    def prompt_int(self, prompt: str, suffix: str | None = None, **kwargs: Any) -> int:
        """Prompt for integer."""
        result: int

        if suffix is not None:
            result = click.prompt(prompt, prompt_suffix=suffix, type=int)
        else:
            result = IntPrompt(console=self).ask(prompt, **kwargs)

        return result

    def confirm(self, prompt: str, **kwargs: Any) -> bool:
        """Prompt for confirmation"""
        return Confirm(console=self).ask(prompt, **kwargs)


console = ApyConsole()
consolePlain = ApyConsole(highlight=False)
