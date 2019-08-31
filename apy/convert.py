"""Convert between formats/targets"""


def markdown_file_to_notes(filename):
    """Parse notes data from Markdown file

    The following example should adequately specify the syntax.

        //input.md
        model: Basic
        tags: marked

        # Note 1
        ## Front
        Question?

        ## Back
        Answer.

        # Note 2
        tag: silly-tag

        ## Front
        Question?

        ## Back
        Answer

        # Note 3
        model: NewModel
        markdown: false (default is true)

        ## NewFront
        FieldOne

        ## NewBack
        FieldTwo

        ## FieldThree
        FieldThree
    """
    defaults, notes = _parse_file(filename)

    # Set default markdown flag
    def_markdown = True
    if 'markdown' in defaults:
        def_markdown = defaults['markdown'] in ('true', 'yes')
        defaults.pop('markdown')
    elif 'md' in defaults:
        def_markdown = defaults['md'] in ('true', 'yes')
        defaults.pop('md')

    if 'tags' in defaults:
        defaults['tags'] = defaults['tags'].replace(',', '')

    # Ensure each note has all necessary properties
    for note in notes:
        if 'model' not in note:
            note['model'] = defaults.get('model', 'Basic')

        if 'tags' in note:
            note['tags'] = note['tags'].replace(',', '')
        else:
            note['tags'] = defaults.get('tags', 'marked')

        if 'markdown' in note:
            note['markdown'] = note['markdown'] in ('true', 'yes')
        elif 'md' in note:
            note['markdown'] = note['md'] in ('true', 'yes')
            note.pop('md')
        else:
            note['markdown'] = def_markdown

    return notes

def _parse_file(filename):
    """Get data from file"""
    import re

    defaults = {}
    notes = []
    note = {}
    codeblock = False
    field = None
    for line in open(filename, 'r'):
        if codeblock:
            if field:
                note['fields'][field] += line
            match = re.match(r'```\s*$', line)
            if match:
                codeblock = False
            continue
        else:
            match = re.match(r'```\w*\s*$', line)
            if match:
                codeblock = True
                if field:
                    note['fields'][field] += line
                continue

        if not field:
            match = re.match(r'(\w+): (.*)', line)
            if match:
                k, v = match.groups()
                k = k.lower()
                if k == 'tag':
                    k = 'tags'
                note[k] = v.strip()
                continue

        match = re.match(r'(#+)\s*(.*)', line)
        if not match:
            if field:
                note['fields'][field] += line
            continue

        level, title = match.groups()

        if len(level) == 1:
            if note:
                if field:
                    note['fields'][field] = note['fields'][field].strip()
                    notes.append(note)
                else:
                    defaults.update(note)

            note = {'title': title, 'fields': {}}
            field = None
            continue

        if len(level) == 2:
            if field:
                note['fields'][field] = note['fields'][field].strip()

            if title in note:
                import click
                click.echo(f'Error when parsing {filename}!')
                raise click.Abort()

            field = title
            note['fields'][field] = ''

    if note and field:
        note['fields'][field] = note['fields'][field].strip()
        notes.append(note)

    return defaults, notes


def markdown_to_html(plain):
    """Convert Markdown to HTML"""
    import re
    import base64
    from bs4 import BeautifulSoup
    import markdown
    from markdown.extensions.abbr import AbbrExtension
    from markdown.extensions.codehilite import CodeHiliteExtension
    from markdown.extensions.def_list import DefListExtension
    from markdown.extensions.fenced_code import FencedCodeExtension
    from markdown.extensions.footnotes import FootnoteExtension

    # Don't convert if plain text is really plain
    if re.match(r"[a-zA-Z0-9æøåÆØÅ ,.?+-]*$", plain):
        return plain

    # Fix whitespaces in input
    plain = plain.replace("\xc2\xa0", " ").replace("\xa0", " ")

    # For convenience: Fix mathjax escaping
    plain = plain.replace(r"\[", r"\\[")
    plain = plain.replace(r"\]", r"\\]")
    plain = plain.replace(r"\(", r"\\(")
    plain = plain.replace(r"\)", r"\\)")

    html = markdown.markdown(plain, extensions=[
        AbbrExtension(),
        CodeHiliteExtension(
            noclasses=True,
            linenums=False,
            pygments_style='friendly',
            guess_lang=False,
        ),
        DefListExtension(),
        FencedCodeExtension(),
        FootnoteExtension(),
        ], output_format="html5")

    html_tree = BeautifulSoup(html, 'html.parser')

    tag = _get_first_tag(html_tree)
    if not tag:
        if not html:
            # Add space to prevent input field from shrinking in UI
            html = "&nbsp;"
        html_tree = BeautifulSoup(f"<div>{html}</div>", "html.parser")
        tag = _get_first_tag(html_tree)

    # Store original text as data-attribute on tree root
    # Note: convert newlines to <br> to make text readable in the Anki viewer
    original_html = base64.b64encode(
        plain.replace("\n", "<br />").encode('utf-8')).decode()
    tag['data-original-markdown'] = original_html

    return str(html_tree)

def clean_html(html):
    """Remove some extra things from html"""
    import re
    return re.sub(r'\<style\>.*\<\/style\>', '', html, flags=re.S)

def html_to_markdown(html):
    """Extract Markdown from generated HTML"""
    import base64
    from bs4 import BeautifulSoup
    tag = _get_first_tag(BeautifulSoup(html, 'html.parser'))
    encoded_bytes = tag['data-original-markdown'].encode()
    markdown = base64.b64decode(encoded_bytes).decode('utf-8')
    return markdown.replace("<br>", "\n").replace("<br />", "\n")

def html_to_screen(html, parseable=False):
    """Convert html for printing to screen"""
    import re
    import click

    plain = html
    if is_generated_html(plain):
        plain = html_to_markdown(plain)

    plain = plain.replace(r'&lt;', '<')
    plain = plain.replace(r'&gt;', '>')
    plain = plain.replace(r'&nbsp;', ' ')

    plain = plain.replace('<br>', '\n')
    plain = plain.replace('<br/>', '\n')
    plain = plain.replace('<br />', '\n')
    plain = plain.replace('<div>', '\n')
    plain = plain.replace('</div>', '')

    # For convenience: Fix mathjax escaping
    plain = plain.replace(r"\[", r"[")
    plain = plain.replace(r"\]", r"]")
    plain = plain.replace(r"\(", r"(")
    plain = plain.replace(r"\)", r")")

    plain = re.sub(r'\<b\>\s*\<\/b\>', '', plain)

    if not parseable:
        plain = re.sub(r'\*\*(.*?)\*\*',
                       click.style(r'\1', bold=True),
                       plain, re.S)

        plain = re.sub(r'\<b\>(.*?)\<\/b\>',
                       click.style(r'\1', bold=True),
                       plain, re.S)

        plain = re.sub(r'_(.*?)_',
                       click.style(r'\1', underline=True),
                       plain, re.S)

        plain = re.sub(r'\<i\>(.*?)\<\/i\>',
                       click.style(r'\1', underline=True),
                       plain, re.S)

    return plain.strip()

def is_generated_html(html):
    """Check if text is a generated HTML"""
    from bs4 import BeautifulSoup
    if html is None:
        return False

    tag = _get_first_tag(BeautifulSoup(html, 'html.parser'))

    return (tag is not None
            and tag.attrs is not None
            and 'data-original-markdown' in tag.attrs)


def _get_first_tag(tree):
    """Get first tag among children of tree"""
    from bs4 import Tag
    for child in tree.children:
        if isinstance(child, Tag):
            return child

    return None
