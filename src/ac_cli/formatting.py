"""Shared output helpers for CLI commands."""

from __future__ import annotations

import json
import sys

from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()


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
    """
    table = Table(title=Text(title) if title else title, show_lines=False)
    for _, header in columns:
        table.add_column(header)

    for row in data:
        table.add_row(*(Text(str(row.get(key, ""))) for key, _ in columns))

    console.print(table)


def print_detail(data: dict, fields: list[tuple[str, str]]) -> None:
    """Render a single record as key-value pairs.

    fields: list of (key, label) tuples.

    The label is a literal, so it keeps its markup. The value is not, so it
    prints as a Text. See print_table.
    """
    for key, label in fields:
        value = data.get(key, "")
        console.print(f"[bold]{label}:[/bold]", Text(str(value)))


def print_json(data: object) -> None:
    """Dump data as JSON to stdout (for piping/scripting)."""
    sys.stdout.write(json.dumps(data, indent=2, default=str) + "\n")
