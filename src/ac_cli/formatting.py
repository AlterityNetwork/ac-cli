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
    """
    return _highlighter(Text(str(value)))


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
    return Text(str(_blank_if_null(value)))


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
    """
    table = Table(title=Text(title, style="table.title") if title else title, show_lines=False)
    for _, header in columns:
        table.add_column(header)

    for row in data:
        table.add_row(*(_cell(row.get(key)) for key, _ in columns))

    console.print(table)


def print_detail(data: dict, fields: list[tuple[str, str]]) -> None:
    """Render a single record as key-value pairs.

    fields: list of (key, label) tuples.

    The label is a literal, so it keeps its markup. The value is not, so it
    goes through as_text. See print_table.

    A null prints blank here for the same reason it does in a table. One record
    read two ways is one record, so `runs get` and `runs list` must not answer
    `None` and blank for the same null.
    """
    for key, label in fields:
        console.print(f"[bold]{label}:[/bold]", as_text(_blank_if_null(data.get(key))))


def print_json(data: object) -> None:
    """Dump data as JSON to stdout (for piping/scripting)."""
    sys.stdout.write(json.dumps(data, indent=2, default=str) + "\n")
