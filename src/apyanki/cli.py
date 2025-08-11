"""A script to interact with the Anki database"""

import os
import sys
from pathlib import Path
from typing import Any

import click

from apyanki import __version__
from apyanki.anki import Anki
from apyanki.config import cfg, cfg_file
from apyanki.console import console
from apyanki.note import Note
from apyanki.utilities import suppress_stdout

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option("-b", "--base-path", help="Set Anki base directory")
@click.option("-p", "--profile-name", help="Specify name of Anki profile to use")
@click.option("-V", "--version", is_flag=True, help="Show apy version")
@click.pass_context
def main(ctx: Any, base_path: str, profile_name: str, version: bool) -> None:
    """A script to interact with the Anki database.

    The base_path directory may be specified with the -b / --base-path option. For
    convenience, it may also be specified in the config file `~/.config/apy/apy.json`
    or with the environment variable APY_BASE or ANKI_BASE. This should point to the
    base directory where Anki stores its database and related files. See the Anki
    documentation for information about where this is located on different systems
    (https://docs.ankiweb.net/files.html#file-locations).

    A few sub commands will open an editor for input. Vim is used by default.
    The input is parsed when one saves and quits. To abort, one should exit the
    editor with a non-zero exit code. In Vim, one can do this with the `:cquit`
    command.

    One may specify a different editor with the VISUAL or EDITOR environment variable.
    For example, to use emacs one can add this to one's `~/.bashrc` (or similar)
    file:

        export VISUAL=emacs

    Note: Use `apy subcmd --help` to get detailed help for a given subcommand.
    """
    if version:
        console.print(f"apy {__version__}")
        sys.exit()

    if base_path:
        cfg["base_path"] = os.path.abspath(os.path.expanduser(base_path))

    if profile_name:
        cfg["profile_name"] = profile_name

    if ctx.invoked_subcommand is None:
        ctx.invoke(info)


@main.command("add-single")
@click.argument("fields", nargs=-1)
@click.option("-p", "--parse-markdown", is_flag=True, help="Parse input as Markdown.")
@click.option("-s", "--preset", default="default", help="Specify a preset.")
@click.option("-t", "--tags", help="Specify default tags for new cards.")
@click.option(
    "-m", "--model", "model_name", help="Specify default model for new cards."
)
@click.option("-d", "--deck", help="Specify default deck for new cards.")
def add_single(
    fields: list[str],
    parse_markdown: bool,
    tags: str | None = None,
    preset: str | None = None,
    model_name: str | None = None,
    deck: str | None = None,
) -> None:
    """Add a single note from command line arguments.

    Examples:

    \b
        # Add a note to the default deck
        apy add-single myfront myback

    \b
        # Add a cloze deletion note to the default deck
        apy add-single -m Cloze "cloze {{c1::deletion}}" "extra text"

    \b
        # Add a note to deck "MyDeck" with tags 'my-tag' and 'new-tag'
        apy add-single -t "my-tag new-tag" -d MyDeck myfront myback
    """
    with Anki(**cfg) as a:
        tags_preset = " ".join(cfg["presets"][preset]["tags"])
        if not tags:
            tags = tags_preset
        else:
            tags += " " + tags_preset

        if not model_name:
            model_name = cfg["presets"][preset]["model"]

        _ = a.add_notes_single(fields, parse_markdown, tags, model_name, deck)


@main.command()
@click.option("-t", "--tags", default="", help="Specify default tags for new cards.")
@click.option(
    "-m",
    "--model",
    "model_name",
    default="Basic",
    help=("Specify default model for new cards."),
)
@click.option("-d", "--deck", help="Specify default deck for new cards.")
def add(tags: str, model_name: str, deck: str) -> None:
    """Add notes interactively from terminal.

    Examples:

    \b
        # Add notes to deck "MyDeck" with tags 'my-tag' and 'new-tag'
        apy add -t "my-tag new-tag" -d MyDeck

    \b
        # Ask for the model and the deck for each new card
        apy add -m ASK -d ask
    """
    with Anki(**cfg) as a:
        notes = a.add_notes_with_editor(tags, model_name, deck)
        _added_notes_postprocessing(a, notes)


