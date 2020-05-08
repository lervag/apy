"""A Note wrapper class"""

import os
import functools
import tempfile
import subprocess
from pathlib import Path
from bs4 import BeautifulSoup

import click
import readchar
from anki import latex

from apy.convert import html_to_markdown
from apy.convert import html_to_screen
from apy.convert import is_generated_html
from apy.convert import markdown_file_to_notes
from apy.convert import markdown_to_html
from apy.convert import plain_to_html
from apy.utilities import cd, editor, choose


class Note:
    """A Note wrapper class"""

    def __init__(self, anki, note):
        self.a = anki
        self.n = note
        self.model_name = note.model()['name']
        self.fields = [x for x, y in self.n.items()]
        self.suspended = any([c.queue == -1 for c in self.n.cards()])


    def __repr__(self):
        """Convert note to Markdown format"""
        lines = [
            f'# Note ID: {self.n.id}',
            f'model: {self.model_name}',
        ]

        if self.a.n_decks > 1:
            lines += [f'deck: {self.get_deck()}']

        lines += [f'tags: {self.get_tag_string()}']

        if not any([is_generated_html(x) for x in self.n.values()]):
            lines += ['markdown: false']

        lines += ['']

        for key, val in self.n.items():
            if is_generated_html(val):
                key += ' (md)'

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

        if not any([is_generated_html(x) for x in self.n.values()]):
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

    def print(self):
        """Print to screen (similar to __repr__ but with colors)"""
        lines = [
            click.style(f'# Note ID: {self.n.id}', fg='green'),
            click.style('model: ', fg='yellow')
            + f'{self.model_name} ({len(self.n.cards())} cards)',
        ]

        if self.a.n_decks > 1:
            lines += [click.style('deck: ', fg='yellow')+self.get_deck()]

        lines += [click.style('tags: ', fg='yellow')
                  + self.get_tag_string()]

        if not any([is_generated_html(x) for x in self.n.values()]):
            lines += [f"{click.style('markdown:', fg='yellow')} false"]

        if self.suspended:
            lines[0] += f" ({click.style('suspended', fg='red')})"

        lines += ['']

        latex_imgs = []
        for key, html in self.n.items():
            # Render LaTeX if necessary
            latex.render_latex(html, self.n.model(), self.a.col)
            latex_imgs += self.get_lateximg_from_field(html)

            if is_generated_html(html):
                key += ' (md)'

            lines.append(click.style('# ' + key, fg='blue'))
            lines.append(html_to_screen(html))
            lines.append('')

        if latex_imgs:
            lines.append(click.style('LaTeX sources', fg='blue'))
            for line in latex_imgs:
                lines.append('- ' + str(line))
            lines.append('')

        click.echo('\n'.join(lines))


    def show_images(self):
        """Show in the fields"""
        images = []
        for html in self.n.values():
            images += self.get_lateximg_from_field(html)

        with cd(self.a.col.media.dir()):
            for file in images:
                if file.suffix == '.svg':
                    subprocess.Popen(['display', '-density', '300', file],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                else:
                    subprocess.Popen(['feh', file],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)


    def edit(self):
        """Edit tags and fields of current note"""
        with tempfile.NamedTemporaryFile(mode='w+',
                                         dir=os.getcwd(),
                                         prefix='edit_note_',
                                         suffix='.md') as tf:
            tf.write(str(self))
            tf.flush()

            retcode = editor(tf.name)
            if retcode != 0:
                click.echo(f'Editor return with exit code {retcode}!')
                return

            notes = markdown_file_to_notes(tf.name)

        if not notes:
            click.echo(f'Something went wrong when editing note!')
            return

        if len(notes) > 1:
            self.a.add_notes_from_list(notes[1:])
            click.confirm(f'\nAdded {len(notes) - 1} new notes while editing.'
                          '\nPress <cr> to continue.',
                          prompt_suffix='', show_default=False)

        note = notes[0]

        new_tags = note['tags'].split()
        if new_tags != self.n.tags:
            self.n.tags = new_tags

        for i, value in enumerate(note['fields'].values()):
            if note['markdown']:
                self.n.fields[i] = markdown_to_html(value)
            else:
                self.n.fields[i] = plain_to_html(value)

        self.n.flush()
        self.a.modified = True
        if self.n.dupeOrEmpty():
            click.confirm('The updated note is now a dupe!',
                          prompt_suffix='', show_default=False)

    def delete(self):
        """Delete the note"""
        self.a.delete_notes(self.n.id)


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


    def get_deck(self):
        """Return which deck the note belongs to"""
        return self.a.col.decks.name(self.n.cards()[0].did)


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


    def get_lateximg_from_field(self, html):
        """Gather the generated LaTeX image filenames"""
        return [Path(ltx.filename) for ltx in
                self.a.col.backend.extract_latex(
                    html, self.n.model().get("latexsvg", False), False).latex]

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
            'd': 'Delete',
            'f': 'Show images',
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

        refresh = True
        while True:
            if refresh:
                click.clear()
                if i is None:
                    click.secho('Reviewing note\n', fg='white')
                elif number_of_notes is None:
                    click.secho(f'Reviewing note {i+1}\n', fg='white')
                else:
                    click.secho(f'Reviewing note {i+1} of {number_of_notes}\n',
                                fg='white')

                column = 0
                for x, y in actions.items():
                    menu = click.style(x, fg='blue') + ': ' + y
                    if column < 3:
                        click.echo(f'{menu:28s}', nl=False)
                    else:
                        click.echo(menu)
                    column = (column + 1) % 4

                width = os.get_terminal_size()[0]
                click.echo('\n' + '-'*width + '\n')

                self.print()
            else:
                refresh = True

            choice = readchar.readchar()
            action = actions.get(choice)

            if action == 'Continue':
                return True

            if action == 'Edit':
                self.edit()
                continue

            if action == 'Delete':
                if click.confirm('Are you sure you want to delete the note?'):
                    self.delete()
                return True

            if action == 'Show images':
                self.show_images()
                refresh = False
                continue

            if action == 'Toggle markdown':
                self.toggle_markdown()
                continue

            if action == 'Toggle marked':
                self.toggle_marked()
                continue

            if action == 'Toggle suspend':
                self.toggle_suspend()
                continue

            if action == 'Add new':
                click.echo('-'*width + '\n')

                notes = self.a.add_notes_with_editor(
                    tags=self.get_tag_string(),
                    model_name=self.model_name,
                    template=self)

                number_of_notes = len(notes)
                click.echo(f'Added {number_of_notes} notes')
                click.confirm('Press any key to continue.',
                              prompt_suffix='', show_default=False)
                continue

            if action == 'Save and stop':
                click.echo('Stopped')
                return False

            if action == 'Abort':
                if self.a.modified:
                    if not click.confirm(
                            'Abort: Changes will be lost. Continue [y/n]?',
                            show_default=False):
                        continue
                    self.a.modified = False
                raise click.Abort()
