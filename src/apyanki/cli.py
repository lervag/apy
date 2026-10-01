"""A script to interact with the Anki database"""

import os
from pathlib import Path
from typing import Annotated, Literal, override

import typer
from typer.core import TyperGroup

from apyanki import __version__
from apyanki.anki import Anki
from apyanki.config import cfg, cfg_file
from apyanki.console import console
from apyanki.note import Note
from apyanki.utilities import suppress_stdout

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


class SortedGroup(TyperGroup):
    """List subcommands alphabetically in the help output"""

    @override
    def list_commands(self, ctx: object) -> list[str]:
        return sorted(self.commands)


main = typer.Typer(
    cls=SortedGroup,
    context_settings=CONTEXT_SETTINGS,
    rich_markup_mode=None,
    add_completion=False,
    pretty_exceptions_enable=False,
)

QueryArgument = Annotated[list[str] | None, typer.Argument(metavar="[QUERY]...")]
RequiredQueryArgument = Annotated[list[str], typer.Argument(metavar="QUERY...")]


@main.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    base_path: Annotated[
        str | None,
        typer.Option("-b", "--base-path", help="Set Anki base directory"),
    ] = None,
    profile_name: Annotated[
        str | None,
        typer.Option(
            "-p",
            "--profile-name",
            help="Specify name of Anki profile to use",
        ),
    ] = None,
    version: Annotated[
        bool,
        typer.Option("-V", "--version", help="Show apy version"),
    ] = False,
) -> None:
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
        raise typer.Exit()

    if base_path:
        cfg["base_path"] = os.path.abspath(os.path.expanduser(base_path))

    if profile_name:
        cfg["profile_name"] = profile_name

    if ctx.invoked_subcommand is None:
        info()


