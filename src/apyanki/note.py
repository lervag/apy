"""Classes and functions for interacting with and creating notes"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from subprocess import DEVNULL, Popen
from time import localtime, strftime
from typing import TYPE_CHECKING, Any, Literal

import readchar
from click import Abort
from rich.columns import Columns
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from typing_extensions import override

from apyanki import cards
from apyanki.config import cfg
from apyanki.console import console, consolePlain
from apyanki.fields import (
    check_if_generated_from_markdown,
    check_if_inconsistent_markdown,
    convert_field_to_text,
    convert_text_to_field,
    img_paths_from_field,
    img_paths_from_field_latex,
    prepare_field_for_cli,
    prepare_field_for_cli_raw,
    toggle_field_to_markdown,
)
from apyanki.utilities import cd, choose, edit_file

if TYPE_CHECKING:
    from anki.notes import Note as ANote

    from apyanki.anki import Anki


class Note:
    """A Note wrapper class"""

    def __init__(self, anki: Anki, note: ANote) -> None:
        self.a: Anki = anki
        self.n: ANote = note
        note_type = note.note_type()
        if note_type:
            self.model_name: str = note_type["name"]
        else:
            self.model_name = "__invalid-note__"
        self.field_names: list[str] = list(self.n.keys())
        self.suspended: bool = any(c.queue == -1 for c in self.n.cards())

    @override
    def __repr__(self) -> str:
        """Convert note to Markdown format"""
        lines = [
            "# Note",
            f"model: {self.model_name}",
            f"tags: {self.get_tag_string()}",
            f"nid: {self.n.id}",
        ]

        if self.a.n_decks > 1:
            lines += [f"deck: {self.get_deck()}"]

        if not any(check_if_generated_from_markdown(f) for f in self.n.values()):
            lines += ["markdown: false"]

        lines += [""]

        for name, field in self.n.items():
            lines.append(f"## {name}")
            lines.append(convert_field_to_text(field))
            lines.append("")

        return "\n".join(lines)

    def pprint(
        self, print_raw: bool = False, list_cards: bool = False, verbose: bool = False
    ) -> None:
        """Print to screen"""
        from anki import latex

        header = f"[green]# Note (nid: {self.n.id})[/green]"
        if self.suspended:
            header += " | [red]suspended[/red]"

        tags = self.get_tag_string()
        if "marked" in tags:
            header += " | [blue]marked[/blue]"
        if "leech" in tags:
            header += " | [yellow]leech[/yellow]"

        consolePlain.print(header + "\n")

        if verbose:
            created = strftime("%F %H:%M", localtime(self.n.id / 1000))
            modified = strftime("%F %H:%M", localtime(self.n.mod))
            details = [
                f"[yellow]model:[/yellow] {self.model_name} ({len(self.n.cards())} cards)",
                f"[yellow]tags:[/yellow] {tags}",
                f"[yellow]created:[/yellow] {created}",
                f"[yellow]modified:[/yellow] {modified}",
            ]
            if self.a.n_decks > 1:
                details += ["[yellow]deck:[/yellow] " + self.get_deck()]

            if not list_cards:
                flagged = [
                    cards.get_flag(c, str(c.template()["name"]))
                    for c in self.n.cards()
                    if c.flags > 0
                ]
                if flagged:
                    details += [f"[yellow]flagged:[/yellow] {', '.join(flagged)}"]

            for detail in details:
                consolePlain.print(detail)

        if list_cards:
            self.print_cards()

        if verbose or list_cards:
            console.print()

        imgs: list[Path] = []
        for name, field in self.n.items():
            is_markdown = check_if_generated_from_markdown(field)
            if is_markdown:
                name += " [italic](markdown)[/italic]"

            console.print(f"[blue]## {name}[/blue]")
            if print_raw:
                console.print(Markdown(prepare_field_for_cli_raw(field)))
            else:
                text = prepare_field_for_cli(field, is_markdown)
                if is_markdown:
                    console.print(Markdown(text))
                else:
                    console.print(text)
            console.print("")

            # Render LaTeX if necessary and fill list of LaTeX images
            note_type = self.n.note_type()
            if note_type:
                _ = latex.render_latex(field, note_type, self.a.col)
                imgs += img_paths_from_field_latex(field, note_type, self.a)

        if imgs:
            console.print("[blue]## LaTeX sources[/blue]")
            for line in imgs:
                console.print("- " + str(line))
            console.print("")

    def print_cards(self) -> None:
        """Print list of cards to screen"""
        table = Table(
            show_edge=False,
            padding=(0, 3, 0, 0),
            highlight=True,
            box=None,
            header_style=None,
        )
        table.add_column("Card name", header_style="yellow", no_wrap=True)
        table.add_column("Due", justify="right", header_style="white")
        table.add_column("Interval", justify="right", header_style="white")
        table.add_column("Reps", justify="right", header_style="white")
        table.add_column("Lapses", justify="right", header_style="white")
        table.add_column("Ease", justify="right", header_style="white")
        for card in sorted(self.n.cards(), key=lambda x: x.factor):
            table.add_row(
                "- " + str(card.template()["name"]) + cards.get_flag(card),
                cards.get_due_days(card, self.a.today),
                str(card.ivl),
                str(card.reps),
                str(card.lapses),
                str(card.factor / 10.0),
            )
        console.print(table)

    def show_images(self) -> None:
        """Show in the fields"""
        note_type = self.n.note_type()
        if not note_type:
            return

        images: list[Path] = []
        for html in self.n.values():
            images += img_paths_from_field_latex(html, note_type, self.a)
            images += img_paths_from_field(html)

        with cd(self.a.col.media.dir()):
            for file in images:
                view_cmd = cfg["img_viewers"].get(
                    file.suffix[1:], cfg["img_viewers_default"]
                )
                _ = Popen(view_cmd + [file], stdout=DEVNULL, stderr=DEVNULL)

    def edit(self) -> None:
        """Edit tags and fields of current note"""
        with tempfile.NamedTemporaryFile(
            mode="w+", dir=os.getcwd(), prefix="edit_note_", suffix=".md"
        ) as tf:
            # Write the note content (includes note ID from __repr__)
            _ = tf.write(str(self))
            tf.flush()

            retcode = edit_file(tf.name)
            if retcode != 0:
                console.print(f"[red]Editor return with exit code {retcode}![/red]")
                return

            notes = markdown_file_to_notes(tf.name)

        if not notes:
            console.print("[red]Something went wrong when editing note![/red]")
            return

        # Handle additional notes created during editing
        if len(notes) > 1:
            added_notes = self.a.add_notes_from_list(notes[1:])
            if added_notes:
                console.print(
                    f"[green]Added {len(added_notes)} new notes while editing.[/green]"
                )
                for added_note in added_notes:
                    cards = added_note.n.cards()
                    console.print(f"* nid: {added_note.n.id} (with {len(cards)} cards)")
                console.wait_for_keypress()

        # Update the current note from the first note in the file
        note = notes[0]

        # Update tags if changed
        new_tags = note.tags.split()
        if sorted(new_tags) != sorted(self.n.tags):
            self.n.tags = new_tags

        # Update deck if changed
        if note.deck is not None and note.deck != self.get_deck():
            self.set_deck(note.deck)

        # Update fields if changed
        for i, text in enumerate(note.fields.values()):
            new_field = convert_text_to_field(text, note.markdown)
            if new_field != self.n.fields[i]:
                self.n.fields[i] = new_field

        # Save changes
        _ = self.a.col.update_note(self.n)
        self.a.modified = True

        # Check for duplication issues
        if self.n.dupeOrEmpty():
            console.print("[red]Warning: The updated note is now a dupe![/red]")
            console.wait_for_keypress()

    def delete(self) -> None:
        """Delete the note"""
        self.a.delete_notes(self.n.id)

    def has_consistent_markdown(self) -> bool:
        """Check if markdown fields are consistent with html values"""
        return any(check_if_inconsistent_markdown(f) for f in self.n.values())

    def change_model(self) -> Note | None:
        """Change the note type"""
        console.clear()
        console.print("[red]Warning![/red]")
        console.print(
            "The note type is changed by creating a new note with the selected "
            "type and then deleting the old note. This means that the review "
            "progress is lost!"
        )
        if not console.confirm("\nContinue?"):
            return None

        models = sorted(self.a.model_names)
        while True:
            console.clear()
            console.print("Please choose new model:")
            for n, m in enumerate(models):
                console.print(f"  {n + 1}: {m}")
            index: int = console.prompt_int(">>> ", suffix="") - 1
            try:
                new_model = models[index]
                _ = self.a.set_model(new_model)
                model = self.a.get_model(new_model)
                if not model:
                    continue
            except IndexError:
                continue

            break

        fields: dict[str, str] = {}
        first_field: str = model["flds"][0]["name"]
        for field in model["flds"]:
            fields[field["name"]] = ""

        fields[first_field] = f"Created from Note {self.n.id}\n"
        for old_field_name, old_field in self.n.items():
            text = convert_field_to_text(old_field)
            fields[first_field] += f"\n### {old_field_name}\n{text}\n"

        if model["name"] == "Cloze":
            fields[first_field] += "\nCloze card needs clozes: {{c1::content}}"

        note_data = NoteData(
            model["name"],
            " ".join(self.n.tags),
            fields,
            any(check_if_generated_from_markdown(f) for f in self.n.values()),
            deck=self.get_deck(),
        )

        new_note = note_data.add_to_collection(self.a)
        new_note.edit()
        self.a.delete_notes(self.n.id)

        return new_note

    def toggle_marked(self) -> None:
        """Toggle marked tag for note"""
        if "marked" in self.n.tags:
            self.n.remove_tag("marked")
        else:
            self.n.add_tag("marked")
        self.n.flush()
        self.a.modified = True

    def toggle_leech(self) -> None:
        """Toggle leech tag for note"""
        if "leech" in self.n.tags:
            self.n.remove_tag("leech")
        else:
            self.n.add_tag("leech")
        self.n.flush()
        self.a.modified = True

    def toggle_suspend(self) -> None:
        """Toggle suspend for note"""
        cids = [c.id for c in self.n.cards()]

        if self.suspended:
            _ = self.a.col.sched.unsuspendCards(cids)
        else:
            _ = self.a.col.sched.suspendCards(cids)

        self.suspended = not self.suspended
        self.a.modified = True

    def toggle_markdown(self, index: int | None = None) -> None:
        """Toggle markdown on a field"""
        if index is None:
            field_name = choose(self.field_names, "Toggle markdown for field:")
            index = self.field_names.index(field_name)

        self.n.fields[index] = toggle_field_to_markdown(self.n.fields[index])
        self.n.flush()
        self.a.modified = True

    def clear_flags(self) -> None:
        """Clear flags for note"""
        for c in self.n.cards():
            if c.flags > 0:
                c.flags = 0
                c.flush()
                self.a.modified = True

    def reset_progress(self) -> None:
        """Reset progress for a card"""
        card_list = {c.template()["name"]: c for c in self.n.cards()}
        if len(card_list) <= 1:
            card_name = next(iter(card_list))
        else:
            card_name = choose(list(card_list.keys()), "Select card to reset:")

        card = card_list[card_name]
        console.print("\n[magenta]Resetting progress for card:")
        cards.card_pprint(card)
        if not console.confirm("[red bold]Are you sure?"):
            return

        _ = self.a.col.sched.schedule_cards_as_new(
            [card.id], restore_position=True, reset_counts=True
        )
        self.a.modified = True
        console.print("[magenta]The progress was reset.")
        console.wait_for_keypress()

    def get_deck(self) -> str:
        """Return which deck the note belongs to"""
        return self.a.col.decks.name(self.n.cards()[0].did)

    def set_deck(self, deck: str) -> None:
        """Move note to deck"""
        newdid = self.a.col.decks.id(deck)
        cids = [c.id for c in self.n.cards()]

        if cids and newdid:
            _ = self.a.col.set_deck(cids, newdid)
            self.a.modified = True

    def set_deck_interactive(self) -> None:
        """Move note to deck, interactive"""
        console.clear()
        console.print("[white]Available decks:")
        for d in self.a.col.decks.all_names_and_ids(include_filtered=False):
            console.print(f"* {d.name}")
        console.print("* OTHER -> create new deck")

        try:
            newdeck = console.prompt("[white]Specify target deck")
        except Abort:
            return

        self.set_deck(newdeck)

    def get_tag_string(self) -> str:
        """Get tag string"""
        return ", ".join(self.n.tags)

    def review(
        self,
        i: int | None = None,
        number_of_notes: int | None = None,
        remove_actions: list[str] | None = None,
    ) -> Literal["stop", "continue", "rewind"]:
        """Interactive review of the note

        This method is used by the review command.

        if the arguments "i" and "number_of_notes" are supplied, then they are
        displayed to show review progress.

        The "remove_actions" argument can be used to remove a default action
        from the action menu.
        """

        actions = {
            "c": "Continue",
            "p": "Go back",
            "s": "Save and stop",
            "x": "Save and stop",
            "e": "Edit",
            "a": "Add new",
            "d": "Delete",
            "m": "Toggle markdown",
            "*": "Toggle marked",
            "l": "Toggle leech",
            "z": "Toggle suspend",
            "P": "Toggle pprint",
            "F": "Clear flags",
            "R": "Reset progress",
            "f": "Show images",
            "E": "Edit CSS",
            "D": "Change deck",
            "N": "Change model",
            "v": "Show cards",
            "V": "Show details",
        }

        if remove_actions:
            actions = {
                key: val for key, val in actions.items() if val not in remove_actions
            }

        note_number_string = ""
        if i is not None:
            if number_of_notes:
                note_number_string = f" {i + 1} of {number_of_notes}"
            else:
                note_number_string = f" {i + 1}"

        menu = Columns(
            [
                f"[blue]{key}[/blue]: {value}"
                for key, value in actions.items()
                if key != "x"
            ],
            padding=(0, 2),
            title=Text(
                f"Reviewing note{note_number_string}",
                justify="left",
                style="white",
            ),
        )

        print_raw_fields = False
        verbose = cfg["review_verbose"]
        show_cards = cfg["review_show_cards"]
        refresh = True
        while True:
            if refresh:
                console.clear()
                console.print(menu)
                console.print("")
                self.pprint(print_raw_fields, list_cards=show_cards, verbose=verbose)

            refresh = True
            choice = readchar.readchar()
            action = actions.get(choice)

            if action == "Continue":
                return "continue"

            if action == "Go back":
                return "rewind"

            if action == "Edit":
                self.edit()
                continue

            if action == "Add new":
                notes = self.a.add_notes_with_editor(
                    tags=self.get_tag_string(),
                    model_name=self.model_name,
                    template=self,
                )

                console.print(f"Added {len(notes)} notes")
                console.wait_for_keypress()
                continue

            if action == "Delete" and console.confirm(
                "Are you sure you want to delete the note?"
            ):
                self.delete()
                return "continue"

            if action == "Toggle markdown":
                self.toggle_markdown()
                continue

            if action == "Toggle marked":
                self.toggle_marked()
                continue

            if action == "Toggle leech":
                self.toggle_leech()
                continue

            if action == "Toggle suspend":
                self.toggle_suspend()
                continue

            if action == "Toggle pprint":
                print_raw_fields = not print_raw_fields
                continue

            if action == "Clear flags":
                self.clear_flags()
                continue

            if action == "Reset progress":
                self.reset_progress()
                continue

            if action == "Show images":
                self.show_images()
                refresh = False
                continue

            if action == "Edit CSS":
                self.a.edit_model_css(self.model_name)
                continue

            if action == "Change deck":
                self.set_deck_interactive()
                continue

            if action == "Change model":
                new_note = self.change_model()
                if new_note is not None:
                    return new_note.review(i, number_of_notes)
                continue

            if action == "Save and stop":
                console.print("Stopped")
                return "stop"

            if action == "Show cards":
                show_cards = not show_cards
                cfg["review_show_cards"] = show_cards
                continue

            if action == "Show details":
                verbose = not verbose
                cfg["review_verbose"] = verbose
                continue


@dataclass
class NoteData:
    """Dataclass to contain data for a single note"""

    model: str
    tags: str
    fields: dict[str, str]
    markdown: bool = True
    deck: str | None = None
    nid: str | None = None
    cid: str | None = None

    def add_to_collection(self, anki: Anki) -> Note:
        """Add note to collection

        Returns: The new note
        """
        model = anki.set_model(self.model)
        model_field_names: list[str] = [field["name"] for field in model["flds"]]
        if len(model_field_names) != len(self.fields):
            console.print(f"Error: Not enough fields for model {self.model}!")
            anki.modified = False
            raise Abort()

        field_names = [x.replace(" (markdown)", "") for x in self.fields.keys()]
        for x, y in zip(model_field_names, field_names):
            if x != y:
                console.print(f"Warning: Inconsistent field names ({x} != {y})")

        notetype = anki.col.models.current(for_deck=False)
        new_note = anki.col.new_note(notetype)

        note_type = new_note.note_type()
        if self.deck is not None and note_type is not None:
            note_type["did"] = anki.deck_name_to_id[self.deck]

        new_note.fields = [
            convert_text_to_field(f, self.markdown) for f in self.fields.values()
        ]

        for tag in self.tags.strip().split():
            new_note.add_tag(tag)

        if not new_note.duplicate_or_empty():
            _ = anki.col.addNote(new_note)
            anki.modified = True
        else:
            field_name, field_value = list(self.fields.items())[0]
            console.print("[red]Dupe detected, new_note was not added!")
            console.print(f"First field: {field_name}")
            console.print(f"First value: {field_value}")

        return Note(anki, new_note)

    def update_or_add_to_collection(self, anki: Anki) -> Note:
        """Update existing note in collection if ID is provided, otherwise add as new

        Returns: The updated or new note
        """
        # First try to find the note by nid or cid
        existing_note = None

        if self.nid:
            # Try to find the note by its note ID
            try:
                # Import NoteId here to avoid circular imports at module level
                from anki.notes import NoteId

                note_id = NoteId(int(self.nid))
                existing_note = anki.col.get_note(note_id)
                return self._update_note(anki, existing_note)
            except (ValueError, TypeError):
                console.print(
                    f"[yellow]Invalid note ID format: {self.nid}. Will create a new note.[/yellow]"
                )
            except Exception as e:
                console.print(
                    f"[yellow]Note with ID {self.nid} not found: {e}. Will create a new note.[/yellow]"
                )

        if not existing_note and self.cid:
            # Try to find the note by card ID
            try:
                # Import CardId here to avoid circular imports at module level
                from anki.cards import CardId

                card_id = CardId(int(self.cid))
                card = anki.col.get_card(card_id)
                if card:
                    existing_note = card.note()
                    return self._update_note(anki, existing_note)
            except (ValueError, TypeError):
                console.print(
                    f"[yellow]Invalid card ID format: {self.cid}. Will create a new note.[/yellow]"
                )
            except Exception as e:
                console.print(
                    f"[yellow]Card with ID {self.cid} not found: {e}. Will create a new note.[/yellow]"
                )

        # If no existing note found or ID not provided, add as new
        return self.add_to_collection(anki)

    def _update_note(self, anki: Anki, existing_note: Any) -> Note:
        """Update an existing note with new field values

        Returns: The updated note
        """
        # Verify model match
        note_type = existing_note.note_type()
        if note_type and note_type["name"] != self.model:
            console.print(
                f"[yellow]Warning: Model mismatch. File specifies '{self.model}', note has '{note_type['name']}'.[/yellow]"
            )
            if not console.confirm("Continue with update anyway?"):
                console.print(
                    "[yellow]Update canceled. Adding as new note instead.[/yellow]"
                )
                return self.add_to_collection(anki)

        # Update tags
        existing_note.tags = self.tags.strip().split()

        # Update deck if specified
        if self.deck is not None:
            try:
                # Get first card and update its deck
                cards = existing_note.cards()
                if cards:
                    # Explicitly cast to int to satisfy mypy
                    deck_id = anki.deck_name_to_id.get(self.deck, None)
                    if deck_id is not None:  # Make sure deck_id exists and is not None
                        card_ids = [c.id for c in cards]
                        _ = anki.col.set_deck(card_ids, deck_id)
            except Exception as e:
                console.print(f"[yellow]Failed to update deck: {e}[/yellow]")

        # Update fields
        field_names = list(existing_note.keys())
        for i, field_name in enumerate(field_names):
            # Match field names from the file to the existing note
            matching_field = None
            for file_field_name, content in self.fields.items():
                clean_name = file_field_name.replace(" (markdown)", "")
                if clean_name.lower() == field_name.lower():
                    matching_field = content
                    break

            if matching_field is not None:
                existing_note.fields[i] = convert_text_to_field(
                    matching_field,
                    self.markdown,
                )

        # Save the updated note
        _ = anki.col.update_note(existing_note)
        anki.modified = True

        return Note(anki, existing_note)


def markdown_file_to_notes(filename: str) -> list[NoteData]:
    """Parse note data from a Markdown file"""
    try:
        notes = [
            NoteData(
                model=x["model"],
                tags=x["tags"],
                fields=x["fields"],
                markdown=x["markdown"],
                deck=x["deck"],
                nid=x["nid"],
                cid=x["cid"],
            )
            for x in _parse_markdown_file(filename)
        ]
    except KeyError as e:
        console.print(f"Error {e.__class__} when parsing {filename}!")
        console.print("This may typically be due to bad Markdown formatting.")
        raise Abort() from e

    return notes


def _parse_markdown_file(filename: str) -> list[dict[str, Any]]:
    """Parse the content of a Markdown file

    This must adhere to the specification of {add_from_file} from cli.py!
    """
    defaults: dict[str, Any] = {
        "model": "Basic",
        "markdown": True,
        "tags": "",
        "deck": None,
        "nid": None,
        "cid": None,
    }
    with open(filename, "r", encoding="utf8") as f:
        for line in f:
            match = re.match(r"#+\s*.*", line)
            if match:
                break

            match = re.match(r"(\w+): (.*)", line)
            if match:
                k, v = match.groups()
                k = k.lower()
                v = v.strip()
                if k in ("tag", "tags"):
                    defaults["tags"] = v.replace(",", "")
                elif k in ("markdown", "md"):
                    defaults["markdown"] = v in ("true", "yes")
                elif k == "nid":
                    defaults["nid"] = v
                elif k == "cid":
                    defaults["cid"] = v
                else:
                    defaults[k] = v

    notes: list[dict[str, Any]] = []
    current_note: dict[str, Any] = {}
    current_field: str | None = None
    is_in_codeblock = False
    with open(filename, "r", encoding="utf8") as f:
        for line in f:
            if is_in_codeblock:
                if current_field is not None:
                    current_note["fields"][current_field] += line
                match = re.match(r"```\s*$", line)
                if match:
                    is_in_codeblock = False
                continue

            match = re.match(r"```\w*\s*$", line)
            if match:
                is_in_codeblock = True
                if current_field is not None:
                    current_note["fields"][current_field] += line
                continue

            if current_note and current_field is None:
                match = re.match(r"(\w+): (.*)", line)
                if match:
                    k, v = match.groups()
                    k = k.lower()
                    v = v.strip()
                    if k in ("tag", "tags"):
                        # Merge global tags with note-specific tags
                        current_tags = current_note.get("tags", "").strip()
                        if current_tags:
                            current_note["tags"] = (
                                f"{current_tags} {v.replace(',', '')}"
                            )
                        else:
                            current_note["tags"] = v.replace(",", "")
                    elif k in ("markdown", "md"):
                        current_note["markdown"] = v in ("true", "yes")
                    else:
                        current_note[k] = v

            match = re.match(r"(#+)\s*(.*)", line)
            if not match:
                if current_field is not None:
                    current_note["fields"][current_field] += line
                continue

            level, title = match.groups()

            if len(level) == 1:
                if current_note and current_field is not None:
                    current_note["fields"][current_field] = current_note["fields"][
                        current_field
                    ].strip()
                    notes.append(current_note)

                current_note = {"title": title, "fields": {}, **defaults}
                current_field = None
                continue

            if len(level) == 2:
                if current_field is not None:
                    current_note["fields"][current_field] = current_note["fields"][
                        current_field
                    ].strip()

                if title in current_note["fields"]:
                    console.print(f"Error when parsing {filename}!")
                    raise Abort()

                current_field = title
                current_note["fields"][current_field] = ""

    # Add remaining note to list
    if current_note and current_field is not None:
        current_note["fields"][current_field] = current_note["fields"][
            current_field
        ].strip()
        notes.append(current_note)

    return notes
