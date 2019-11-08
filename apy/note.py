"""A Note wrapper class"""


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
        from apy.convert import is_generated_html
        from apy.convert import html_to_screen

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
        from apy.convert import is_generated_html
        from apy.convert import html_to_screen

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
        import click

        from apy.convert import is_generated_html
        from apy.convert import html_to_screen

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

        for key, val in self.n.items():
            if is_generated_html(val):
                key += ' (md)'

            lines.append(click.style('# ' + key, fg='blue'))
            lines.append(html_to_screen(val))
            lines.append('')

            latex_tags = self.get_lateximg_from_field(val)
            if latex_tags:
                lines.append('LaTeX sources:')
                for line in latex_tags:
                    lines.append('- ' + line)
                lines.append('')

        click.echo('\n'.join(lines))

    def print_short(self):
        """Print short version to screen"""
        import os
        import re

        import click

        from apy.convert import html_to_screen

        try:
            width = os.get_terminal_size()[0]
        except OSError:
            width = 120

        first_field = html_to_screen(self.n.values()[0])
        first_field = first_field.replace('\n', ' ')
        first_field = re.sub(r'\s\s\s+', ' ', first_field)
        first_field = first_field[:width-14] + click.style('', reset=True)

        if self.suspended:
            color = 'red'
        elif 'marked' in self.n.tags:
            color = 'yellow'
        else:
            color = 'green'

        model = f'{self.model_name[:13]:14s}'
        click.echo(click.style(model, fg=color) + first_field)


    def edit(self):
        """Edit tags and fields of current note"""
        import os
        import tempfile

        import click

        from apy.utilities import editor
        from apy.convert import markdown_file_to_notes
        from apy.convert import markdown_to_html, plain_to_html

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
        from apy.utilities import choose
        from apy.convert import is_generated_html
        from apy.convert import html_to_markdown
        from apy.convert import markdown_to_html

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
        from apy.convert import is_generated_html
        from apy.convert import html_to_markdown

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
        """Get LaTeX image tags from field"""
        from anki import latex
        links = []

        # pylint: disable=protected-access
        for match in latex.regexps['standard'].finditer(html):
            links.append(latex._imgLink(self.a.col,
                                        match.group(1),
                                        self.n.model()))
        for match in latex.regexps['expression'].finditer(html):
            links.append(latex._imgLink(self.a.col,
                                        "$" + match.group(1) + "$",
                                        self.n.model()))
        for match in latex.regexps['math'].finditer(html):
            links.append(latex._imgLink(self.a.col,
                                        "\\begin{displaymath}"
                                        + match.group(1)
                                        + "\\end{displaymath}",
                                        self.n.model()))
        # pylint: enable=protected-access

        return links