@main.command("add-single")
def add_single(
    fields: Annotated[list[str] | None, typer.Argument(metavar="[FIELDS]...")] = None,
    parse_markdown: Annotated[
        bool,
        typer.Option("-p", "--parse-markdown", help="Parse input as Markdown."),
    ] = False,
    preset: Annotated[
        str, typer.Option("-s", "--preset", help="Specify a preset.")
    ] = "default",
    tags: Annotated[
        str | None,
        typer.Option("-t", "--tags", help="Specify default tags for new cards."),
    ] = None,
    model_name: Annotated[
        str | None,
        typer.Option("-m", "--model", help="Specify default model for new cards."),
    ] = None,
    deck: Annotated[
        str | None,
        typer.Option("-d", "--deck", help="Specify default deck for new cards."),
    ] = None,
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
        tags_preset: str = " ".join(cfg["presets"][preset]["tags"])
        if not tags:
            tags = tags_preset
        else:
            tags += " " + tags_preset

        if not model_name:
            model_name = cfg["presets"][preset]["model"]

        _ = a.add_notes_single(fields or [], parse_markdown, tags, model_name, deck)


@main.command()
def add(
    tags: Annotated[
        str,
        typer.Option("-t", "--tags", help="Specify default tags for new cards."),
    ] = "",
    model_name: Annotated[
        str,
        typer.Option("-m", "--model", help="Specify default model for new cards."),
    ] = "Basic",
    deck: Annotated[
        str | None,
        typer.Option("-d", "--deck", help="Specify default deck for new cards."),
    ] = None,
) -> None:
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
        _added_notes_postprocessing(a, notes, "Added")


@main.command("update-from-file")
def update_from_file(
    file: Annotated[Path, typer.Argument(metavar="FILE", exists=True, dir_okay=False)],
    tags: Annotated[
        str,
        typer.Option("-t", "--tags", help="Specify default tags for cards."),
    ] = "",
    deck: Annotated[
        str | None,
        typer.Option("-d", "--deck", help="Specify default deck for cards."),
    ] = None,
    link_duplicates: Annotated[
        bool,
        typer.Option(
            "-l",
            "--link-duplicates",
            help="Link duplicates to existing notes in IDs file.",
        ),
    ] = False,
) -> None:
    """Update existing notes or add new notes from Markdown file.

    This command will update existing notes when a note ID (nid) is available.
    There are two modes:

      * External IDs: Each note has a unique `id` key in the note header, and
        the `nid` is found in an external JSON file. When adding new cards, the
        Markdown file will be updated to add missing `id`, and the external ID
        file will be updated accordingly with the corresponding `nid` values.
      * Internal IDs: Each note has a `nid` key in the note header. When adding
        new notes, the Markdown file will be updated with the added `nid` value
        for the new cards.

    INTERNAL IDS MODE

    Here is an example of an internal ID Markdown input:

        // example.md
        model: Basic
        tags: marked

        # Note 1
        nid: 1619153168151

        ## Front
        Updated question?

        ## Back
        Updated answer.

        # Note 2
        nid: 1619153168152

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

    EXTERNAL IDS MODE

    For collaborative workflows (e.g., sharing markdown files via Git), you can
    store note IDs in a separate external JSON file instead of in the Markdown
    file itself.

    To activate external IDs mode, add an 'external-ids:' header at the top of
    the markdown file pointing to the JSON file:

        // notes.md
        external-ids: .anki-ids.json

        # Note 1
        id: note1

        ## Front
        Question 1

        ## Back
        Answer 1

        # Note 2
        id: note2

        ## Front
        Question 2

        ## Back
        Answer 2

    The external IDs file (e.g., .anki-ids.json) maps user-defined IDs to Anki
    note IDs:

        {
            "note1": "1619153168151",
            "note2": "1619153168152"
        }
    """
    with Anki(**cfg) as a:
        notes = a.add_notes_from_file(
            str(file),
            tags,
            deck,
            update_origin_file=True,
            respect_note_ids=True,
            link_duplicates=link_duplicates,
        )
        _added_notes_postprocessing(a, notes, "Updated/added")


# Create an alias for backward compatibility
@main.command("add-from-file")
def add_from_file(
    file: Annotated[Path, typer.Argument(metavar="FILE", exists=True, dir_okay=False)],
    tags: Annotated[
        str,
        typer.Option("-t", "--tags", help="Specify default tags for new cards."),
    ] = "",
    deck: Annotated[
        str | None,
        typer.Option("-d", "--deck", help="Specify default deck for new cards."),
    ] = None,
) -> None:
    """Add new notes from Markdown file.

    This command will add new notes to the collection. Unlike update-from-file,
    it will not update existing notes based on IDs - all notes are treated as new.
    The file (or external IDs file when using external-ids mode) will NOT be
    updated with note IDs.

    This command is useful for importing notes without modifying the source file.

    Here is an example Markdown input for adding notes:

        // example.md
        model: Basic
        tags: marked

        # Note 1
        nid: 1619153168151    <-  NB! This is IGNORED!

        ## Front
        Updated question?

        ## Back
        Updated answer.

        # Note 2

        ## Front
        Another updated question?

        ## Back
        Another updated answer.

        # Note 3
        model: Basic
        tags: newtag

        ## Front
        This will be a new note (no ID provided)

        ## Back
        New note content
    """
    with Anki(**cfg) as a:
        notes = a.add_notes_from_file(str(file), tags, deck)
        _added_notes_postprocessing(a, notes, "Added")


def _added_notes_postprocessing(
    a: Anki,
    notes: list[Note],
    action_word: Literal["Updated/added", "Added"],
) -> None:
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
        if (n := len(cards)) == 1:
            console.print(f"* nid: {note.n.id} / cid: {cards[0].id}")
        else:
            console.print(f"* nid: {note.n.id} / with {n} cards:")
            for card in cards:
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
        for key in cfg:
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


model = typer.Typer(
    cls=SortedGroup,
    context_settings=CONTEXT_SETTINGS,
    rich_markup_mode=None,
    add_completion=False,
    pretty_exceptions_enable=False,
)
main.add_typer(model, name="model")


@model.callback(invoke_without_command=True)
def model_callback() -> None:
    """Interact with Anki models."""


@model.command("edit-css")
def edit_css(
    model_name: Annotated[
        str,
        typer.Option(
            "-m",
            "--model-name",
            help="Specify for which model to edit CSS template.",
        ),
    ] = "Basic",
    sync_after: Annotated[
        bool,
        typer.Option("-s", "--sync-after", help="Perform sync after any change."),
    ] = False,
) -> None:
    """Edit the CSS template for the specified model."""
    with Anki(**cfg) as a:
        a.edit_model_css(model_name)

        if a.modified and sync_after:
            a.sync()
            a.modified = False


@model.command()
def rename(
    old_name: Annotated[str, typer.Argument(metavar="OLD_NAME")],
    new_name: Annotated[str, typer.Argument(metavar="NEW_NAME")],
) -> None:
    """Rename model from old_name to new_name."""
    with Anki(**cfg) as a:
        a.rename_model(old_name, new_name)


@main.command("list-cards")
def list_cards(
    query: QueryArgument = None,
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Print details for each card"),
    ] = False,
) -> None:
    """List cards that match QUERY.

    The default QUERY is "tag:marked OR -flag:0". This default can be
    customized in the config file `~/.config/apy/apy.json`, e.g. with

    \b
    {
      "query": "tag:marked OR tag:leech"
    }
    """
    query_str = " ".join(query) if query else cfg["query"]

    with Anki(**cfg) as a:
        a.list_cards(query_str, verbose)


