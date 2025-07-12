"""Simple utility functions."""

import os
import shutil
from collections.abc import Generator
from contextlib import contextmanager, redirect_stdout
from io import TextIOWrapper
from subprocess import PIPE, Popen, call
from tempfile import NamedTemporaryFile
from types import TracebackType
from typing import Any, TypeVar

import readchar
from click import Abort

from apyanki.console import console


class cd:
    """Context manager for changing the current working directory"""

    def __init__(self, newPath: str) -> None:
        self.newPath: str = os.path.expanduser(newPath)
        self.savedPath: str = ""

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


def edit_file(filepath: str) -> int:
    """Use $VISUAL or $EDITOR to edit file at given path"""
    editor = os.environ.get("VISUAL", os.environ.get("EDITOR", "vim"))
    return call([editor, filepath])


def edit_text(input_text: str, prefix: str = "") -> str:
    """Use EDITOR to edit text (from a temporary file)"""
    if prefix:
        prefix = prefix + "_"

    with NamedTemporaryFile(mode="w+", prefix=prefix, suffix=".md") as tf:
        _ = tf.write(input_text)
        tf.flush()
        _ = edit_file(tf.name)
        _ = tf.seek(0)
        edited_message = tf.read().strip()

    return edited_message


chooseType = TypeVar("chooseType")


def choose(items: list[chooseType], text: str = "Choose from list:") -> chooseType:
    """Choose from list of items"""
    if shutil.which("fzf"):
        return choose_with_fzf(items, text)
    return choose_from_list(items, text)


def choose_with_fzf(
    items: list[chooseType], text: str = "Choose from list:"
) -> chooseType:
    """Choose from list of items with fzf"""
    fzf_input = "\n".join(map(str, items)).encode("utf-8")

    fzf_process = Popen(
        ["fzf", "--prompt", f"{text}> "],
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
    )
    stdout, _ = fzf_process.communicate(input=fzf_input)

    if fzf_process.returncode != 0:
        raise Abort()

    selected_item_str = stdout.decode("utf-8").strip()

    # Find the selected item in the original list to preserve its type
    for item in items:
        if str(item) == selected_item_str:
            return item

    # This should not be reached if fzf returns a valid selection
    raise Abort()


def choose_from_list(
    items: list[chooseType], text: str = "Choose from list:"
) -> chooseType:
    """Choose from list of items"""
    console.print(text)
    for i, element in enumerate(items):
        console.print(f"{i + 1}: {element}")

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
