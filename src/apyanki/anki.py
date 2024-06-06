"""An Anki collection wrapper class."""

from __future__ import annotations
import os
from pathlib import Path
import pickle
import sqlite3
import tempfile
import time
from types import TracebackType
from typing import Any, Generator, Optional, Sequence, TYPE_CHECKING, Type

from click import Abort
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from apyanki import cards
from apyanki.config import cfg
from apyanki.console import console
from apyanki.note import Note, NoteData, markdown_file_to_notes
from apyanki.utilities import cd, choose, edit_file, suppress_stdout

if TYPE_CHECKING:
    from anki.notes import NoteId
    from anki.models import NotetypeDict
    from anki.cards import CardId


class Anki:
    """My Anki collection wrapper class."""

    def __init__(
        self,
        base_path: Optional[str] = None,
        collection_db_path: Optional[str] = None,
        profile_name: Optional[str] = None,
        **_kwargs: dict[str, Any],
    ):
        self.modified = False

        self._meta = None
        self._collection_db_path = ""
        self._profile_name = profile_name
        self._profile = None

        self._init_load_profile(base_path, collection_db_path)
        self._init_load_collection()
        self._init_load_config()

        with suppress_stdout():
            self.today: int = self.col.sched.today

        self.model_name_to_id: dict[str, int] = {
            m["name"]: m["id"] for m in self.col.models.all()
        }
        self.model_names = list(self.model_name_to_id.keys())

        self.deck_name_to_id = {d["name"]: d["id"] for d in self.col.decks.all()}
        self.deck_names = self.deck_name_to_id.keys()
        self.n_decks: int = len(self.deck_names)

    def _init_load_profile(
        self, base_path_str: Optional[str], collection_db_path: Optional[str]
    ) -> None:
        """Load the Anki profile from database"""
        if base_path_str is None:
            if collection_db_path:
                self._collection_db_path = str(Path(collection_db_path).absolute())
                return

            console.print("Base path is not properly set!")
            raise Abort()

        base_path = Path(base_path_str)
        db_path = base_path / "prefs21.db"

        if not db_path.exists():
            console.print("Invalid base path!")
            console.print(f"path = {base_path.absolute()}")
            raise Abort()

        # Load metadata and profiles from database
        conn = sqlite3.connect(db_path)
        try:
            res = conn.execute(
                "select cast(data as blob) from profiles where name = '_global'"
            )
            self._meta = pickle.loads(res.fetchone()[0])

            profiles = conn.execute(
                "select name, cast(data as blob) from profiles where name != '_global'"
            ).fetchall()
        finally:
            conn.close()

        profiles_dict = {name: pickle.loads(data) for name, data in profiles}

        if self._profile_name is None:
            self._profile_name = self._meta.get(
                "last_loaded_profile_name", profiles[0][0]
            )

        self._collection_db_path = str(
            base_path / self._profile_name / "collection.anki2"
        )
        self._profile = profiles_dict[self._profile_name]

    def _init_load_collection(self) -> None:
        """Load the Anki collection"""
        # pylint: disable=import-outside-toplevel
        from anki.collection import Collection
        from anki.errors import DBError

        # Save CWD (because Anki changes it)
        save_cwd = os.getcwd()

        try:
            self.col = Collection(self._collection_db_path)
        except AssertionError as error:
            console.print("Path to database is not valid!")
            console.print(f"path = {self._collection_db_path}")
            raise Abort() from error
        except DBError as error:
            console.print("Database is NA/locked!")
            raise Abort() from error

        # Restore CWD (because Anki changes it)
        os.chdir(save_cwd)

    @staticmethod
    def _init_load_config() -> None:
        """Load custom configuration"""
        # pylint: disable=import-outside-toplevel
        from anki import latex

        # Update LaTeX commands
        # * Idea based on Anki addon #1546037973 ("Edit LaTeX build process")
        if "pngCommands" in cfg:
            latex.pngCommands = cfg["pngCommands"]
        if "svgCommands" in cfg:
            latex.svgCommands = cfg["svgCommands"]

    def __enter__(self) -> Anki:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self.modified:
            console.print("Database was modified.")
            if self._profile is not None and self._profile["syncKey"]:
                console.print("[blue]Remember to sync!")

        self.col.close()

    def sync(self) -> None:
        """Sync collection to AnkiWeb"""
        # pylint: disable=import-outside-toplevel
        from anki.sync import SyncAuth

        if self._profile is None:
            return

        hkey = self._profile.get("syncKey")
        if not hkey:
            return

        auth = SyncAuth(
            hkey=hkey,
            endpoint=self._profile.get("currentSyncUrl")
            or self._profile.get("customSyncUrl")
            or None,
            io_timeout_secs=self._profile.get("networkTimeout") or 30,
        )

        if auth is None:
            return

        with Progress(
            TextColumn(
                "Syncing {task.fields[name]} [green]…[/green] {task.description}"
            ),
            SpinnerColumn(spinner_name="point", finished_text=""),
            console=console,
        ) as progress:
            t1 = progress.add_task("", total=None, name="deck")
            t2 = progress.add_task("", total=None, name="media")

            # Perform main sync
            with suppress_stdout():
                self.col.sync_collection(auth, True)
            progress.update(t1, total=1, completed=1, description="[green]done!")

            # Perform media sync
            with cd(self.col.media.dir()):
                status_str = ""
                self.col.sync_media(auth)
                try:
                    while True:
                        time.sleep(0.01)
                        status = self.col.media_sync_status()
                        if p := status.progress:
                            status_str = f"{p.added}, {p.removed}, {p.checked}".lower()
                            progress.update(t2, description=f"[blue]({status_str})")
                        if not status.active:
                            break

                except Exception as error:
                    if "sync cancelled" in str(error):
                        progress.update(
                            t2,
                            total=1,
                            completed=1,
                            description="[yellow]cancelled!",
                        )
                        return
                    raise Abort() from error

                progress.update(
                    t2,
                    total=1,
                    completed=1,
                    description=f"[blue]({status_str}) [green]done!",
                )

    def check_media(self) -> None:
        """Check media (will rebuild missing LaTeX files)"""
        # pylint: disable=import-outside-toplevel
        from anki.notes import NoteId

        with cd(self.col.media.dir()):
            with Progress(
                TextColumn("{task.description}"),
                SpinnerColumn(spinner_name="point", finished_text=""),
                console=console,
            ) as progress:
                t1 = progress.add_task("Checking media DB [green]… ", total=None)
                output = self.col.media.check()
                progress.update(
                    t1,
                    total=1,
                    completed=1,
                    description="Checking media DB [green]… done!",
                )

            if len(output.missing) + len(output.unused) == 0:
                console.print("[white]No unused or missing files found.")
                return

            for file in output.missing:
                console.print(f"[red]Missing: {file}")

            if len(output.missing) > 0 and console.confirm("Render missing LaTeX?"):
                out = self.col.media.render_all_latex()
                if out is not None:
                    nid = NoteId(out[0])
                    console.print(f"[red]Error processing note: {nid}")

                    if console.confirm("Review note?"):
                        note = Note(self, self.col.get_note(nid))
                        note.review()

            for file in output.unused:
                console.print(f"[red]Unused: {file}")

            if len(output.unused) > 0 and console.confirm("Delete unused media?"):
                for file in output.unused:
                    if os.path.isfile(file):
                        os.remove(file)

    def find_notes(self, query: str) -> Generator[Note, None, None]:
        """Find notes in Collection and return Note objects"""
        return (
            Note(self, self.col.get_note(i)) for i in set(self.col.find_notes(query))
        )

    def delete_notes(self, ids: NoteId | list[NoteId]) -> None:
        """Delete notes by note ids"""
        if not isinstance(ids, list):
            ids = [ids]

        self.col.remove_notes(ids)
        self.modified = True

    def get_model(self, model_name: str) -> Optional[NotetypeDict]:
        """Get model from model name"""
        # pylint: disable=import-outside-toplevel
        from anki.models import NotetypeId

        model_id = self.model_name_to_id.get(model_name)
        if not isinstance(model_id, int):
            return None

        return self.col.models.get(NotetypeId(model_id))

    def set_model(self, model_name: str) -> NotetypeDict:
        """Set current model based on model name"""
        current = self.col.models.current(for_deck=False)
        if current["name"] == model_name:
            return current

        model = self.get_model(model_name)
        if model is None:
            console.print(f'Model "{model_name}" was not recognized!')
            raise Abort()

        self.col.models.set_current(model)
        return model

    def rename_model(self, old_model_name: str, new_model_name: str) -> None:
        """Rename a model"""
        model = self.get_model(old_model_name)
        if not model:
            console.print("Can't rename model!")
            console.print(f"No such model: {old_model_name}")
            raise Abort()

        # Change the name
        model["name"] = new_model_name

        # Update local storage
        self.model_name_to_id = {m["name"]: m["id"] for m in self.col.models.all()}
        self.model_names = list(self.model_name_to_id.keys())

        # Save changes
        self.col.models.update_dict(model)
        self.modified = True

    def list_tags(self) -> None:
        """List all tags"""
        table = Table(show_edge=False, box=None, header_style="bold white")
        table.add_column("tag", style="cyan")
        table.add_column("notes", style="magenta", justify="right")

        tags = [(t, len(self.col.find_notes(f"tag:{t}"))) for t in self.col.tags.all()]
        for tag, n in sorted(tags, key=lambda x: x[0]):
            table.add_row(tag, str(n))

        console.print(table)

    def change_tags(self, query: str, tags: str, add: bool = True) -> None:
        """Add/Remove tags from notes that match query"""
        note_ids = self.col.find_notes(query)
        if add:
            self.col.tags.bulk_add(note_ids, tags)
        else:
            self.col.tags.bulk_remove(note_ids, tags)

        self.modified = True

    def edit_model_css(self, model_name: str) -> None:
        """Edit the CSS part of a given model."""
        model = self.get_model(model_name)
        if not model:
            console.print(f"Could not find model: {model_name}!")
            return

        with tempfile.NamedTemporaryFile(
            mode="w+", prefix="_apy_edit_", suffix=".css", delete=False
        ) as tf:
            tf.write(model["css"])
            tf.flush()

            retcode = edit_file(tf.name)
            if retcode != 0:
                console.print(f"Editor return with exit code {retcode}!")
                return

            with open(tf.name, "r", encoding="utf8") as f:
                new_content = f.read()

        if model["css"] != new_content:
            model["css"] = new_content
            self.col.models.save(model, templates=True)
            self.modified = True

    def list_notes(self, query: str) -> None:
        """List notes that match a query"""
        for note in self.find_notes(query):
            cards.print_question(note.n.cards()[0])

    def list_cards(self, query: str, opts_display: dict[str, bool]) -> None:
        """List cards that match a query"""
        width = console.width - 1
        if opts_display.get("show_cid", False):
            width -= 15
        if opts_display.get("show_due", False):
            width -= 6
        if opts_display.get("show_type", False):
            width -= 9
        if opts_display.get("show_ease", False):
            width -= 5
        if opts_display.get("show_lapses", False):
            width -= 5
        if opts_display.get("show_model", False):
            width -= 25
        if opts_display.get("show_answer", False):
            width //= 2
            width -= 1

        table = Table(box=None, header_style="bold white")
        table.add_column("question")
        if opts_display.get("show_answer", False):
            table.add_column("answer")
        if opts_display.get("show_cid", False):
            table.add_column("cid", min_width=13)
        if opts_display.get("show_due", False):
            table.add_column("due", min_width=4)
        if opts_display.get("show_type", False):
            table.add_column("type", min_width=8)
        if opts_display.get("show_ease", False):
            table.add_column("ease", min_width=3)
        if opts_display.get("show_lapses", False):
            table.add_column("lapses", min_width=3)
        if opts_display.get("show_model", False):
            table.add_column("model", min_width=10)

        for cid in self.col.find_cards(query):
            card = self.col.get_card(cid)
            row: list[str | Text] = [
                cards.card_field_to_text(card.question(), max_width=width)
            ]
            if opts_display.get("show_answer", False):
                row += [cards.card_field_to_text(card.answer(), max_width=width)]
            if opts_display.get("show_cid", False):
                row += [str(card.id)]
            if opts_display.get("show_due", False):
                row += [str(card.due)]
            if opts_display.get("show_type", False):
                card_type = ["new", "learning", "review", "relearning"][int(card.type)]
                row += [card_type]
            if opts_display.get("show_ease", False):
                row += [str(int(card.factor / 10))]
            if opts_display.get("show_lapses", False):
                row += [str(card.lapses)]
            if opts_display.get("show_model", False):
                row += [card.note_type()["name"]]
            table.add_row(*row)

        console.print(table)

    def add_notes_with_editor(
        self,
        tags: str = "",
        model_name: Optional[str] = None,
        deck_name: Optional[str] = None,
        template: Optional[Note] = None,
    ) -> list[Note]:
        """Add new notes to collection with editor"""
        if template:
            input_string = str(template)
        else:
            if model_name is None or model_name.lower() == "ask":
                model_name = choose(sorted(self.model_names), "Choose model:")

            if deck_name is None:
                deck_name = self.col.decks.current()["name"]
            elif deck_name.lower() == "ask":
                deck_name = choose(sorted(self.deck_names), "Choose deck:")

            input_strings = [f"model: {model_name}"]

            if self.n_decks > 1:
                input_strings += [f"deck: {deck_name}"]

            input_strings += [f"tags: {tags}"]

            if model_name not in cfg["markdown_models"]:
                input_strings += ["markdown: false"]

            input_strings += ["\n# Note\n"]

            model = self.set_model(model_name)
            input_strings += [
                x
                for y in [[f'## {field["name"]}', ""] for field in model["flds"]]
                for x in y
            ]

            input_string = "\n".join(input_strings) + "\n"

        with tempfile.NamedTemporaryFile(
            mode="w+", prefix="apy_note_", suffix=".md", delete=False
        ) as tf:
            tf.write(input_string)
            tf.flush()
            retcode = edit_file(tf.name)

            if retcode != 0:
                console.print(f"Editor return with exit code {retcode}!")
                return []

            return self.add_notes_from_file(tf.name)

    def add_notes_from_file(
        self, filename: str, tags: str = "", deck: Optional[str] = None
    ) -> list[Note]:
        """Add new notes to collection from Markdown file"""
        notes = markdown_file_to_notes(filename)
        return self.add_notes_from_list(notes, tags, deck)

    def add_notes_from_list(
        self,
        parsed_notes: list[NoteData],
        tags: str = "",
        deck: Optional[str] = None,
    ) -> list[Note]:
        """Add new notes to collection from note list (from parsed file)"""
        notes = []
        for note in parsed_notes:
            if note.deck is None:
                note.deck = deck
            note.tags = f"{tags} {note.tags}"
            notes.append(note.add_to_collection(self))

        return notes

    def add_notes_single(
        self,
        field_values: list[str],
        markdown: bool,
        tags: str = "",
        model_name_in: Optional[str] = None,
        deck: Optional[str] = None,
    ) -> Note:
        """Add new note to collection from args"""
        model_name: str
        if model_name_in:
            model = self.set_model(model_name_in)
            model_name = model_name_in
        else:
            model = self.col.models.current(for_deck=False)
            model_name = model["name"]

        field_names: list[str] = [field["name"] for field in model["flds"]]
        fields = dict(zip(field_names, field_values))

        new_note = NoteData(model_name, tags, fields, markdown, deck)
        return new_note.add_to_collection(self)
