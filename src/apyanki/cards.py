"""Utility functions for working with Anki cards"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rich.markdown import Markdown
from rich.text import Text

from markdownify import markdownify as to_md

from apyanki.console import console, consolePlain

if TYPE_CHECKING:
    from anki.cards import Card


def card_pprint(card: Card, verbose: bool = True) -> None:
    """Pretty print a card."""
    flag = get_flag(card)
    consolePlain.print(f"[green]# Card (cid: {card.id})[/green]{flag}\n")

    if verbose:
        card_type = ["new", "learning", "review", "relearning"][int(card.type)]
        details = [
            f"[yellow]nid:[/yellow] {card.nid}",
            f"[yellow]model:[/yellow] {card.note_type()['name']}",
            f"[yellow]type:[/yellow] {card_type}",
            f"[yellow]due:[/yellow] {card.due} days",
            f"[yellow]interval:[/yellow] {card.ivl} days",
            f"[yellow]repetitions:[/yellow] {card.reps}",
            f"[yellow]lapses:[/yellow] {card.lapses}",
            f"[yellow]ease:[/yellow] {int(card.factor / 10)} %",
            "",
        ]
        for detail in details:
            consolePlain.print(detail)

    question, answer = card_fields_as_md(card)
    for title, field in [
        ["Front", question],
        ["Back", answer],
    ]:
        console.print(f"[blue]## {title}[/blue]\n")
        console.print(Markdown(field))
        console.print()


def card_fields_as_md(
    card: Card, one_line: bool = False, max_width: int = 0
) -> tuple[str, str]:
    rendered = card.render_output()

    return (
        _field_to_md(rendered.question_text, one_line, max_width),
        _field_to_md(rendered.answer_text, one_line, max_width),
    )


def _field_to_md(field: str, one_line: bool = False, max_width: int = 0) -> str:
    prepared_field: str = to_md(field)

    if one_line:
        prepared_field = prepared_field.replace("\n", " ")
        prepared_field = re.sub(r"\s\s+", " ", prepared_field)

    if max_width > 0:
        prepared_field = prepared_field[0:max_width]

    return prepared_field


def print_question(card: Card) -> None:
    """Print the card question"""
    question, _ = card_fields_as_md(card)

    output = Text("Q: ")
    output.stylize("yellow", 0, 2)
    _ = output.append_text(Text.from_markup(question))
    console.print(output.fit(console.width))


def print_answer(card: Card) -> None:
    """Print the card answer"""
    _, answer = card_fields_as_md(card)

    output = Text("Q: ")
    output.stylize("yellow", 0, 2)
    _ = output.append_text(Text.from_markup(answer))
    console.print(output.fit(console.width))


def get_flag(card: Card, text: str = "  ") -> str:
    """Get rich formatted flag of card"""
    style = {
        1: "red",
        2: "orange",
        3: "green",
        4: "blue",
        5: "pink1",
        6: "medium_turquoise",
        7: "purple",
    }.get(card.flags)

    if style:
        return f"[{style}]{text}[/{style}]"

    return ""


def get_due_days(card: Card, today: int) -> str:
    """Get number of days until card is due"""
    if card.type < 2:
        return "0"

    if card.type == 2:
        return str(card.due - today)

    return "?"
