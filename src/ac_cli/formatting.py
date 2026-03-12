"""Shared output helpers for CLI commands."""

import json
import sys

from rich.console import Console
from rich.table import Table

console = Console()


def print_table(
    data: list[dict],
    columns: list[tuple[str, str]],
    title: str | None = None,
) -> None:
    """Render a list of dicts as a Rich table.

    columns: list of (key, header_label) tuples.
    """
    table = Table(title=title, show_lines=False)
    for _, header in columns:
        table.add_column(header)

    for row in data:
        table.add_row(*(str(row.get(key, "")) for key, _ in columns))

    console.print(table)


def print_detail(data: dict, fields: list[tuple[str, str]]) -> None:
    """Render a single record as key-value pairs.

    fields: list of (key, label) tuples.
    """
    for key, label in fields:
        value = data.get(key, "")
        console.print(f"[bold]{label}:[/bold] {value}")


def print_json(data: object) -> None:
    """Dump data as JSON to stdout (for piping/scripting)."""
    sys.stdout.write(json.dumps(data, indent=2, default=str) + "\n")
