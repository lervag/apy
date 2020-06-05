# apy

[Anki](https://apps.ankiweb.net/index.html) is a flash card program which makes
remembering things easy. `apy` is a Python script for easily adding cards to
Anki.

**Important**:

* This is currently **WORK IN PROGRESS**, and there may still be some major
  changes.
* The current version should be compatible with Anki 2.1.26.
* This script and its author(s) are not affiliated/associated with the main
  Anki project in any way.
* Use this software entirely at your own risk. Frequent backups are encouraged.

| Version | Version note                       |
|:-------:| ---------------------------------- |
| `HEAD`  | Development branch                 |
| 0.4     | Minor improvements                 |
| 0.3     | Compatible with Anki 2.1.26        |
| 0.2     | Compatible with Anki 2.1.23        |
| 0.1     | Compatible with Anki 2.1.13        |

## Table of Contents

* [Install instructions](#install-instructions)
* [Usage](#usage)
* [Zsh completion](#zsh-completion)
* [Relevant resources](#relevant-resources)
* [Alternatives](#alternatives)

## Install instructions

To install `apy`, you can do something like this:

```bash
# Install latest version
pip install --user git+https://github.com/lervag/apy.git#egg=apy

# One can also do
git clone https://github.com/lervag/apy.git
pip install -e .
```

**Important**: `apy` uses the python API from the Anki desktop app. So please
  make sure to install the Anki source. Note that the releases on
  [Ankiweb](https://apps.ankiweb.net/#download) only include precompiled
  binaries. Ankiweb recommends that one uses these precompiled binaries, but
  for `apy` to work one needs the Anki source to be available. These are
  typically included if one installs from repositories (e.g. with `sudo apt
  install anki` or `pacman -S anki`). One may also download the source either
  from the ["Development" tab on Ankiweb](https://apps.ankiweb.net/#dev) or
  from [github](https://github.com/dae/anki).

`apy` assumes that the Anki source is available at `/usr/share/anki`. If you
put it somewhere else, then you must set the environment variable
`APY_ANKI_PATH`, e.g. `export APY_ANKI_PATH=/my/path/to/anki`.

## Usage

```sh
apy --help
```

## Configuration

`apy` loads configuration from `~/.config/apy/apy.json`. The following keys are
currently recognized:

- `pngCommands`/`svgCommands`: Set LaTeX commands to generate PNG/SVG files. This is inspired by the [Edit LaTeX build process](https://ankiweb.net/shared/info/937148547) addon to Anki.
- `base`: Specify where `apy` should look for your Anki database. This is usually something like `/home/your_name/.local/share/Anki2/`

An example configuration:

```json
{
  "base": "/home/your_name/.local/share/Anki2/",
  "pngCommands": [
    ["latex", "-interaction=nonstopmode", "tmp.tex"],
    ["dvipng", "-D", "150", "-T", "tight", "-bg", "Transparent",
      "tmp.dvi", "-o", "tmp.png"]
  ],
  "svgCommands": [
    ["lualatex", "-interaction=nonstopmode", "tmp.tex"],
    ["pdfcrop", "tmp.pdf", "tmp.pdf"],
    ["pdf2svg", "tmp.pdf", "tmp.svg"]
  ]
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

