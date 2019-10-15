# apy

[Anki](https://apps.ankiweb.net/index.html) is a flash card program which makes
remembering things easy. `apy` is a Python script for easily adding cards to
Anki.

Note:
* Use this software entirely at your own risk. Frequent backups are encouraged.
* This is currently **WORK IN PROGRESS**, and there may still be some major
  changes.
* This script and its author(s) are not affiliated/associated with the main
  Anki project in any way.

**Table of Contents**

- [Install instructions](#install-instructions)
- [Usage](#usage)
- [Zsh completion](#zsh-completion)
- [Relevant resources](#relevant-resources)
- [Alternatives](#alternatives)

## Install instructions

To install `apy`, do:

```bash
# For users
pip install .

# For developers
pip install -e .
```

**Important**: `apy` uses the python API from the Anki desktop app. So please
  make sure to install [Anki](https://apps.ankiweb.net/#download). If Anki
  desktop is not available, you should see errors like `ModuleNotFoundError: No
  module named 'anki'`

## Usage

```sh
apy --help
```

## Zsh completion

There is also a zsh completion file available. To use it, one may symlink or
copy it to a location that is already in ones `fpath` variable, or one may add
the `apy/completion` directory to the `fpath` list.

As an example, one may first symlink the `_apy` file:

```sh
mkdir -p ~/.local/zsh-functions
ln -s /path/to/apy/completion/_apy ~/.local/zsh-functions
```

Then add the following line to ones `.zshrc` file:

```sh
fpath=($HOME/.local/zsh-functions $fpath)
```

## Relevant resources

Here are a list of relevant resources for learning how to work with the Anki
databases and code:
* [AnkiDroid: Database
  Structure](https://github.com/ankidroid/Anki-Android/wiki/Database-Structure)
* [AnkiConnect.py](https://github.com/FooSoft/anki-connect/blob/master/AnkiConnect.py)
* [The Anki Manual](https://apps.ankiweb.net/docs/manual.html)

## Alternatives

Here are some alternatives to `apy` from which I've drawn inspiration. I've
also added a short note on why I did not just settle for the alternative.

### Ankiconnect

[Ankiconnect](https://foosoft.net/projects/anki-connect/) is an Anki plugin [2055492159](https://ankiweb.net/shared/info/2055492159)) hosted on [github](https://github.com/FooSoft/anki-connect).

> Ankiconnect enables external applications to communicate with Anki over
> a network interface. The exposed API makes it possible to execute queries
> against the user’s card deck, automatically create new vocabulary and Kanji
> flash cards, and more.

A couple of relevant applications that use Ankiconnect:

* [Anki Quick Adder](https://codehealthy.com/chrome-anki-quick-adder/):
  A Chrome extension to add words to Anki desktop quickly.

* [Anki-editor](https://github.com/louietan/anki-editor) is an emacs plugin for
  making Anki cards with Org.

* [anki-cli](https://github.com/towercity/anki-cli) is a simple nodejs based
  command-line interface for Anki.

_The Dealbreaker_: I wanted a script that does not require Anki to be running.

### Anki::Import - Anki note generation made easy

[Anki::Import](https://github.com/sdondley/Anki-Import) (see also
[here](https://metacpan.org/pod/Anki::Import)) allows one to "Efficiently
generate Anki notes with your text editor for easy import into Anki". Quote:

> Inputting notes into Anki can be a tedious chore. Anki::Import lets you you
> generate Anki notes with your favorite text editor (e.g. vim, BBEdit, Atom,
> etc.) so you can enter formatted notes into Anki's database more
> efficiently.

_The Dealbreaker_: This sounds very good, except there are too many steps.
I didn't want to have to open Anki desktop. It should work flawlessly directly
from the terminal.

### AnkiVim

[AnkiVim](https://github.com/MFreidank/AnkiVim) may be used to "Use vim to
rapidly write textfiles immediately importable into anki(1)."

_The Dealbreaker_: Similar to `Anki::Import`: I didn't want to have to open
Anki desktop. It should work flawlessly directly from the terminal.

### Knowledge (Vim plugin)

[Knowledge](https://github.com/tbabej/knowledge) is a Vim plugin for generating
flash cards to either Anki or Mnemosyne.

_The Dealbreaker_: It has [a single, open
issue](https://github.com/tbabej/knowledge/issues/1), which seems to indicate
that the application does not work very well and/or is not well maintained.

### Ankisync

[Ankisync](https://github.com/patarapolw/ankisync) seems somewhat promising, in
that it exposes an API for working with Anki collections from Python. It is
a successor to [AnkiTools](https://github.com/patarapolw/AnkiTools), which is
stated to be "an Anki *.apkg and collection.anki2 reader and editor".

_The Dealbreaker_: It does not include any features to add or edit notes (as
far as I could tell).

### Genanki

[Genanki](https://github.com/kerrickstaley/genanki) is a library for generating
Anki decks.

_The Dealbreaker_: It is quite close to being something I wanted, except that
it needs to run as a plugin to Anki desktop to generate notes to a local
collection. It does not seem to allow editing/adding to a local collection
outside of Anki desktop.