@main.command("update-from-file")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("-t", "--tags", default="", help="Specify default tags for cards.")
@click.option("-d", "--deck", help="Specify default deck for cards.")
@click.option(
    "-u", "--update-file", is_flag=True, help="Update original file with note IDs."
)
def update_from_file(file: Path, tags: str, deck: str, update_file: bool) -> None:
    """Update existing notes or add new notes from Markdown file.

    This command will update existing notes if a note ID (nid) or card ID (cid)
    is provided in the file header, otherwise it will add new notes.

    With the --update-file option, the original file will be updated to include
    note IDs for any new notes added.

    The syntax is similar to add-from-file, but with two additional keys:

    \b
    * nid:      The note ID to update (optional)
    * cid:      The card ID to update (optional, used if nid is not provided)

    If neither nid nor cid is provided, a new note will be created.

    Here is an example Markdown input for updating:

        // example.md
        model: Basic
        tags: marked
        nid: 1619153168151

        # Note 1
        ## Front
        Updated question?

        ## Back
        Updated answer.

        # Note 2
        cid: 1619153168152

        ## Front
        Another updated question?

        ## Back
        Another updated answer.

        # Note 3
        model: Basic

        ## Front
        This will be a new note (no ID provided)

        ## Back
        New note content
    """
    with Anki(**cfg) as a:
        notes = a.update_notes_from_file(str(file), tags, deck, update_file)
        _added_notes_postprocessing(a, notes)


# Create an alias for backward compatibility
@main.command("add-from-file")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("-t", "--tags", default="", help="Specify default tags for new cards.")
@click.option("-d", "--deck", help="Specify default deck for new cards.")
@click.option(
    "-u", "--update-file", is_flag=True, help="Update original file with note IDs."
)
def add_from_file(file: Path, tags: str, deck: str, update_file: bool) -> None:
    """Add notes from Markdown file.

    With the --update-file option, the original file will be updated to include
    note IDs for any new notes added.

    This command is an alias for update-from-file, which can both add new notes
    and update existing ones.
    """
    with Anki(**cfg) as a:
        notes = a.update_notes_from_file(str(file), tags, deck, update_file)
        _added_notes_postprocessing(a, notes)


def _added_notes_postprocessing(a: Anki, notes: list[Note]) -> None:
    """Common postprocessing after 'apy add[-from-file]' or 'apy update-from-file'."""
    n_notes = len(notes)
    if n_notes == 0:
        console.print("No notes added or updated")
        return

    decks = [a.col.decks.name(c.did) for n in notes for c in n.n.cards()]
    n_decks = len(set(decks))
    if n_decks == 0:
        console.print("No notes added or updated")
        return

    # Check if the command is update or add (based on caller function name)
    import inspect

    caller_frame = inspect.currentframe()
    if caller_frame is not None and caller_frame.f_back is not None:
        caller_function = caller_frame.f_back.f_code.co_name
    else:
        caller_function = ""
    is_update = "update" in caller_function.lower()

    action_word = "Updated/added" if is_update else "Added"

    if a.n_decks > 1:
        if n_notes == 1:
            console.print(f"{action_word} note to deck: {decks[0]}")
        elif n_decks > 1:
            console.print(f"{action_word} {n_notes} notes to {n_decks} different decks")
        else:
            console.print(f"{action_word} {n_notes} notes to deck: {decks[0]}")
    else:
        console.print(f"{action_word} {n_notes} notes")

    for note in notes:
        cards = note.n.cards()
        console.print(f"* nid: {note.n.id} (with {len(cards)} cards)")
        for card in note.n.cards():
            console.print(f"  * cid: {card.id}")


@main.command("check-media")
def check_media() -> None:
    """Check media."""
    with Anki(**cfg) as a:
        a.check_media()


