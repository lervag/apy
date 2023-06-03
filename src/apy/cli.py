"""A script to interact with the Anki database"""
import os
import sys

import click

from apy import __version__
from apy.anki import Anki
from apy.config import cfg, cfg_file

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option("-b", "--base-path", help="Set Anki base directory")
@click.option("-p", "--profile-name", help="Specify name of Anki profile to use")
@click.option("-V", "--version", is_flag=True, help="Show apy version")
@click.pass_context
def main(ctx, base_path, profile_name, version):
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

    One may specify a different editor with the EDITOR environment variable.
    For example, to use emacs one can add this to one's `~/.bashrc` (or similar)
    file:

        export EDITOR=emacs

    Note: Use `apy subcmd --help` to get detailed help for a given subcommand.
    """
    if version:
        click.echo(f"apy {__version__}")
        sys.exit()

    if base_path:
        cfg["base_path"] = os.path.abspath(os.path.expanduser(base_path))

    if profile_name:
        cfg["profile_name"] = profile_name

    if ctx.invoked_subcommand is None:
        ctx.invoke(info)


@main.command("add-single")
@click.option("-s", "--preset", default="default", help="Specify a preset.")
@click.option("-t", "--tags", help="Specify default tags for new cards.")
@click.option(
    "-m", "--model", "model_name", help=("Specify default model for new cards.")
)
@click.option("-d", "--deck", help=("Specify default deck for new cards."))
@click.argument("fields", nargs=-1)
def add_single(fields, tags=None, preset=None, model_name=None, deck=None):
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

        a.add_notes_single(fields, tags, model_name, deck)


@main.command()
@click.option("-t", "--tags", default="", help="Specify default tags for new cards.")
@click.option(
    "-m",
    "--model",
    "model_name",
    default="Basic",
    help=("Specify default model for new cards."),
)
@click.option("-d", "--deck", help=("Specify default deck for new cards."))
def add(tags, model_name, deck):
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
def add_from_file(file, tags):
    """Add notes from Markdown file.

    For input file syntax specification, see docstring for
    markdown_file_to_notes() in convert.py.
    """
    with Anki(**cfg) as a:
        notes = a.add_notes_from_file(file, tags)
        _added_notes_postprocessing(a, notes)


def _added_notes_postprocessing(a, notes):
    """Common postprocessing after 'apy add[-from-file]'."""
    n_notes = len(notes)
    if n_notes == 0:
        click.echo("No notes added")
        return

    decks = [a.col.decks.name(c.did) for n in notes for c in n.n.cards()]
    n_decks = len(decks)
    if n_decks == 0:
        click.echo("No notes added")
        return

    if a.n_decks > 1:
        if n_notes == 1:
            click.echo(f"Added note to deck: {decks[0]}")
        elif n_decks > 1:
            click.echo(f"Added {n_notes} notes to {n_decks} different decks")
        else:
            click.echo(f"Added {n_notes} notes to deck: {decks[0]}")
    else:
        click.echo(f"Added {n_notes} notes")

    for note in notes:
        cards = note.n.cards()
        click.echo(f"* nid: {note.n.id} (with {len(cards)} cards)")
        for card in note.n.cards():
            click.echo(f"  * cid: {card.id}")


@main.command("check-media")
def check_media():
    """Check media."""
    with Anki(**cfg) as a:
        a.check_media()


@main.command()
def info():
    """Print some basic statistics."""
    if cfg_file.exists():
        click.echo(f"Config file:             {cfg_file}")
        for key in cfg.keys():
            click.echo(f"Config loaded:           {key}")
    else:
        click.echo("Config file:             Not found")

    with Anki(**cfg) as a:
        click.echo(f"Collection path:         {a.col.path}")
        click.echo(f"Scheduler version:       {a.col.sched_ver()}")

        if a.col.decks.count() > 1:
            click.echo("Decks:")
            for name in sorted(a.deck_names):
                click.echo(f"  - {name}")

        sum_notes = a.col.note_count()
        sum_cards = a.col.card_count()
        sum_due = len(a.col.find_notes("is:due"))
        sum_marked = len(a.col.find_notes("tag:marked"))
        sum_flagged = len(a.col.find_notes("-flag:0"))
        sum_new = len(a.col.find_notes("is:new"))
        sum_susp = len(a.col.find_notes("is:suspended"))

        click.echo(
            f"\n{'Model':24s} {'notes':>7s} {'cards':>7s} "
            f"{'due':>7s} {'new':>7s} {'susp.':>7s} "
            f"{'marked':>7s} {'flagged':>7s}"
        )
        click.echo("-" * 80)
        models = sorted(a.model_names)
        for m in models:
            nnotes = len(set(a.col.find_notes(f'"note:{m}"')))
            ncards = len(a.find_cards(f'"note:{m}"'))
            ndue = len(a.find_cards(f'"note:{m}" is:due'))
            nmarked = len(a.find_cards(f'"note:{m}" tag:marked'))
            nflagged = len(a.find_cards(f'"note:{m}" -flag:0'))
            nnew = len(a.find_cards(f'"note:{m}" is:new'))
            nsusp = len(a.find_cards(f'"note:{m}" is:suspended'))
            name = m[:24]
            click.echo(
                f"{name:24s} {nnotes:7d} {ncards:7d} "
                f"{ndue:7d} {nnew:7d} {nsusp:7d} "
                f"{nmarked:7d} {nflagged:7d}"
            )
        click.echo("-" * 80)
        click.echo(
            f"{'Sum':24s} {sum_notes:7d} {sum_cards:7d} "
            f"{sum_due:7d} {sum_new:7d} {sum_susp:7d} "
            f"{sum_marked:7d} {sum_flagged:7d}"
        )
        click.echo("-" * 80)


@main.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
def model():
    """Interact with Anki models."""


@model.command("edit-css")
@click.option(
    "-m",
    "--model-name",
    default="Basic",
    help="Specify for which model to edit CSS template.",
)
@click.option("-s", "--sync-after", is_flag=True, help="Perform sync after any change.")
def edit_css(model_name, sync_after):
    """Edit the CSS template for the specified model."""
    with Anki(**cfg) as a:
        a.edit_model_css(model_name)

        if a.modified and sync_after:
            a.sync()
            a.modified = False


@model.command()
@click.argument("old-name")
@click.argument("new-name")
def rename(old_name, new_name):
    """Rename model from old_name to new_name."""
    with Anki(**cfg) as a:
        a.rename_model(old_name, new_name)


@main.command("list")
@click.argument("query", required=False, nargs=-1)
@click.option("-v", "--verbose", is_flag=True, help="Be verbose, show more info")
def list_cards(query, verbose):
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
def review(query, check_markdown_consistency, cmc_range):
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
                if not n.consistent_markdown()
            ]

        number_of_notes = len(notes)
        for i, note in enumerate(notes):
            if not note.review(i, number_of_notes):
                break


@main.command()
def sync():
    """Synchronize collection with AnkiWeb."""
    with Anki(**cfg) as a:
        a.sync()


@main.command()
@click.argument("query", required=False, nargs=-1)
@click.option("-a", "--add-tags", help="Add specified tags to matched notes.")
@click.option("-r", "--remove-tags", help="Remove specified tags from matched notes.")
def tag(query, add_tags, remove_tags):
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
            click.echo("No matching notes!")
            raise click.Abort()

        click.echo(f"The operation will be applied to {n_notes} matched notes:")
        a.list_notes(query)
        click.echo("")

        if add_tags is not None:
            click.echo(f'Add tags:    {click.style(add_tags, fg="green")}')
        if remove_tags is not None:
            click.echo(f'Remove tags: {click.style(remove_tags, fg="red")}')

        if not click.confirm(click.style("Continue?", fg="blue")):
            raise click.Abort()

        if add_tags is not None:
            a.change_tags(query, add_tags)

        if remove_tags is not None:
            a.change_tags(query, remove_tags, add=False)


@main.command()
@click.argument("position", type=int, required=True, nargs=1)
@click.argument("query", required=True, nargs=-1)
def reposition(position, query):
    """Reposition cards that match QUERY.

    Sets the new position to POSITION and shifts other cards.

    Note that repositioning only works with new cards!
    """
    query = " ".join(query)

    with Anki(**cfg) as a:
        cids = list(a.find_cards(query))
        if not cids:
            click.echo(f"No matching cards for query: {query}!")
            raise click.Abort()

        for cid in cids:
            card = a.col.get_card(cid)
            if card.type != 0:
                click.echo("Can only reposition new cards!")
                raise click.Abort()

        a.col.sched.sortCards(cids, position, 1, False, True)
        a.modified = True


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    main()
