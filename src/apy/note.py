"""A Note wrapper class"""

import os
from pathlib import Path
from subprocess import DEVNULL, Popen
import tempfile

from anki import latex
from bs4 import BeautifulSoup
import click
import readchar

from apy.config import cfg
from apy.convert import (
    html_to_markdown,
    html_to_screen,
    is_generated_html,
    markdown_file_to_notes,
    markdown_to_html,
    plain_to_html,
)
from apy.utilities import cd, choose, editor


class Note:
    """A Note wrapper class"""

    def __init__(self, anki, note):
        self.a = anki
        self.n = note
        self.model_name = note.note_type()['name']
        self.fields = [x for x, y in self.n.items()]
        self.suspended = any(c.queue == -1 for c in self.n.cards())

    def __repr__(self):
        """Convert note to Markdown format"""
        lines = [
            '# Note',
            f'nid: {self.n.id}',
            f'model: {self.model_name}',
        ]

        if self.a.n_decks > 1:
            lines += [f'deck: {self.get_deck()}']

        lines += [f'tags: {self.get_tag_string()}']

        if not any(is_generated_html(x) for x in self.n.values()):
            lines += ['markdown: false']

        lines += ['']

        for key, val in self.n.items():
            lines.append('## ' + key)
            lines.append(html_to_screen(val, parseable=True))
            lines.append('')

        return '\n'.join(lines)

    def get_template(self):
        """Convert note to Markdown format as a template for new notes"""
        lines = [f'model: {self.model_name}']

        if self.a.n_decks > 1:
            lines += [f'deck: {self.get_deck()}']

        lines += [f'tags: {self.get_tag_string()}']

        if not any(is_generated_html(x) for x in self.n.values()):
            lines += ['markdown: false']

        lines += ['']
        lines += ['# Note']
        lines += ['']

        for key, val in self.n.items():
            if is_generated_html(val):
                key += ' (md)'

            lines.append('## ' + key)
            lines.append(html_to_screen(val, parseable=True))
            lines.append('')

        return '\n'.join(lines)

    def print(self, pprint=True):
        """Print to screen (similar to __repr__ but with colors)"""
        lines = [click.style('# Note', fg='green')]

        types = ', '.join(
            {
                ['new', 'learning', 'review', 'relearning'][c.type]
                for c in self.n.cards()
            }
        )

        lines += [
            click.style('nid: ', fg='yellow')
            + f'{self.n.id}'
            + click.style('    card type(s): ', fg='yellow')
            + types
        ]

        lines += [
            click.style('model: ', fg='yellow')
            + f'{self.model_name} ({len(self.n.cards())} cards)'
        ]

        if self.a.n_decks > 1:
            lines += [click.style('deck: ', fg='yellow') + self.get_deck()]

        lines += [click.style('tags: ', fg='yellow') + self.get_tag_string()]

        flags = [c.template()['name'] for c in self.n.cards() if c.flags > 0]
        if flags:
            flags = [click.style(x, fg='magenta') for x in flags]
            lines += [f"{click.style('flagged:', fg='yellow')} " f"{', '.join(flags)}"]

        if not any(is_generated_html(x) for x in self.n.values()):
            lines += [f"{click.style('markdown:', fg='yellow')} false"]

        if self.suspended:
            lines[0] += f" ({click.style('suspended', fg='red')})"

        lines += ['']

        imgs = []
        for key, html in self.n.items():
            # Render LaTeX if necessary
            note_type = self.n.note_type()
            latex.render_latex(html, note_type, self.a.col)
            imgs += _get_imgs_from_html_latex(html, note_type, self.a)

            lines.append(click.style('## ' + key, fg='blue'))
            lines.append(html_to_screen(html, pprint))
            lines.append('')

        if imgs:
            lines.append(click.style('LaTeX sources', fg='blue'))
            for line in imgs:
                lines.append('- ' + str(line))
            lines.append('')

        click.echo('\n'.join(lines))

    def show_images(self):
        """Show in the fields"""
        note_type = self.n.note_type()
        images = []
        for html in self.n.values():
            images += _get_imgs_from_html_latex(html, note_type, self.a)
            images += _get_imgs_from_html(html)

        with cd(self.a.col.media.dir()):
            for file in images:
                view_cmd = cfg['img_viewers'].get(
                    file.suffix[1:], cfg['img_viewers_default']
                )
                Popen(view_cmd + [file], stdout=DEVNULL, stderr=DEVNULL)

    def edit(self):
        """Edit tags and fields of current note"""
        with tempfile.NamedTemporaryFile(
            mode='w+', dir=os.getcwd(), prefix='edit_note_', suffix='.md'
        ) as tf:
            tf.write(str(self))
            tf.flush()

            retcode = editor(tf.name)
            if retcode != 0:
                click.echo(f'Editor return with exit code {retcode}!')
                return

            notes = markdown_file_to_notes(tf.name)

        if not notes:
            click.echo('Something went wrong when editing note!')
            return

        if len(notes) > 1:
            added_notes = self.a.add_notes_from_list(notes[1:])
            click.echo(f'\nAdded {len(added_notes)} new notes while editing.')
            for note in added_notes:
                cards = note.n.cards()
                click.echo(f'* nid: {note.n.id} (with {len(cards)} cards)')
                for card in note.n.cards():
                    click.echo(f'  * cid: {card.id}')
            click.confirm(
                '\nPress <cr> to continue.', prompt_suffix='', show_default=False
            )

        note = notes[0]

        new_tags = note['tags'].split()
        if new_tags != self.n.tags:
            self.n.tags = new_tags

        new_deck = note.get('deck', None)
        if new_deck is not None and new_deck != self.get_deck():
            self.set_deck(new_deck)

        for i, value in enumerate(note['fields'].values()):
            if note['markdown']:
                self.n.fields[i] = markdown_to_html(value)
            else:
                self.n.fields[i] = plain_to_html(value)

        self.n.flush()
        self.a.modified = True
        if self.n.dupeOrEmpty():
            click.confirm(
                'The updated note is now a dupe!', prompt_suffix='', show_default=False
            )

    def delete(self):
        """Delete the note"""
        self.a.delete_notes(self.n.id)

    def consistent_markdown(self):
        """Check if markdown fields are consistent with html values"""
        for html in [h for h in self.n.values() if is_generated_html(h)]:
            if html != markdown_to_html(html_to_markdown(html)):
                return False

        return True

    def change_model(self):
        """Change the note type"""
        click.clear()
        click.secho('Warning!', fg='red')
        click.echo(
            '\nThe note type is changed by creating a new note with '
            'the selected\ntype and then deleting the old note. This '
            'means that the review\nprogress is lost!'
        )
        if not click.confirm('\nContinue?'):
            return False

        models = list(self.a.model_names)
        models.sort()
        while True:
            click.clear()
            click.echo('Please choose new model:')
            for n, m in enumerate(models):
                click.echo(f'  {n+1}: {m}')
            index = click.prompt('>>> ', prompt_suffix='', type=int) - 1
            try:
                new_model = models[index]
                self.a.set_model(new_model)
                model = self.a.get_model(new_model)
                break
            except IndexError:
                continue

        fields = ['' for _ in range(len(model['flds']))]
        for key, val in self.n.items():
            fields[0] += f'### {key}\n{val}\n'

        tags = ', '.join(self.n.tags)
        is_markdown = any(is_generated_html(x) for x in self.n.values())

        # pylint: disable=protected-access
        new_note = self.a._add_note(fields, tags, is_markdown)
        new_note.edit()
        # pylint: enable=protected-access
        self.a.delete_notes(self.n.id)

        return True

    def toggle_marked(self):
        """Toggle marked tag for note"""
        if 'marked' in self.n.tags:
            self.n.delTag('marked')
        else:
            self.n.addTag('marked')
        self.n.flush()
        self.a.modified = True

    def toggle_suspend(self):
        """Toggle suspend for note"""
        cids = [c.id for c in self.n.cards()]

        if self.suspended:
            self.a.col.sched.unsuspendCards(cids)
        else:
            self.a.col.sched.suspendCards(cids)

        self.suspended = not self.suspended
        self.a.modified = True

    def toggle_markdown(self, index=None):
        """Toggle markdown on a field"""
        if index is None:
            fields = self.fields
            field = choose(fields, 'Toggle markdown for field:')
            index = fields.index(field)

        field_value = self.n.fields[index]

        if is_generated_html(field_value):
            self.n.fields[index] = html_to_markdown(field_value)
        else:
            self.n.fields[index] = markdown_to_html(field_value)

        self.n.flush()
        self.a.modified = True

    def clear_flags(self):
        """Clear flags for note"""
        for c in self.n.cards():
            if c.flags > 0:
                c.flags = 0
                c.flush()
                self.a.modified = True

    def show_cards(self):
        """Show cards for note"""
        for i, c in enumerate(self.n.cards()):
            number = f'{str(i) + ".":>3s}'
            name = c.template()['name']
            if c.flags > 0:
                name = click.style(name, fg='red')
            click.echo(f'  {click.style(number, fg="white")} {name}')

        click.secho('\nPress any key to continue ... ', fg='blue', nl=False)
        readchar.readchar()

    def get_deck(self):
        """Return which deck the note belongs to"""
        return self.a.col.decks.name(self.n.cards()[0].did)

    def set_deck(self, deck):
        """Move note to deck"""
        if not isinstance(deck, str):
            raise Exception('Argument "deck" should be string!')

        newdid = self.a.col.decks.id(deck)
        cids = [c.id for c in self.n.cards()]

        if cids:
            self.a.col.decks.setDeck(cids, newdid)
            self.a.modified = True

    def set_deck_interactive(self):
        """Move note to deck, interactive"""
        click.clear()

        click.secho('Specify target deck (CTRL-c/CTRL-d to abort):', fg='white')
        for d in self.a.col.decks.all_names_and_ids(include_filtered=False):
            click.echo(f'* {d.name}')
        click.echo('* OTHER -> create new deck')

        try:
            newdeck = click.prompt('> ', prompt_suffix='')
        except click.Abort:
            return

        self.set_deck(newdeck)

    def get_field(self, index_or_name):
        """Return field with given index or name"""
        if isinstance(index_or_name, str):
            index = self.fields.index(index_or_name)
        else:
            index = index_or_name

        reply = self.n.fields[index]

        if is_generated_html(reply):
            reply = html_to_markdown(reply)

        return reply

    def get_tag_string(self):
        """Get tag string"""
        return ', '.join(self.n.tags)

    def review(self, i=None, number_of_notes=None, remove_actions=None):
        """Interactive review of the note

        This method is used by the review command.

        if the arguments "i" and "number_of_notes" are supplied, then they are
        displayed to show review progress.

        The "remove_actions" argument can be used to remove a default action
        from the action menu.
        """
        actions = {
            'c': 'Continue',
            'e': 'Edit',
            'a': 'Add new',
            'd': 'Delete',
            'm': 'Toggle markdown',
            '*': 'Toggle marked',
            'z': 'Toggle suspend',
            'p': 'Toggle pprint',
            'F': 'Clear flags',
            'C': 'Show card names',
            'f': 'Show images',
            'E': 'Edit CSS',
            'D': 'Change deck',
            'N': 'Change model',
            's': 'Save and stop',
            'x': 'Abort',
        }

        if remove_actions:
            actions = {
                key: val for key, val in actions.items() if val not in remove_actions
            }

        _pprint = True
        refresh = True
        while True:
            if refresh:
                click.clear()
                if i is None:
                    click.secho('Reviewing note', fg='white')
                elif number_of_notes is None:
                    click.secho(f'Reviewing note {i+1}', fg='white')
                else:
                    click.secho(
                        f'Reviewing note {i+1} of {number_of_notes}', fg='white'
                    )

                column = 0
                for x, y in actions.items():
                    menu = click.style(x, fg='blue') + ': ' + y
                    if column < 3:
                        click.echo(f'{menu:28s}', nl=False)
                    else:
                        click.echo(menu)
                    column = (column + 1) % 4

                width = os.get_terminal_size()[0]
                click.echo('\n')

                self.print(_pprint)
            else:
                refresh = True

            choice = readchar.readchar()
            action = actions.get(choice)

            if action == 'Continue':
                return True

            if action == 'Edit':
                self.edit()
                continue

            if action == 'Add new':
                click.echo('-' * width + '\n')

                notes = self.a.add_notes_with_editor(
                    tags=self.get_tag_string(),
                    model_name=self.model_name,
                    template=self,
                )

                click.echo(f'Added {len(notes)} notes')
                for note in notes:
                    cards = note.n.cards()
                    click.echo(f'* nid: {note.n.id} (with {len(cards)} cards)')
                    for card in note.n.cards():
                        click.echo(f'  * cid: {card.id}')
                click.confirm(
                    'Press any key to continue.', prompt_suffix='', show_default=False
                )
                continue

            if action == 'Delete' and click.confirm(
                'Are you sure you want to delete the note?'
            ):
                self.delete()
                return True

            if action == 'Toggle markdown':
                self.toggle_markdown()
                continue

            if action == 'Toggle marked':
                self.toggle_marked()
                continue

            if action == 'Toggle suspend':
                self.toggle_suspend()
                continue

            if action == 'Toggle pprint':
                _pprint = not _pprint
                continue

            if action == 'Clear flags':
                self.clear_flags()
                continue

            if action == 'Show card names':
                self.show_cards()
                continue

            if action == 'Show images':
                self.show_images()
                refresh = False
                continue

            if action == 'Edit CSS':
                self.a.edit_model_css(self.model_name)
                continue

            if action == 'Change deck':
                self.set_deck_interactive()
                continue

            if action == 'Change model':
                if self.change_model():
                    return True
                continue

            if action == 'Save and stop':
                click.echo('Stopped')
                return False

            if action == 'Abort':
                if self.a.modified:
                    if not click.confirm(
                        'Abort: Changes will be lost. Continue [y/n]?',
                        show_default=False,
                    ):
                        continue
                    self.a.modified = False
                raise click.Abort()


def _get_imgs_from_html(field_html):
    """Gather image filenames from <img> tags in field html.

    Note: The returned paths are relative to the Anki media directory.
    """
    soup = BeautifulSoup(field_html, 'html.parser')
    return [Path(x['src']) for x in soup.find_all('img')]


def _get_imgs_from_html_latex(field_html, note_type, anki):
    """Gather the generated LaTeX image filenames from field html.

    Note: The returned paths are relative to the Anki media directory.
    """
    # pylint: disable=protected-access
    proto = anki.col._backend.extract_latex(
        text=field_html, svg=note_type.get('latexsvg', False), expand_clozes=False
    )
    out = latex.ExtractedLatexOutput.from_proto(proto)
    return [Path(ltx.filename) for ltx in out.latex]
