"""Shared output helpers for CLI commands."""

from __future__ import annotations

import json
import sys
from contextvars import ContextVar
from enum import Enum

from rich.console import Console
from rich.table import Table

console = Console()


class OutputMode(str, Enum):
    """Supported CLI output modes."""

    table = "table"
    json = "json"


_output_mode: ContextVar[OutputMode] = ContextVar("output_mode", default=OutputMode.table)


def set_output_mode(mode: OutputMode | str) -> None:
    """Set the output mode for the current command context."""
    _output_mode.set(OutputMode(mode))


def get_output_mode() -> OutputMode:
    """Return the active output mode."""
    return _output_mode.get()


def _display_row(row: dict, keys: list[str]) -> dict:
    return {key: row[key] for key in keys if key in row}


def print_table(
    data: list[dict],
    columns: list[tuple[str, str]],
    title: str | None = None,
) -> None:
    """Render a list of dicts as a Rich table.

    columns: list of (key, header_label) tuples.
    """
    if get_output_mode() == OutputMode.json:
        keys = [key for key, _ in columns]
        print_json([_display_row(row, keys) for row in data], sort_keys=True)
        return

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
    if get_output_mode() == OutputMode.json:
        print_json({key: data[key] for key, _ in fields if key in data}, sort_keys=True)
        return

    for key, label in fields:
        value = data.get(key, "")
        console.print(f"[bold]{label}:[/bold] {value}")


def print_json(data: object, *, sort_keys: bool = False) -> None:
    """Dump data as JSON to stdout (for piping/scripting)."""
    sys.stdout.write(json.dumps(data, indent=2, sort_keys=sort_keys, default=str) + "\n")
