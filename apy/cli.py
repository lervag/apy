"""A script to interact with the Anki database"""
import os

import click

from apy.anki import Anki
from apy.config import cfg, cfg_file


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option('-b', '--base', help="Set Anki base directory")
@click.pass_context
def main(ctx, base):
    """A script to interact with the Anki database.

    The base directory may be specified with the -b / --base option. For
    convenience, it may also be specified in the config file
    `~/.config/apy/apy.json` or with the environment variable APY_BASE or
    ANKI_BASE. This should point to the base directory where Anki stores it's
    database and related files. See the Anki documentation for information
    about where this is located on different systems
    (https://apps.ankiweb.net/docs/manual.html#file-locations).

    A few sub commands will open an editor for input. Vim is used by default.
    The input is parsed when one saves and quits. To abort, one should exit the
    editor with a non-zero exit code. In Vim, one can do this with the `:cquit`
    command.

    One may specify a different editor with the EDITOR environment variable.
    For example, to use emacs one can add this to ones `~/.bashrc` (or similar)
    file:

        export EDITOR=emacs

    Note: Use `apy subcmd --help` to get detailed help for a given subcommand.
    """
    if base:
        cfg['base'] = os.path.abspath(os.path.expanduser(base))

    if ctx.invoked_subcommand is None:
        ctx.invoke(info)


@main.command()
@click.option('-t', '--tags', default='',
              help='Specify default tags for new cards.')
@click.option('-m', '--model', default='Basic',
              help=('Specify default model for new cards.'))
@click.option('-d', '--deck',
              help=('Specify defauly deck for new cards.'))
def add(tags, model, deck):
    """Add notes interactively from terminal.

    Examples:

    \b
        # Add notes to deck "MyDeck" with tags 'my-tag' and 'new-tag'
        apy add -t "my-tag new-tag" -d MyDeck

    \b
        # Ask for the model and the deck for each new card
        apy add -m ASK -d ask
    """
    with Anki(cfg['base']) as a:
        notes = a.add_notes_with_editor(tags, model, deck)

        decks = [a.col.decks.name(c.did) for n in notes for c in n.n.cards()]
        n_notes = len(notes)
        n_decks = len(decks)

        if a.n_decks > 1:
            if n_notes == 1:
                click.echo(f'Added note to deck: {decks[0]}')
            elif n_decks > 1:
                click.echo(f'Added {n_notes} notes to {n_decks} different decks')
            else:
                click.echo(f'Added {n_notes} notes to deck: {decks[0]}')
        else:
            click.echo(f'Added {n_notes} notes')

        if click.confirm('Review added notes?'):
            for i, note in enumerate(notes):
                note.review(i, n_notes, remove_actions=['Abort'])

@main.command('add-from-file')
@click.argument('file', type=click.Path(exists=True, dir_okay=False))
@click.option('-t', '--tags', default='',
              help='Specify default tags for new cards.')
def add_from_file(file, tags):
    """Add notes from Markdown file.

    For input file syntax specification, see docstring for
    parse_notes_from_markdown().
    """
    with Anki(cfg['base']) as a:
        notes = a.add_notes_from_file(file, tags)

        decks = [a.col.decks.name(c.did) for n in notes for c in n.n.cards()]
        n_notes = len(notes)
        n_decks = len(decks)

        if a.n_decks > 1:
            if n_notes == 1:
                click.echo(f'Added note to deck: {decks[0]}')
            elif n_decks > 1:
                click.echo(f'Added {n_notes} notes to {n_decks} different decks')
            else:
                click.echo(f'Added {n_notes} notes to deck: {decks[0]}')
        else:
            click.echo(f'Added {n_notes} notes')

        if click.confirm('Review added notes?'):
            for i, note in enumerate(notes):
                note.review(i, n_notes, remove_actions=['Abort'])

@main.command('check-media')
def check_media():
    """Check media"""
    with Anki(cfg['base']) as a:
        a.check_media()

