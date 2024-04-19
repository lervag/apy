# apy

[Anki](https://apps.ankiweb.net/index.html) is a flash card program which makes
remembering things easy. `apy` is a Python script for easily adding cards to
Anki. It does not require Anki to be running at the same time.

### Important

* This script and its author(s) are not affiliated/associated with the main
  Anki project in any way.
* Use this software entirely at your own risk. Frequent backups are encouraged.

### Table of Contents

* [Install instructions](#install-instructions)
* [Usage](#usage)
* [Configuration](#configuration)
* [Zsh completion](#zsh-completion)
* [Changelog](#changelog)
* [Relevant resources](#relevant-resources)
* [Alternatives](#alternatives)

## Install instructions

`apy` can be installed in the "usual" way with `pip`:

```bash
pip install apyanki
```

**However**, note that installing Python packages outside [virtual
environments](https://docs.python.org/3/library/venv.html) is not recommended,
even at the user level! If you do this, then be aware that you may experience
issues due to conflicts with other packages/tools installed in the same manner.

Instead, the best way to install `apy` for normal usage is with
[`pipx`](https://pypa.github.io/pipx/). This will ensure `apy` doesn't
interfere with other Python packages already on your system.

If you don't already have `pipx`, install it with your distribution's package
manager. For instance, on Ubuntu:

```bash
sudo apt update
sudo apt install pipx
```

Then, install `apy` with:

```bash
pipx install apyanki
```

### Requirements

`apy` should work for Python 3.9 and later.

Technically, `apy` does **not** depend on any existing Anki installation, since
it pulls in a copy of the non-GUI components of Anki as a separate dependency.
However, you still need to have an Anki database with collections and profile
settings already existing on your machine, since `apy` can't create one from
nothing.

## Usage

```sh
apy --help
```

Some examples:

```sh
# Add card with interactive editor session
apy add

# Add single card with specified preset (see configuration for more info on
# presets)
apy add-single -s preset "Question/Front" "Answer/Back"

# List leech cards (will show cid values for each card). Note that the query
# should be similar to a search query in the Anki browser.
apy list -v tag:leech

# Review and possibly edit file with given cid
apy review cid:12345678
```

`apy` can be combined with editor specific configuration and workflows to
improve the process of adding and editing cards. For more information about
this, see [the Wiki](https://github.com/lervag/apy/wiki/Vim).

## Configuration

`apy` loads configuration from `~/.config/apy/apy.json`. The following keys are
currently recognized:

- `base_path`: Specify where `apy` should look for your Anki database. This is
  usually something like `/home/your_name/.local/share/Anki2/`.
- `img_viewers`: Specify a dictionary of image viewer commands. Each key is
  a file extension. The value is a command list, e.g. `['display', 'density',
  '300']` which specifies the command and its options to use for the
  corresponding key (file extension).
- `img_viewers_default`: Specify the default command to show an image. Must be
  provided as a list of the command and desired options, such as `['feh',
  '-d']`.
- `markdown_models`: Specify a list of models for which `apy` will use
  a markdown converter.
- `markdown_pygments_style`: Specify the code highlight scheme to use for
  fenced code blocks in Markdown notes. See the [Pygments
  documentation](https://pygments.org/docs/styles/) for more details.
- `pngCommands`/`svgCommands`: Set LaTeX commands to generate PNG/SVG files.
  This is inspired by the [Edit LaTeX build
  process](https://ankiweb.net/shared/info/937148547) addon to Anki.
- `presets`: Specify preset combination of model and tags for use with `apy
  add-single`.
- `profile_name`: Specify which profile to load by default.
- `query`: Specify default query for `apy list`, `apy review` and `apy tag`.
- `review_show_cards`: Whether to show list of cards by default during note
  review

An example configuration:

```json
{
  "base_path": "/home/your_name/.local/share/Anki2/",
  "profile_name": "MyAnkiProfile",
  "query": "tag:leech",
  "presets": {
    "default": { "model": "Custom", "tags": ["marked"] }
  },
  "pngCommands": [
    ["latex", "-interaction=nonstopmode", "tmp.tex"],
    ["dvipng", "-D", "150", "-T", "tight", "-bg", "Transparent",
      "tmp.dvi", "-o", "tmp.png"]
  ],
  "svgCommands": [
    ["lualatex", "-interaction=nonstopmode", "tmp.tex"],
    ["pdfcrop", "tmp.pdf", "tmp.pdf"],
    ["pdf2svg", "tmp.pdf", "tmp.svg"]
  ],
  "review_show_cards": true
}
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

## Changelog

See the [release history on GitHub](https://github.com/lervag/apy/releases).
For details, feel free to inspect the commity history.

## Relevant resources

Here are a list of relevant resources for learning how to work with the Anki
databases and code:
* [AnkiDroid: Database
  Structure](https://github.com/ankidroid/Anki-Android/wiki/Database-Structure)
* [AnkiConnect.py](https://github.com/FooSoft/anki-connect/blob/master/AnkiConnect.py)
* [The Anki Manual](https://docs.ankiweb.net)

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

* [trrc](https://github.com/Constantin1489/trrc) is a command-line program to
  add a card to Anki using AnkiConnect API.

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

### inka

[inka](https://github.com/lazy-void/inka) is a CLI utility for adding
flashcards from Markdown files to Anki.

_The Dealbreaker_: This did not exist when apy was created. It seems to be
close to what I would personally be interested in, but today I find apy solves
all (or most) of my requirements. Also, `inka` requires the AnkiConnect plugin.

### Obsidian_to_Anki

[Obsidian_to_Anki](https://github.com/Pseudonium/Obsidian_to_Anki) is a plugin to add flashcards from a text or markdown file to Anki. It can also be run from the command-line as a python script. Built with Obsidian markdown syntax in mind.

_The Dealbreaker_: Requires AnkiConnect.

### Markdown2Anki

[Markdown2Anki](https://github.com/Mochitto/Markdown2Anki) is a Python script that allows you to easily format your cards
using Markdown syntax, and then import them into Anki while retaining the
structure you gave them.

As many other alternatives, you need to manually import cards. It may provide
support for AnkiConnect.

## Contributing

The following is a short and simple guide to getting started with contributing
and developing the `apy` code.

### Setup

This project uses [Poetry](https://python-poetry.org/) as the build system and
to manage dependencies.

Install Poetry first if you don't have it already. Fork the repository, then
clone your fork and install a local development build of the project using
Poetry.

```sh
# Clone the forked repo
git clone git@github.com:<username>/apy.git
cd apy/

# Install the project with Poetry
poetry install
```

Poetry will create a virtual environment for you (see
[here](https://python-poetry.org/docs/configuration/#virtualenvsin-project) for
where the environment is created). You can either activate this environment
yourself then issue commands in the usual way, or you can prefix your commands
with `poetry run`. Example:

```sh
poetry run apy --version
```

### Tests

To run the tests, activate the virtual environment and run:

```sh
pytest
```

Alternatively, without activating the environment:

```sh
poetry run pytest
```

### Linting

To format the code, run:

```sh
poetry run black .
```

To type-check the code, run:

```sh
poetry run mypy src
```
