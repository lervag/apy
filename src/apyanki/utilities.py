"""Simple utility functions."""

from contextlib import contextmanager, redirect_stdout
from io import TextIOWrapper
import os
from subprocess import call
from tempfile import NamedTemporaryFile
from types import TracebackType
from typing import Any, Generator, Optional, TypeVar

import readchar

from apyanki.console import console


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


def edit_file(filepath: str) -> int:
    """Use $VISUAL or $EDITOR to edit file at given path"""
    editor = os.environ.get("VISUAL", os.environ.get("EDITOR", "vim"))
    return call([editor, filepath])


def edit_text(input_text: str, prefix: str = "") -> str:
    """Use EDITOR to edit text (from a temporary file)"""
    if prefix:
        prefix = prefix + "_"

    with NamedTemporaryFile(mode="w+", prefix=prefix, suffix=".md") as tf:
        tf.write(input_text)
        tf.flush()
        edit_file(tf.name)
        tf.seek(0)
        edited_message = tf.read().strip()

    return edited_message


chooseType = TypeVar("chooseType")


def choose(items: list[chooseType], text: str = "Choose from list:") -> chooseType:
    """Choose from list of items"""
    console.print(text)
    for i, element in enumerate(items):
        console.print(f"{i+1}: {element}")

    index = _read_number_between(1, len(items)) - 1
    return items[index]


@contextmanager
def suppress_stdout() -> Generator[TextIOWrapper, Any, Any]:
    """A context manager that redirects stdout to devnull"""
    with open(os.devnull, "w", encoding="utf8") as fnull:
        with redirect_stdout(fnull) as out:
            yield out


def _read_number_between(first: int, last: int) -> int:
    """Read number from user input between first and last (inclusive)"""
    console.print("> ", end="")
    while True:
        choice_str = ""
        choice_int = 0
        choice_digits = 0
        max_digits = len(str(last))

        while choice_digits < max_digits:
            if choice_digits > 0 and int(choice_str + "0") > last:
                break

            char = readchar.readchar()
            if char == "\n":
                break

            try:
                _ = int(char)
            except ValueError:
                continue

            next_int = int(choice_str + char)
            if next_int > 0:
                console.print(char, end="")
                choice_str += char
                choice_int = next_int
                choice_digits += 1

        if first <= choice_int <= last:
            console.print("")
            return choice_int

        console.print(f"\nPlease type number between {first} and {last}!\n> ", end="")