@main.command("list-cards-table")
def list_cards_table(
    query: QueryArgument = None,
    show_answer: Annotated[
        bool,
        typer.Option("-a", "--show-answer", help="Display answer"),
    ] = False,
    show_model: Annotated[
        bool,
        typer.Option("-m", "--show-model", help="Display model"),
    ] = False,
    show_cid: Annotated[
        bool,
        typer.Option("-c", "--show-cid", help="Display card ids"),
    ] = False,
    show_due: Annotated[
        bool,
        typer.Option("-d", "--show-due", help="Display card due time in days"),
    ] = False,
    show_type: Annotated[
        bool,
        typer.Option("-t", "--show-type", help="Display card type"),
    ] = False,
    show_ease: Annotated[
        bool,
        typer.Option("-e", "--show-ease", help="Display card ease"),
    ] = False,
    show_lapses: Annotated[
        bool,
        typer.Option("-l", "--show-lapses", help="Display card number of lapses"),
    ] = False,
    show_deck: Annotated[
        bool,
        typer.Option("-D", "--show-deck", help="Display deck"),
    ] = False,
) -> None:
    """List cards that match QUERY in a tabular format.

    The default QUERY is "tag:marked OR -flag:0". This default can be
    customized in the config file `~/.config/apy/apy.json`, e.g. with

    \b
    {
      "query": "tag:marked OR tag:leech"
    }
    """
    query_str = " ".join(query) if query else cfg["query"]

    with Anki(**cfg) as a:
        a.list_cards_as_table(
            query_str,
            {
                "show_answer": show_answer,
                "show_model": show_model,
                "show_cid": show_cid,
                "show_due": show_due,
                "show_type": show_type,
                "show_ease": show_ease,
                "show_lapses": show_lapses,
                "show_deck": show_deck,
            },
        )


@main.command("list-models")
def list_models() -> None:
    """List available models."""
    with Anki(**cfg) as a:
        a.list_models()