@main.command()
def info() -> None:
    """Print some basic statistics."""
    if cfg_file.exists():
        for key in cfg.keys():
            console.print(f"Config loaded:     {key}")
        console.print(f"Config file:       {cfg_file}")
    else:
        console.print("Config file:       Not found")

    with Anki(**cfg) as a:
        scheduler = 3 if a.col.v3_scheduler() else a.col.sched_ver()
        console.print(f"Collection path:   {a.col.path}")
        console.print(f"Scheduler version: {scheduler}")

        if a.col.decks.count() > 1:
            console.print("Decks:")
            for name in sorted(a.deck_names):
                console.print(f"  - {name}")

        sum_notes = a.col.note_count()
        sum_marked = len(a.col.find_notes("tag:marked"))
        sum_cards = a.col.card_count()
        sum_due = len(a.col.find_cards("is:due"))
        sum_new = len(a.col.find_cards("is:new"))
        sum_flagged = len(a.col.find_cards("-flag:0"))
        sum_susp = len(a.col.find_cards("is:suspended"))

        console.print(
            "\n"
            f"{'Model':24s} "
            f"{'notes':>7s} "
            f"{'marked':>7s} "
            f"{'cards':>7s} "
            f"{'due':>7s} "
            f"{'new':>7s} "
            f"{'flagged':>7s}"
            f"{'susp.':>7s} "
        )
        console.rule()
        models = sorted(a.model_names)
        for m in models:
            nnotes = len(set(a.col.find_notes(f'"note:{m}"')))
            if nnotes == 0:
                continue
            nmarked = len(a.col.find_notes(f'"note:{m}" tag:marked'))
            ncards = len(a.col.find_cards(f'"note:{m}"'))
            ndue = len(a.col.find_cards(f'"note:{m}" is:due'))
            nnew = len(a.col.find_cards(f'"note:{m}" is:new'))
            nflagged = len(a.col.find_cards(f'"note:{m}" -flag:0'))
            nsusp = len(a.col.find_cards(f'"note:{m}" is:suspended'))

            name = m[:24]
            console.print(
                f"{name:24s} "
                f"{nnotes:7d} "
                f"{nmarked:7d} "
                f"{ncards:7d} "
                f"{ndue:7d} "
                f"{nnew:7d} "
                f"{nflagged:7d}"
                f"{nsusp:7d} "
            )
        console.rule()
        console.print(
            f"{'Sum':24s} "
            f"{sum_notes:7d} "
            f"{sum_marked:7d} "
            f"{sum_cards:7d} "
            f"{sum_due:7d} "
            f"{sum_new:7d} "
            f"{sum_flagged:7d}"
            f"{sum_susp:7d} "
        )
        console.rule()


@main.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
def model() -> None:
    """Interact with Anki models."""


@model.command("edit-css")
@click.option(
    "-m",
    "--model-name",
    default="Basic",
    help="Specify for which model to edit CSS template.",
)
@click.option("-s", "--sync-after", is_flag=True, help="Perform sync after any change.")
def edit_css(model_name: str, sync_after: bool) -> None:
    """Edit the CSS template for the specified model."""
    with Anki(**cfg) as a:
        a.edit_model_css(model_name)

        if a.modified and sync_after:
            a.sync()
            a.modified = False


@model.command()
@click.argument("old-name")
@click.argument("new-name")
def rename(old_name: str, new_name: str) -> None:
    """Rename model from old_name to new_name."""
    with Anki(**cfg) as a:
        a.rename_model(old_name, new_name)


@main.command("list-cards")
@click.argument("query", required=False, nargs=-1)
@click.option("-v", "--verbose", is_flag=True, help="Print details for each card")
def list_cards(query: str, verbose: bool) -> None:
    """List cards that match QUERY.

    The default QUERY is "tag:marked OR -flag:0". This default can be
    customized in the config file `~/.config/apy/apy.json`, e.g. with

    \b
    {
      "query": "tag:marked OR tag:leech"
    }
    """
    if query:
        query = " ".join(query)
    else:
        query = cfg["query"]

    with Anki(**cfg) as a:
        a.list_cards(query, verbose)


@main.command("list-notes")
@click.argument("query", required=False, nargs=-1)
@click.option("-c", "--show-cards", is_flag=True, help="Print card specs")
@click.option("-r", "--show-raw-fields", is_flag=True, help="Print raw field data")
@click.option("-v", "--verbose", is_flag=True, help="Print note details")
def list_notes(
    query: str, show_cards: bool, show_raw_fields: bool, verbose: bool
) -> None:
    """List notes that match QUERY.

    The default QUERY is "tag:marked OR -flag:0". This default can be
    customized in the config file `~/.config/apy/apy.json`, e.g. with

    \b
    {
      "query": "tag:marked OR tag:leech"
    }
    """
    if query:
        query = " ".join(query)
    else:
        query = cfg["query"]

    with Anki(**cfg) as a:
        a.list_notes(query, show_cards, show_raw_fields, verbose)