@main.command()
def info():
    """Print some basic statistics."""
    if cfg_file.exists():
        click.echo(f"Config file:             {cfg_file}")
        for key in cfg.keys():
            click.echo(f"Config loaded:           {key}")
    else:
        click.echo(f"Config file:             Not found")

    with Anki(cfg['base']) as a:
        click.echo(f"Collecton path:          {a.col.path}")
        click.echo(f"Scheduler version:       {a.col.schedVer()}")

        if a.col.decks.count() > 1:
            click.echo("Decks:")
            for name in sorted(a.deck_names):
                click.echo(f"  - {name}")

        sum_notes = a.col.noteCount()
        sum_cards = a.col.cardCount()
        sum_due = len(a.col.findNotes('is:due'))
        sum_marked = len(a.col.findNotes('tag:marked'))
        sum_flagged = len(a.col.findNotes('-flag:0'))

        click.echo(f"\n{'Model':26s} {'notes':>8s} {'cards':>8s} "
                   f"{'due':>8s} {'marked':>8s} {'flagged':>8s}")
        click.echo("-"*71)
        models = sorted(a.model_names)
        for m in models:
            nnotes = len(a.col.findNotes(f'"note:{m}"'))
            ncards = len(a.find_cards(f'"note:{m}"'))
            ndue = len(a.find_cards(f'"note:{m}" is:due'))
            nmarked = len(a.find_cards(f'"note:{m}" tag:marked'))
            nflagged = len(a.find_cards(f'"note:{m}" -flag:0'))
            click.echo(f"{m:26s} {nnotes:8d} {ncards:8d} "
                       f"{ndue:8d} {nmarked:8d} {nflagged:8d}")
        click.echo("-"*71)
        click.echo(f"{'Sum':26s} {sum_notes:8d} {sum_cards:8d} "
                   f"{sum_due:8d} {sum_marked:8d} {sum_flagged:8d}")
        click.echo("-"*71)


@main.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.pass_context
def model(ctx):
    """Interact with Anki models."""

@model.command('edit-css')
@click.option('-m', '--model-name', default='Basic',
              help='Specify for which model to edit CSS template.')
@click.option('-s', '--sync-after', is_flag=True,
              help='Perform sync after any change.')
def edit_css(model_name, sync_after):
    """Edit the CSS template for the specified model."""
    with Anki(cfg['base']) as a:
        a.edit_model_css(model_name)

        if a.modified and sync_after:
            a.sync()
            a.modified = False

@model.command()
@click.argument('old-name')
@click.argument('new-name')
def rename(old_name, new_name):
    """Rename model from old_name to new_name."""
    with Anki(cfg['base']) as a:
        a.rename_model(old_name, new_name)


@main.command('list')
@click.argument('query', required=False, default='tag:marked OR -flag:0')
@click.option('-v', '--verbose', is_flag=True,
              help='Be verbose, show more info')
def list_cards(query, verbose):
    """List cards that match a given query."""
    with Anki(cfg['base']) as a:
        a.list_cards(query, verbose)

@main.command()
@click.option('-q', '--query', default='tag:marked OR -flag:0',
              help=('Review cards that match query [default: marked cards].'))
def review(query):
    """Review marked notes."""
    with Anki(cfg['base']) as a:
        notes = list(a.find_notes(query))
        number_of_notes = len(notes)
        for i, note in enumerate(notes):
            if not note.review(i, number_of_notes):
                break

@main.command()
def sync():
    """Synchronize collection with AnkiWeb."""
    with Anki(cfg['base']) as a:
        a.sync()

@main.command()
@click.argument('query')
@click.option('-a', '--add-tags',
              help='Add specified tags to matched notes.')
@click.option('-r', '--remove-tags',
              help='Add specified tags to matched notes.')
def tag(query, add_tags, remove_tags):
    """Add or remove tags from notes that match the query."""
    if add_tags is None and remove_tags is None:
        click.echo(f'Please specify either -a and/or -r to add/remove tags!')
        return

    with Anki(cfg['base']) as a:
        n_notes = len(list(a.find_notes(query)))
        if n_notes == 0:
            click.echo(f'No matching notes!')
            raise click.Abort()

        click.echo(f'The operation will be applied to {n_notes} matched notes:')
        a.list_notes(query)
        click.echo('')

        if add_tags is not None:
            click.echo(f'Add tags:    {click.style(add_tags, fg="green")}')
        if remove_tags is not None:
            click.echo(f'Remove tags: {click.style(remove_tags, fg="red")}')

        if not click.confirm(click.style('Continue?', fg='blue')):
            raise click.Abort()

        if add_tags is not None:
            a.change_tags(query, add_tags)

        if remove_tags is not None:
            a.change_tags(query, remove_tags, add=False)


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    main()
