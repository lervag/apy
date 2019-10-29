"""An Anki collection wrapper class."""


class Anki:
    """My Anki collection wrapper class."""

    def __init__(self, base=None, path=None):
        import os
        import sys
        from sqlite3 import OperationalError
        sys.path.append(os.environ.get('APY_ANKI_PATH', '/usr/share/anki'))
        import anki
        from aqt.profiles import ProfileManager

        import click

        # Update LaTeX commands
        # (based on "Edit LaTeX build process"; addon #1546037973)
        anki.latex.pngCommands = [
            ["latex", "-interaction=nonstopmode", "tmp.tex"],
            ["dvipng", "-D", "150", "-T", "tight", "-bg", "Transparent",
             "tmp.dvi", "-o", "tmp.png"]
        ]
        anki.latex.svgCommands = [
            ["lualatex", "-interaction=nonstopmode", "tmp.tex"],
            ["pdfcrop", "tmp.pdf", "tmp.pdf"],
            ["pdf2svg", "tmp.pdf", "tmp.svg"]
        ]

        self.modified = False

        # Save CWD (because Anki changes it)
        save_cwd = os.getcwd()

        if path is None:
            # Initialize a profile manager to get an interface to the profile
            # settings and main database path; also required for syncing
            self.pm = ProfileManager(base)
            self.pm.setupMeta()
            self.pm.load(self.pm.profiles()[0])

            # Load the main Anki database/collection
            path = self.pm.collectionPath()
        else:
            self.pm = None

        try:
            self.col = anki.Collection(path)
        except AssertionError:
            click.echo('Path to database is not valid!')
            click.echo(f'path = {path}')
            raise click.Abort()
        except OperationalError:
            click.echo('Database is NA/locked!')
            raise click.Abort()

        # Restore CWD (because Anki changes it)
        os.chdir(save_cwd)

        self.model_names = [m['name'] for m in self.col.models.all()]
        self.model_name_to_id = {m['name']: m['id']
                                 for m in self.col.models.all()}

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        import click

        if self.modified:
            click.echo('Database was modified.')
            if self.pm is not None and self.pm.profile['syncKey']:
                click.secho('Remember to sync!', fg='blue')
            self.col.close()


    def sync(self):
        """Sync collection to AnkiWeb"""
        if self.pm is None:
            return

        import click

        if not self.pm.profile['syncKey']:
            click.echo('No sync auth registered in profile')
            return

        import os
        from anki.sync import (Syncer, MediaSyncer,
                               RemoteServer, RemoteMediaServer)

        # Initialize servers and sync clients
        hkey = self.pm.profile['syncKey']
        hostNum = self.pm.profile.get('hostNum')
        server = RemoteServer(hkey, hostNum=hostNum)
        main_client = Syncer(self.col, server)
        media_client = MediaSyncer(self.col,
                                   RemoteMediaServer(self.col, hkey,
                                                     server.client,
                                                     hostNum=hostNum))

        # Perform main sync
        try:
            click.echo('Syncing deck ... ', nl=False)
            ret = main_client.sync()
        except Exception as e:
            if 'sync cancelled' in str(e):
                server.abort()
            click.secho('Error during sync!', fg='red')
            click.echo(e)
            raise click.Abort()

        # Parse return value
        if ret == "noChanges":
            click.echo('done (no changes)!')
        elif ret == "success":
            click.echo('done!')
        elif ret == "serverAbort":
            click.echo('aborted!')
            return
        elif ret == "fullSync":
            click.echo('aborted!')
            click.secho('Full sync required!', fg='red')
            return
        else:
            click.echo('failed!')
            click.echo(f'Message: {ret}')
            return

        # Perform media sync
        try:
            click.echo('Syncing media ... ', nl=False)
            save_cwd = os.getcwd()
            os.chdir(self.col.media.dir())
            ret = media_client.sync()
            os.chdir(save_cwd)
        except Exception as e:
            if "sync cancelled" in str(e):
                return
            raise

        if ret == "noChanges":
            click.echo('done (no changes)!')
        elif ret in ("sanityCheckFailed", "corruptMediaDB"):
            click.echo('failed!')
        else:
            click.echo('done!')


    def check_media(self):
        """Check media (will rebuild missing LaTeX files)"""
        import os
        import click
        from apy.utilities import cd

        with cd(self.col.media.dir()):
            click.echo('Checking media DB ... ', nl=False)
            nohave, unused, warnings = self.col.media.check()
            click.echo('done!')

            if not warnings + unused + nohave:
                click.secho('No unused or missing files found.', fg='white')
                return

            for warning in warnings:
                click.secho(warning, fg='red')

            for file in nohave:
                click.secho(f'Missing: {file}', fg='red')

            if unused:
                for file in unused:
                    click.secho(f'Unused: {file}', fg='red')

                if not click.confirm('Delete unused media?'):
                    return

                for file in unused:
                    if os.path.isfile(file):
                        os.remove(file)


    def find_cards(self, query):
        """Find card ids in Collection that match query"""
        return self.col.findCards(query)

    def find_notes(self, query):
        """Find notes in Collection and return Note objects"""
        from apy.note import Note
        return (Note(self, self.col.getNote(i))
                for i in self.col.findNotes(query))

    def delete_notes(self, ids):
        """Delete notes by note ids"""
        if not isinstance(ids, list):
            ids = [ids]

        self.col.remNotes(ids)
        self.modified = True


    def get_model(self, model_name):
        """Get model from model name"""
        return self.col.models.get(self.model_name_to_id.get(model_name))

    def set_model(self, model_name):
        """Set current model based on model name"""
        import click

        current = self.col.models.current()
        if current['name'] == model_name:
            return current

        model = self.get_model(model_name)
        if model is None:
            click.secho(f'Model "{model_name}" was not recognized!')
            raise click.Abort()

        self.col.models.setCurrent(model)
        return model


    def edit_model_css(self, model_name):
        """Edit the CSS part of a given model."""
        import tempfile
        import click
        from apy.utilities import editor

        model = self.get_model(model_name)

        with tempfile.NamedTemporaryFile(mode='w+', prefix='_apy_edit_',
                                         suffix='.css', delete=False) as tf:
            tf.write(model['css'])
            tf.flush()

            retcode = editor(tf.name)
            if retcode != 0:
                click.echo(f'Editor return with exit code {retcode}!')
                return

            with open(tf.name, 'r') as f:
                new_content = f.read()

        if model['css'] != new_content:
            model['css'] = new_content
            self.col.models.save(model, templates=True)
            self.modified = True


    def add_notes_with_editor(self, tags='', model_name=None, template=None):
        """Add new notes to collection with editor"""
        import os
        import tempfile

        import click

        from apy.utilities import editor, choose
        from apy.note import Note

        if isinstance(template, Note):
            input_string = template.get_template()
        else:
            if model_name is None or model_name.lower() == 'ask':
                model_name = choose(sorted(self.model_names), "Choose model:")

            model = self.set_model(model_name)

            input_lines = [
                f'model: {model_name}',
                f'tags: {tags}',
            ]

            if model_name != 'Basic':
                input_lines += ['markdown: false']

            input_lines += ['\n# Note\n']

            input_lines += [x for y in
                            [[f'## {field["name"]}', ''] for field in model['flds']]
                            for x in y]
            if model_name == 'Basic':
                input_lines.insert(-3, "**CATEGORY**")

            input_string = '\n'.join(input_lines) + '\n'

        with tempfile.NamedTemporaryFile(mode='w+',
                                         dir=os.getcwd(),
                                         prefix='note_',
                                         suffix='.md',
                                         delete=False) as tf:
            tf.write(input_string)
            tf.flush()
            retcode = editor(tf.name)

            if retcode != 0:
                click.echo(f'Editor return with exit code {retcode}!')
                return []

            return self.add_notes_from_file(tf.name)

    def add_notes_from_file(self, filename, tags=''):
        """Add new notes to collection from Markdown file"""
        from apy.convert import markdown_file_to_notes
        return self.add_notes_from_list(markdown_file_to_notes(filename),
                                        tags)

    def add_notes_from_list(self, parsed_notes, tags=''):
        """Add new notes to collection from note list (from parsed file)"""
        import click

        notes = []
        for note in parsed_notes:
            model_name = note['model']
            model = self.set_model(model_name)
            model_field_names = [field['name'] for field in model['flds']]

            field_names = note['fields'].keys()
            field_values = note['fields'].values()

            if len(field_names) != len(model_field_names):
                click.echo(f'Error: Not enough fields for model {model_name}!')
                self.modified = False
                raise click.Abort()

            for x, y in zip(model_field_names, field_names):
                if x != y:
                    click.echo('Warning: Inconsistent field names '
                               f'({x} != {y})')

            notes.append(self._add_note(field_values,
                                        f"{tags} {note['tags']}",
                                        note['markdown']))

        return notes

    def _add_note(self, fields, tags, markdown=True):
        """Add new note to collection"""
        import click

        from apy.convert import markdown_to_html, plain_to_html
        from apy.note import Note

        note = self.col.newNote()

        if markdown:
            note.fields = [markdown_to_html(x) for x in fields]
        else:
            note.fields = [plain_to_html(x) for x in fields]

        tags = tags.strip().split()
        for tag in tags:
            note.addTag(tag)

        if not note.dupeOrEmpty():
            self.col.addNote(note)
            self.modified = True
        else:
            click.secho('Dupe detected, note was not added!', fg='red')
            click.echo('Question:')
            click.echo(list(fields)[0])

        return Note(self, note)