@main.command("list-cards-table")
@click.argument("query", required=False, nargs=-1)
@click.option("-a", "--show-answer", is_flag=True, help="Display answer")
@click.option("-m", "--show-model", is_flag=True, help="Display model")
@click.option("-c", "--show-cid", is_flag=True, help="Display card ids")
@click.option("-d", "--show-due", is_flag=True, help="Display card due time in days")
@click.option("-t", "--show-type", is_flag=True, help="Display card type")
@click.option("-e", "--show-ease", is_flag=True, help="Display card ease")
@click.option("-l", "--show-lapses", is_flag=True, help="Display card number of lapses")
def list_cards_table(
    query: str,
    show_answer: bool,
    show_model: bool,
    show_due: bool,
    show_type: bool,
    show_ease: bool,
    show_lapses: bool,
    show_cid: bool,
) -> None:
    """List cards that match QUERY in a tabular format.

    The default QUERY is "tag:marked OR -flag:0". This default can be
    customized in the config file `~/.config/apy/apy.json`, e.g. with

    \b
    {
      "query": "tag:marked OR tag:leech"
    }
    """
    if query:
        query = " ".join(query)
    else:
        query = cfg["query"]

    with Anki(**cfg) as a:
        a.list_cards_as_table(
            query,
            {
                "show_answer": show_answer,
                "show_model": show_model,
                "show_cid": show_cid,
                "show_due": show_due,
                "show_type": show_type,
                "show_ease": show_ease,
                "show_lapses": show_lapses,
            },
        )


@main.command()
@click.argument("query", required=False, nargs=-1)
@click.option(
    "-m",
    "--check-markdown-consistency",
    is_flag=True,
    help="Check for Markdown consistency",
)
@click.option(
    "-n",
    "--cmc-range",
    default=7,
    type=int,
    help="Number of days backwards to check consistency",
)
def review(query: str, check_markdown_consistency: bool, cmc_range: int) -> None:
    """Review/Edit notes that match QUERY.

    The default QUERY is "tag:marked OR -flag:0". This default can be
    customized in the config file `~/.config/apy/apy.json`, e.g. with

    \b
    {
      "query": "tag:marked OR tag:leech"
    }
    """
    if query:
        query = " ".join(query)
    else:
        query = cfg["query"]

    with Anki(**cfg) as a:
        notes = list(a.find_notes(query))

        # Add inconsistent notes
        if check_markdown_consistency:
            notes += [
                n
                for n in a.find_notes(f"rated:{cmc_range}")
                if not n.has_consistent_markdown()
            ]

        i = 0
        number_of_notes = len(notes)
        while i < number_of_notes:
            note = notes[i]
            status = note.review(i, number_of_notes)

            if status == "stop":
                break

            if status == "rewind":
                i = max(i - 1, 0)
            else:
                i += 1


@main.command()
@click.argument("query", nargs=-1, required=True)
@click.option(
    "--force-multiple",
    "-f",
    is_flag=True,
    help="Allow editing multiple notes (will edit them one by one)",
)
def edit(query: str, force_multiple: bool) -> None:
    """Edit notes that match QUERY directly.

    This command allows direct editing of notes matching the provided query
    without navigating through the interactive review interface.

    If the query matches multiple notes, you'll be prompted to confirm
    unless --force-multiple is specified.

    Examples:

    \b
    # Edit a note by its card ID
    apy edit cid:1740342619916

    \b
    # Edit a note by its note ID
    apy edit nid:1234567890123

    \b
    # Edit a note containing specific text
    apy edit "front:error"
    """
    query = " ".join(query)

    with Anki(**cfg) as a:
        notes = list(a.find_notes(query))

        # Handle no matches
        if not notes:
            console.print(f"No notes found matching query: {query}")
            return

        # Handle multiple matches
        if len(notes) > 1 and not force_multiple:
            console.print(f"Query matched {len(notes)} notes. The first five:\n")

            # Show preview of the first 5 matching notes
            for i, note in enumerate(notes[:5]):
                preview_text = note.n.fields[0][:50].replace("\n", " ")
                if len(preview_text) == 50:
                    preview_text += "..."
                console.print(f"{i + 1}. nid:{note.n.id} - {preview_text}")

            console.print(
                "\nHints:\n"
                "* Use 'apy edit --force-multiple' to edit all matches or refine your query so it only matches a single note.\n"
                "* Use 'apy list QUERY' to view all matches."
            )
            return

        # Edit each note
        edited_count = 0
        for i, note in enumerate(notes):
            if len(notes) > 1:
                console.print(
                    f"\nEditing note {i + 1} of {len(notes)} (nid: {note.n.id})"
                )

                # Show a brief preview of the note
                preview_text = note.n.fields[0][:50].replace("\n", " ")
                if len(preview_text) == 50:
                    preview_text += "..."
                console.print(f"Content preview: {preview_text}")
                console.print(f"Tags: {', '.join(note.n.tags)}")

                if not console.confirm("Edit this note?"):
                    console.print("Skipping...")
                    continue

            # Use the direct edit method (bypassing the review interface)
            note.edit()
            edited_count += 1

        # Summary message
        if edited_count > 0:
            console.print(
                f"\n[green]Successfully edited {edited_count} note(s)[/green]"
            )
        else:
            console.print("\n[yellow]No notes were edited[/yellow]")


