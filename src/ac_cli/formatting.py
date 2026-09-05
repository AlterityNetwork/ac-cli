"""Shared output helpers for CLI commands."""

from __future__ import annotations

import json
import sys

from rich.console import Console
from rich.highlighter import ReprHighlighter
from rich.table import Table
from rich.text import Text

console = Console()

# as_text renders through rprint at some call sites, and through the console
# above at others. It owns a highlighter so the two agree.
_highlighter = ReprHighlighter()

# Every C0 and C1 control character except the tab, the newline and the
# carriage return. The tab and the newline carry text, and _visible reads the
# carriage return as a line ending. The rest carry commands: `\x1b` opens an
# ANSI sequence, and `\u009b` opens one on its own.
_CONTROL_CHARS = set(range(0x00, 0x20)) - {0x09, 0x0A, 0x0D} | {0x7F} | set(range(0x80, 0xA0))
_CONTROL_TABLE = {code: f"\\x{code:02x}" for code in _CONTROL_CHARS}


def _visible(value: object) -> str:
    r"""Answers the value as text that the terminal reads as text.

    A markup escape does not stop a control byte. A value that holds
    `\x1b[41m` repaints the terminal under a str, under `rich.markup.escape`
    and under a bare Text. An API value must not repaint the terminal, so each
    control byte renders as its own escape. The reader sees what the value
    holds, and the terminal does not act on it.

    The tab and the newline stay, because both carry text.

    A mail body ends each line with CRLF, so the carriage return is a line
    ending and not a cursor move. It becomes a newline. Rich removes it too
    (`rich.control.STRIP_CONTROL_CODES`), so this keeps what a reader saw
    before and does not depend on that list.

    Args:
        value: What the record holds, of any type.

    Returns:
        The value as text, with each control byte replaced by its escape.
    """
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    return text.translate(_CONTROL_TABLE)


def as_text(value: object) -> Text:
    """Wrap a value the CLI did not write, for a print that reads markup.

    A Text never reaches the markup parser, so a value that holds `[/beta]`
    prints as it is. `rich.markup.escape` closes the same fault, but it
    appends a second backslash to a value that ends in one.

    The console highlights a str argument but not a Text, so the highlighter
    runs here. A number, a URL and a None keep the colour they had. It runs
    always, so a console that sets `highlight=False` does not stop it.

    A Text also stops the emoji substitution. A value that holds `:rocket:`
    prints those eight characters. That is the same rule as the brackets:
    print what the value holds.

    A control byte renders as its escape. See _visible.
    """
    return _highlighter(Text(_visible(value)))


# The character that holds the place of a value while the template parses. The
# template is text the CLI wrote, and no call site writes a null byte.
_SLOT = "\x00"


