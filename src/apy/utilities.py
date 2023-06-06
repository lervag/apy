"""Simple utility functions."""

import os
from tempfile import NamedTemporaryFile
from subprocess import call
from typing import Any
from types import TracebackType

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
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
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


def choose(items: list[Any], text: str = "Choose from list:") -> Any:
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