@main.command("list-notes")
def list_notes(
    query: QueryArgument = None,
    show_cards: Annotated[
        bool,
        typer.Option("-c", "--show-cards", help="Print card specs"),
    ] = False,
    show_raw_fields: Annotated[
        bool,
        typer.Option("-r", "--show-raw-fields", help="Print raw field data"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Print note details"),
    ] = False,
) -> None:
    """List notes that match QUERY.

    The default QUERY is "tag:marked OR -flag:0". This default can be
    customized in the config file `~/.config/apy/apy.json`, e.g. with

    \b
    {
      "query": "tag:marked OR tag:leech"
    }
    """
    query_str = " ".join(query) if query else cfg["query"]

    with Anki(**cfg) as a:
        a.list_notes(query_str, show_cards, show_raw_fields, verbose)


@main.command()
def review(
    query: QueryArgument = None,
    check_markdown_consistency: Annotated[
        bool,
        typer.Option(
            "-m",
            "--check-markdown-consistency",
            help="Check for Markdown consistency",
        ),
    ] = False,
    cmc_range: Annotated[
        int,
        typer.Option(
            "-n",
            "--cmc-range",
            help="Number of days backwards to check consistency",
        ),
    ] = 7,
) -> None:
    """Review/Edit notes that match QUERY.

    The default QUERY is "tag:marked OR -flag:0". This default can be
    customized in the config file `~/.config/apy/apy.json`, e.g. with

    \b
    {
      "query": "tag:marked OR tag:leech"
    }
    """
    query_str = " ".join(query) if query else cfg["query"]

    with Anki(**cfg) as a:
        notes = list(a.find_notes(query_str))

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
def edit(
    query: RequiredQueryArgument,
    force_multiple: Annotated[
        bool,
        typer.Option(
            "--force-multiple",
            "-f",
            help="Allow editing multiple notes (will edit them one by one)",
        ),
    ] = False,
) -> None:
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
    query_str = " ".join(query)

    with Anki(**cfg) as a:
        notes = list(a.find_notes(query_str))

        # Handle no matches
        if not notes:
            console.print(f"No notes found matching query: {query_str}")
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
def tag(
    query: QueryArgument = None,
    add_tags: Annotated[
        str | None,
        typer.Option("-a", "--add-tags", help="Add specified tags to matched notes."),
    ] = None,
    remove_tags: Annotated[
        str | None,
        typer.Option(
            "-r", "--remove-tags", help="Remove specified tags from matched notes."
        ),
    ] = None,
    sort_by_count: Annotated[
        bool,
        typer.Option(
            "-c", "--sort-by-count", help="When listing tags, sort by note count"
        ),
    ] = False,
    simple: Annotated[
        bool, typer.Option("-s", "--simple", help="Only list available tags")
    ] = False,
    purge: Annotated[
        bool,
        typer.Option(
            "-p",
            "--purge",
            help="If specified, then the command will remove all unused tags",
        ),
    ] = False,
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
    query_str = " ".join(query) if query else cfg["query"]

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
            a.list_tags(sort_by_count, simple)
            return

        n_notes = len(list(a.find_notes(query_str)))
        if n_notes == 0:
            console.print("No matching notes!")
            raise typer.Abort()

        console.print(f"The operation will be applied to {n_notes} matched notes:")
        a.list_note_questions(query_str)
        console.print("")

        if add_tags is not None:
            console.print(f"Add tags:    [green]{add_tags}")
        if remove_tags is not None:
            console.print(f"Remove tags: [red]{remove_tags}")

        if not console.confirm("Continue?"):
            raise typer.Abort()

        if add_tags is not None:
            a.change_tags(query_str, add_tags)

        if remove_tags is not None:
            a.change_tags(query_str, remove_tags, add=False)


@main.command()
def reposition(
    position: Annotated[int, typer.Argument(metavar="POSITION")],
    query: RequiredQueryArgument,
) -> None:
    """Reposition cards that match QUERY.

    Sets the new position to POSITION and shifts other cards.

    Note that repositioning only works with new cards!
    """
    query_str = " ".join(query)

    with Anki(**cfg) as a:
        cids = list(a.col.find_cards(query_str))
        if not cids:
            console.print(f"No matching cards for query: {query_str}!")
            raise typer.Abort()

        for cid in cids:
            card = a.col.get_card(cid)
            if card.type != 0:
                console.print("Can only reposition new cards!")
                raise typer.Abort()

        _ = a.col.sched.reposition_new_cards(cids, position, 1, False, True)
        a.modified = True


@main.command()
def backup(
    target_file: Annotated[
        Path, typer.Argument(metavar="TARGET_FILE", resolve_path=True)
    ],
    include_media: Annotated[
        bool,
        typer.Option("-m", "--include-media", help="Include media files in backup."),
    ] = False,
    legacy: Annotated[
        bool,
        typer.Option(
            "-l",
            "--legacy",
            help="Support older Anki versions (slower/larger files)",
        ),
    ] = False,
) -> None:
    """Backup Anki database to specified target file."""
    with Anki(**cfg) as a:
        target_filename = str(target_file)

        if not target_filename.endswith(".colpkg"):
            console.print("[yellow]Warning: Target should have .colpkg extension!")
            raise typer.Abort()

        if target_file.exists():
            console.print("[yellow]Warning: Target file already exists!")
            console.print(f"[yellow]  {target_file}")
            if not console.confirm("Do you want to overwrite it?"):
                raise typer.Abort()

        with suppress_stdout():
            a.col.export_collection_package(target_filename, include_media, legacy)


if __name__ == "__main__":
    main()