def styled(template: str, *values: object) -> Text:
    """Render a markup template whose values are not markup.

    The call site writes the template, so the template keeps its tags. The API
    writes the values, so each value prints as it is. `{}` marks each place a
    value takes.

    This replaces an f-string that mixed the two. `f"[green]Created:[/green]
    {name}"` gave the markup parser a name the CLI did not write, so a name
    that holds `[/beta]` raised MarkupError and the command exited 1 with no
    output.

    The template is not a format string. A lone `{` or `}` is that character,
    and only `{}` marks a place.

    A value keeps the style of the place it takes, so `[bold]{}[/bold]` prints
    a bold value as the f-string did.

    Args:
        template: The markup the call site wrote, with `{}` for each value.
        *values: One value for each `{}`, in order.

    Returns:
        A Text the console prints as it is.

    Raises:
        ValueError: The count of values is not the count of places. A wrong
          count drops a value in silence, and the reader cannot see the loss.
    """
    text = Text.from_markup(template.replace("{}", _SLOT))
    plain = text.plain
    offsets: list[int] = []
    start = plain.find(_SLOT)
    while start != -1:
        offsets += [start, start + 1]
        start = plain.find(_SLOT, start + 1)

    places = len(offsets) // 2
    if places != len(values):
        raise ValueError(f"styled() got {len(values)} values for {places} places")

    # divide answers one piece for each offset boundary, so the pieces read
    # literal, place, literal, place, ... literal. Each place is one character
    # wide, and it carries the styles of the tags that hold it.
    pieces = list(text.divide(offsets))
    out = Text()
    for index, piece in enumerate(pieces):
        if index % 2 == 0:
            out.append_text(piece)
            continue
        value = as_text(values[index // 2])
        for span in piece.spans:
            value.stylize(span.style)
        out.append_text(value)
    return out


def _blank_if_null(value: object) -> object:
    """Answers the empty string for a null, and the value itself otherwise.

    A JSON null and an absent key say the same thing: the record carries no
    value there. The test is `is None`, so a `0` or a `False` keeps its value.

    Args:
        value: What the record holds for that field, or None.

    Returns:
        The value, or "" when it is None.
    """
    return "" if value is None else value


def _cell(value: object) -> Text:
    """Renders one table cell, with a null and an absent key alike.

    Args:
        value: What the row holds for that column, or None.

    Returns:
        A Text the console prints literally. See print_table.
    """
    return Text(_visible(_blank_if_null(value)))


def print_table(
    data: list[dict],
    columns: list[tuple[str, str]],
    title: str | None = None,
) -> None:
    """Render a list of dicts as a Rich table.

    columns: list of (key, header_label) tuples.

    The console reads rich markup, and no caller writes the cells. A company
    name that holds `[/beta]` raises MarkupError, and the command then exits 1
    with no output. One that holds `[formerly Beta]` renders without the
    bracketed text, so the reader reads a name the row does not hold.

    Wrap each cell and the title in Text. The console prints a Text literally,
    so no cell reaches the markup parser. `rich.markup.escape` closes the same
    two faults, but it appends a second backslash to a value that ends in one,
    and the parser does not remove it again.

    A Text also stops the emoji substitution, so a cell or a title that holds
    `:rocket:` prints those eight characters. That is the same rule as the
    brackets: print what the row holds.

    Table applies `table.title` to a str title only, so the Text title names
    that style itself. For the same reason a `title_style` argument would not
    reach a Text title. Do not add one without reading Table.render_annotation.

    ⚠️ **A null cell prints as blank, and not as `None`.** A JSON null and an
    absent key say the same thing: the row carries no value for that column.
    The test is `is None`, so a cell that holds `0` or `False` keeps its value.

    ⚠️ **Every column folds, because the default `ellipsis` destroys an id.**
    Rich divides a line on a space. A tool id, a run id and a UUID hold no
    space. Each is therefore one word that overflows its column. The default
    then cuts the tail off with an ellipsis. That id is the value a caller
    copies into the next command, and a cut id is unusable. `fold` divides the
    word at the column edge instead. The whole value stays on screen over two
    or more lines. A cell that already fits renders as before, and so does
    prose: `fold` changes one word that is wider than its column.

    `no_wrap=False` is not the same fix. It is already the default, and it
    decides whether a cell wraps at all, not how one long word is divided.

    ⚠️ **`show_lines` is on, because a folded row is more than one line tall.**
    A folded id makes a row three lines tall. Without a rule between the rows
    the reader cannot see where one row ends. A table that folds nothing pays
    one rule line for each row. That cost is less harm than a cut id.
    """
    table = Table(title=Text(title, style="table.title") if title else title, show_lines=True)
    for _, header in columns:
        table.add_column(header, overflow="fold")

    for row in data:
        table.add_row(*(_cell(row.get(key)) for key, _ in columns))

    console.print(table)


def print_detail(data: dict, fields: list[tuple[str, str]]) -> None:
    """Render a single record as key-value pairs.

    fields: list of (key, label) tuples.

    Neither the label nor the value reaches the markup parser. The label is a
    literal at every call site, and one rule for the whole line is one rule to
    read. See print_table.

    A null prints blank here for the same reason it does in a table. One record
    read two ways is one record, so `runs get` and `runs list` must not answer
    `None` and blank for the same null.
    """
    for key, label in fields:
        console.print(styled("[bold]{}:[/bold]", label), as_text(_blank_if_null(data.get(key))))


def print_json(data: object) -> None:
    """Dump data as JSON to stdout (for piping/scripting)."""
    sys.stdout.write(json.dumps(data, indent=2, default=str) + "\n")
