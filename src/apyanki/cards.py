"""Utility functions for working with Anki cards"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text

from apyanki.console import console, consolePlain
from apyanki.fields import check_if_generated_from_markdown, prepare_field_for_cli
from apyanki.fields import prepare_field_for_cli_oneline

if TYPE_CHECKING:
    from anki.cards import Card


def card_pprint(card: Card, verbose: bool = True) -> None:
    """Pretty print a card."""
    flag = get_flag(card)
    consolePlain.print(f"[green]# Card (cid: {card.id})[/green]{flag}\n")

    if verbose:
        card_type = ["new", "learning", "review", "relearning"][int(card.type)]
        columned = [
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
        for line in columned:
            consolePlain.print(line)

    rendered = card.render_output()
    for title, field in [
        ["Front", rendered.question_text],
        ["Back", rendered.answer_text],
    ]:
        is_markdown = check_if_generated_from_markdown(field)
        if is_markdown:
            title += " [italic](markdown)[/italic]"

        console.print(f"[blue]## {title}[/blue]\n")
        prepared = prepare_field_for_cli(field)
        prepared = prepared.replace("\n\n", "\n")
        console.print(prepared)
        console.print()


def card_field_to_text(field: str, max_width: int = 0) -> Text:
    prepared_field = prepare_field_for_cli_oneline(field)
    if max_width > 0:
        prepared_field = prepared_field[0:max_width]
    return Text.from_markup(prepared_field)


def print_question(card: Card) -> None:
    """Print the card question"""
    question = Text("Q: ")
    question.stylize("yellow", 0, 2)
    _ = question.append_text(card_field_to_text(card.question()))
    console.print(question.fit(console.width))


def print_answer(card: Card) -> None:
    """Print the card answer"""
    answer = Text("A: ")
    answer.stylize("yellow", 0, 2)
    _ = answer.append_text(card_field_to_text(card.answer()))
    console.print(answer.fit(console.width))


def print_stats(card: Card) -> None:
    """Print the card statistics"""
    cardtype = int(card.type)
    card_type = ["new", "learning", "review", "relearning"][cardtype]

    style = "green"
    console.print(
        Text.assemble(("model: ", style), card.note_type()["name"]),
        Text.assemble(("due: ", style), str(card.due)),
        Text.assemble(("type: ", style), card_type),
        Text.assemble(("ease: ", style), str(card.factor / 10)),
        Text.assemble(("lapses: ", style), str(card.lapses)),
        "\n",
    )


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
