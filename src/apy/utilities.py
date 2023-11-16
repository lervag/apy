"""Simple utility functions."""

from contextlib import contextmanager, redirect_stdout
from io import TextIOWrapper
import os
from subprocess import call
from tempfile import NamedTemporaryFile
from types import TracebackType
from typing import Any, Generator, Optional, TypeVar

import click
import readchar


class cd:
    """Context manager for changing the current working directory"""

    def __init__(self, newPath: str) -> None:
        self.newPath = os.path.expanduser(newPath)
        self.savedPath = ""

    def __enter__(self) -> None:
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        os.chdir(self.savedPath)


def editor(filepath: str) -> int:
    """Use EDITOR to edit file at given path"""
    return call([os.environ.get("EDITOR", "vim"), filepath])


def edit_text(input_text: str, prefix: str = "") -> str:
    """Use EDITOR to edit text (from a temporary file)"""
    if prefix:
        prefix = prefix + "_"

    with NamedTemporaryFile(mode="w+", prefix=prefix, suffix=".md") as tf:
        tf.write(input_text)
        tf.flush()
        editor(tf.name)
        tf.seek(0)
        edited_message = tf.read().strip()

    return edited_message


chooseType = TypeVar("chooseType")


def choose(items: list[chooseType], text: str = "Choose from list:") -> chooseType:
    """Choose from list of items"""
    click.echo(text)
    for i, element in enumerate(items):
        click.echo(f"{i+1}: {element}")
    click.echo("> ", nl=False)

    while True:
        choice = readchar.readchar()

        try:
            index = int(choice)
        except ValueError:
            continue

        try:
            reply = items[index - 1]
            click.echo(index)
            return reply
        except IndexError:
            continue


@contextmanager
def suppress_stdout() -> Generator[TextIOWrapper, Any, Any]:
    """A context manager that redirects stdout to devnull"""
    with open(os.devnull, "w") as fnull:
        with redirect_stdout(fnull) as out:
            yield out