@main.command()
def sync() -> None:
    """Synchronize collection with AnkiWeb."""
    with Anki(**cfg) as a:
        a.sync()


@main.command()
@click.argument("query", required=False, nargs=-1)
@click.option("-a", "--add-tags", help="Add specified tags to matched notes.")
@click.option("-r", "--remove-tags", help="Remove specified tags from matched notes.")
@click.option(
    "-c", "--sort-by-count", is_flag=True, help="When listing tags, sort by note count"
)
@click.option(
    "-p",
    "--purge",
    is_flag=True,
    help="If specified, then the command will remove all unused tags",
)
def tag(
    query: str,
    add_tags: str | None,
    remove_tags: str | None,
    sort_by_count: bool,
    purge: bool,
) -> None:
    """List all tags or add/remove tags from notes that match the query.

    The default query is "tag:marked OR -flag:0". This default can be
    customized in the config file `~/.config/apy/apy.json`, e.g. with

    \b
    {
      "query": "tag:marked OR tag:leech"
    }

    If none of the options --add-tags, --remove-tags, or --purge are supplied, then the
    command simply lists all tags used in the collection.

    Examples:

    \b
      # List all tags
      apy tag

    \b
      # List all tags but sort by the note count
      apy tag -c

    \b
      # Remove tag "bar" from all notes that match "foo"
      apy tag "foo" --remove-tags bar

    \b
      # Remove all unused tags
      apy tag --purge
    """
    if query:
        query = " ".join(query)
    else:
        query = cfg["query"]

    with Anki(**cfg) as a:
        if purge:
            changes = a.purge_unused_tags()
            if changes.count > 0:
                console.print(f"[yellow]Purged {changes.count} unused tags.")
            else:
                console.print("No unused tags found.")

            return

        if (add_tags is None or add_tags == "") and (
            remove_tags is None or remove_tags == ""
        ):
            a.list_tags(sort_by_count)
            return

        n_notes = len(list(a.find_notes(query)))
        if n_notes == 0:
            console.print("No matching notes!")
            raise click.Abort()

        console.print(f"The operation will be applied to {n_notes} matched notes:")
        a.list_note_questions(query)
        console.print("")

        if add_tags is not None:
            console.print(f"Add tags:    [green]{add_tags}")
        if remove_tags is not None:
            console.print(f"Remove tags: [red]{remove_tags}")

        if not console.confirm("Continue?"):
            raise click.Abort()

        if add_tags is not None:
            a.change_tags(query, add_tags)

        if remove_tags is not None:
            a.change_tags(query, remove_tags, add=False)


@main.command()
@click.argument("position", type=int, required=True, nargs=1)
@click.argument("query", required=True, nargs=-1)
def reposition(position: int, query: str) -> None:
    """Reposition cards that match QUERY.

    Sets the new position to POSITION and shifts other cards.

    Note that repositioning only works with new cards!
    """
    query = " ".join(query)

    with Anki(**cfg) as a:
        cids = list(a.col.find_cards(query))
        if not cids:
            console.print(f"No matching cards for query: {query}!")
            raise click.Abort()

        for cid in cids:
            card = a.col.get_card(cid)
            if card.type != 0:
                console.print("Can only reposition new cards!")
                raise click.Abort()

        _ = a.col.sched.reposition_new_cards(cids, position, 1, False, True)
        a.modified = True


@main.command()
@click.argument(
    "target-file", type=click.Path(exists=False, resolve_path=True, path_type=Path)
)
@click.option(
    "-m", "--include-media", is_flag=True, help="Include media files in backup."
)
@click.option(
    "-l",
    "--legacy",
    is_flag=True,
    help="Support older Anki versions (slower/larger files)",
)
def backup(target_file: Path, include_media: bool, legacy: bool) -> None:
    """Backup Anki database to specified target file."""
    with Anki(**cfg) as a:
        target_filename = str(target_file)

        if not target_filename.endswith(".colpkg"):
            console.print("[yellow]Warning: Target should have .colpkg extension!")
            raise click.Abort()

        if target_file.exists():
            console.print("[yellow]Warning: Target file already exists!")
            console.print(f"[yellow]  {target_file}")
            if not console.confirm("Do you want to overwrite it?"):
                raise click.Abort()

        with suppress_stdout():
            a.col.export_collection_package(target_filename, include_media, legacy)


if __name__ == "__main__":
    main()
