"""A script to interact with the Anki database"""

import os
from pathlib import Path
import sys
from typing import Any, Optional

import click

from apyanki import __version__
from apyanki.anki import Anki
from apyanki.config import cfg, cfg_file
from apyanki.console import console
from apyanki.note import Note

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
    tags: Optional[str] = None,
    preset: Optional[str] = None,
    model_name: Optional[str] = None,
    deck: Optional[str] = None,
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

        a.add_notes_single(fields, parse_markdown, tags, model_name, deck)


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


@main.command("add-from-file")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("-t", "--tags", default="", help="Specify default tags for new cards.")
@click.option("-d", "--deck", help="Specify default deck for new cards.")
def add_from_file(file: Path, tags: str, deck: str) -> None:
    """Add notes from Markdown file.

    The example below should adequately specify the syntax. Any initial "key: value"
    pairs specify default values for all the following notes. The following keys are
    accepted:

    \b
    * model:    The note model (required)
    * tags:     The note model (optional)
    * deck:     Which deck the note should be added to (optional)
    * markdown: Set to "false" or "no" if apy should not use a markdown converter
                while converting the input note to an Anki note. (optional)

    Here is the example Markdown input:

        // example.md
        model: Basic
        tags: marked

        # Note 1
        ## Front
        Question?

        ## Back
        Answer.

        # Note 2
        tag: silly-tag

        ## Front
        Question?

        ## Back
        Answer

        # Note 3
        model: NewModel
        markdown: false (default is true)

        ## NewFront
        FieldOne

        ## NewBack
        FieldTwo

        ## FieldThree
        FieldThree
    """
    with Anki(**cfg) as a:
        notes = a.add_notes_from_file(str(file), tags, deck)
        _added_notes_postprocessing(a, notes)


def _added_notes_postprocessing(a: Anki, notes: list[Note]) -> None:
    """Common postprocessing after 'apy add[-from-file]'."""
    n_notes = len(notes)
    if n_notes == 0:
        console.print("No notes added")
        return

    decks = [a.col.decks.name(c.did) for n in notes for c in n.n.cards()]
    n_decks = len(decks)
    if n_decks == 0:
        console.print("No notes added")
        return

    if a.n_decks > 1:
        if n_notes == 1:
            console.print(f"Added note to deck: {decks[0]}")
        elif n_decks > 1:
            console.print(f"Added {n_notes} notes to {n_decks} different decks")
        else:
            console.print(f"Added {n_notes} notes to deck: {decks[0]}")
    else:
        console.print(f"Added {n_notes} notes")

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


@main.command("list")
@click.argument("query", required=False, nargs=-1)
@click.option("-a", "--show-answer", is_flag=True, help="Display answer")
@click.option("-m", "--show-model", is_flag=True, help="Display model")
@click.option("-c", "--show-cid", is_flag=True, help="Display card ids")
@click.option("-d", "--show-due", is_flag=True, help="Display card due time in days")
@click.option("-t", "--show-type", is_flag=True, help="Display card type")
@click.option("-e", "--show-ease", is_flag=True, help="Display card ease")
@click.option("-l", "--show-lapses", is_flag=True, help="Display card number of lapses")
def list_cards(
    query: str,
    show_answer: bool,
    show_model: bool,
    show_due: bool,
    show_type: bool,
    show_ease: bool,
    show_lapses: bool,
    show_cid: bool,
) -> None:
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
        a.list_cards(
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
def sync() -> None:
    """Synchronize collection with AnkiWeb."""
    with Anki(**cfg) as a:
        a.sync()


@main.command()
@click.argument("query", required=False, nargs=-1)
@click.option("-a", "--add-tags", help="Add specified tags to matched notes.")
@click.option("-r", "--remove-tags", help="Remove specified tags from matched notes.")
def tag(query: str, add_tags: str, remove_tags: str) -> None:
    """Add/Remove tags to/from notes that match QUERY.

    The default QUERY is "tag:marked OR -flag:0". This default can be
    customized in the config file `~/.config/apy/apy.json`, e.g. with

    \b
    {
      "query": "tag:marked OR tag:leech"
    }

    If neither of the options --add-tags or --remove-tags are supplied, then
    this command simply lists all tags.
    """
    if query:
        query = " ".join(query)
    else:
        query = cfg["query"]

    with Anki(**cfg) as a:
        if add_tags is None and remove_tags is None:
            a.list_tags()
            return

        n_notes = len(list(a.find_notes(query)))
        if n_notes == 0:
            console.print("No matching notes!")
            raise click.Abort()

        console.print(f"The operation will be applied to {n_notes} matched notes:")
        a.list_notes(query)
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

        a.col.sched.reposition_new_cards(cids, position, 1, False, True)
        a.modified = True


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    main()
