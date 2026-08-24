"""Shared output helpers for CLI commands."""

from __future__ import annotations

import json
import sys

from rich.console import Console
from rich.markup import escape
from rich.table import Table

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
    bracketed text, so the reader reads a name the row does not hold. Escape
    every cell and the title. Do not escape a value before it arrives here:
    escape() is not idempotent, and a second pass shows a backslash.
    """
    table = Table(title=escape(title) if title else title, show_lines=False)
    for _, header in columns:
        table.add_column(header)

    for row in data:
        table.add_row(*(escape(str(row.get(key, ""))) for key, _ in columns))

    console.print(table)


def print_detail(data: dict, fields: list[tuple[str, str]]) -> None:
    """Render a single record as key-value pairs.

    fields: list of (key, label) tuples.

    The label is a literal, so it keeps its markup. The value is not, so it
    takes the same escape as a table cell. See print_table.
    """
    for key, label in fields:
        value = data.get(key, "")
        console.print(f"[bold]{label}:[/bold] {escape(str(value))}")


def print_json(data: object) -> None:
    """Dump data as JSON to stdout (for piping/scripting)."""
    sys.stdout.write(json.dumps(data, indent=2, default=str) + "\n")
