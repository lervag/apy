"""A script to interact with the Anki database"""

import click
from apy.config import cfg


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option('-b', '--base', help="Set Anki base directory")
@click.pass_context
def main(ctx, base):
    """A script to interact with the Anki database.

    The base directory may be specified with the -b / --base option. For
    convenience, it may also be specified in the config file
    `~/.config/apy/apy.json` or with the environment variable APY_BASE or
    ANKI_BASE.

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
        cfg['base'] = base

    if ctx.invoked_subcommand is None:
        ctx.invoke(info)


@main.command()
@click.option('-t', '--tags', default='marked',
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
    from apy.anki import Anki

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
                _review_note(a, note, i, n_notes,
                             remove_actions=['Abort'])


@main.command('add-from-file')
@click.argument('file', type=click.Path(exists=True, dir_okay=False))
@click.option('-t', '--tags', default='marked',
              help='Specify default tags for new cards.')
def add_from_file(file, tags):
    """Add notes from Markdown file.

    For input file syntax specification, see docstring for
    parse_notes_from_markdown().
    """
    from apy.anki import Anki

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
                _review_note(a, note, i, n_notes,
                             remove_actions=['Abort'])


@main.command('check-media')
def check_media():
    """Check media"""
    from apy.anki import Anki

    with Anki(cfg['base']) as a:
        a.check_media()


@main.command('edit-css')
@click.option('-m', '--model-name', default='Basic',
              help='Specify for which model to edit CSS template.')
@click.option('-s', '--sync-after', is_flag=True,
              help='Perform sync after any change.')
def edit_css(model_name, sync_after):
    """Edit the CSS template for the specified model."""
    from apy.anki import Anki

    with Anki(cfg['base']) as a:
        a.edit_model_css(model_name)

        if a.modified and sync_after:
            a.sync()
            a.modified = False


@main.command()
def info():
    """Print some basic statistics."""
    from apy.anki import Anki
    from apy.config import cfg_file

    if cfg_file.exists():
        click.echo(f"Config file:             {cfg_file}")
        for key in cfg.keys():
            click.echo(f"Config loaded:           {key}")
    else:
        click.echo(f"Config file:             Not found")

    with Anki(cfg['base']) as a:
        click.echo(f"Collecton path:          {a.col.path}")
        click.echo(f"Scheduler version:       {a.col.schedVer()}")
        click.echo(f"Number of notes:         {a.col.noteCount()}")
        click.echo(f"Number of cards:         {a.col.cardCount()}")
        click.echo(f"Number of cards (due):   {len(a.col.findNotes('is:due'))}")
        click.echo(f"Number of marked cards:  {len(a.col.findNotes('tag:marked'))}")

        click.echo(f"Number of decks:         {a.col.decks.count()}")
        for d in sorted(a.deck_names):
            click.echo(f"  - {d}")

        models = sorted(a.model_names)
        click.echo(f"Number of models:        {len(models)}")
        for m in models:
            click.echo(f"  - {m}")


@main.command()
@click.option('-q', '--query', default='tag:marked',
              help=('Review cards that match query [default: marked cards].'))
def review(query):
    """Review marked notes."""
    from apy.anki import Anki

    with Anki(cfg['base']) as a:
        notes = list(a.find_notes(query))
        number_of_notes = len(notes)
        for i, note in enumerate(notes):
            if not _review_note(a, note, i, number_of_notes):
                break

def _review_note(anki, note, i=None, number_of_notes=None,
                 remove_actions=None):
    """Review note i of n"""
    import os
    import readchar

    actions = {
        'c': 'Continue',
        'e': 'Edit',
        'd': 'Delete',
        'm': 'Toggle markdown',
        '*': 'Toggle marked',
        'z': 'Toggle suspend',
        'a': 'Add new',
        's': 'Save and stop',
        'x': 'Abort',
    }

    if remove_actions:
        actions = {key: val for key, val in actions.items()
                   if val not in remove_actions}

    while True:
        click.clear()
        if i is None:
            click.secho('Reviewing note\n', fg='white')
        elif number_of_notes is None:
            click.secho(f'Reviewing note {i+1}\n', fg='white')
        else:
            click.secho(f'Reviewing note {i+1} of {number_of_notes}\n',
                        fg='white')

        for x, y in actions.items():
            click.echo(click.style(x, fg='blue') + ': ' + y)

        width = os.get_terminal_size()[0]
        click.echo('\n' + '-'*width + '\n')

        note.print()

        choice = readchar.readchar()
        action = actions.get(choice)

        if action == 'Continue':
            return True

        if action == 'Edit':
            note.edit()
            continue

        if action == 'Delete':
            if click.confirm('Are you sure you want to delete the note?'):
                note.delete()
            return True

        if action == 'Toggle markdown':
            note.toggle_markdown()
            continue

        if action == 'Toggle marked':
            note.toggle_marked()
            continue

        if action == 'Toggle suspend':
            note.toggle_suspend()
            continue

        if action == 'Add new':
            click.echo('-'*width + '\n')

            notes = anki.add_notes_with_editor(
                tags=note.get_tag_string(),
                model_name=note.model_name,
                template=note)

            number_of_notes = len(notes)
            click.echo(f'Added {number_of_notes} notes')
            click.confirm('Press any key to continue.',
                          prompt_suffix='', show_default=False)
            continue

        if action == 'Save and stop':
            click.echo('Stopped')
            return False

        if action == 'Abort':
            if anki.modified:
                if not click.confirm(
                        'Abort: Changes will be lost. Continue [y/n]?',
                        show_default=False):
                    continue
                anki.modified = False
            raise click.Abort()


@main.command('list')
@click.argument('query', required=False, default='tag:marked')
def list_notes(query):
    """List notes that match a given query."""
    from apy.anki import Anki

    with Anki(cfg['base']) as a:
        for note in a.find_notes(query):
            note.print_short()


@main.command('list-cards')
@click.argument('query', required=False, default='tag:marked')
def list_cards(query):
    """List cards that match a given query."""
    from apy.anki import Anki
    from apy.convert import html_to_screen, clean_html

    with Anki(cfg['base']) as a:
        for cid in a.find_cards(query):
            c = a.col.getCard(cid)
            question = html_to_screen(clean_html(c.q())).replace('\n', ' ')
            # answer = html_to_screen(clean_html(c.a())).replace('\n', ' ')
            click.echo(f'lapses: {c.lapses:2d}  ease: {c.factor/10}%  Q: '
                       + question[:80])


@main.command()
def sync():
    """Synchronize collection with AnkiWeb."""
    from apy.anki import Anki

    with Anki(cfg['base']) as a:
        a.sync()


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    main()
