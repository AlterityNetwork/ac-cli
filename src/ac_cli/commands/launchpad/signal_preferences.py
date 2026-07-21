"""Launchpad signal-preferences commands."""

from __future__ import annotations

from typing import Any

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
)
from ac_cli.commands.launchpad import _LAUNCHPAD
from ac_cli.formatting import print_detail, print_json

signal_preferences_app = typer.Typer(help="Org signal-feed preferences for the Launchpad")

_DETAIL_FIELDS = [
    ("sort_mode", "Sort mode"),
    ("group_by_saved_search", "Group by saved search"),
    ("score_threshold", "Score threshold"),
    ("score_direction", "Score direction"),
]

# The four config keys, in order, used to rebuild the full object on `set`.
_CONFIG_KEYS = (
    "sort_mode",
    "group_by_saved_search",
    "score_threshold",
    "score_direction",
)


@signal_preferences_app.command("get")
def signal_preferences_get(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Show the current org signal preferences."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_LAUNCHPAD}/signal-preferences")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, _DETAIL_FIELDS)


@signal_preferences_app.command("set")
def signal_preferences_set(
    ctx: typer.Context,
    sort_mode: str | None = typer.Option(None, "--sort-mode", help="hottest | recent"),
    group: bool | None = typer.Option(
        None,
        "--group/--no-group",
        help="Group the feed by saved search",
    ),
    score_threshold: int | None = typer.Option(
        None, "--score-threshold", help="Company lead-score cutoff"
    ),
    clear_threshold: bool = typer.Option(
        False, "--clear-threshold", help="Remove the score threshold (show all scores)"
    ),
    score_direction: str | None = typer.Option(None, "--score-direction", help="above | below"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update org signal preferences.

    Only the flags you pass change; the rest keep their current server values.
    Pass --clear-threshold to remove the score filter entirely.
    """
    set_json_mode(json_output)

    if (
        all(v is None for v in (sort_mode, group, score_threshold, score_direction))
        and not clear_threshold
    ):
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    # Start from the current server values so unset flags are preserved.
    current = _api_request("get", f"{_LAUNCHPAD}/signal-preferences").json()
    body: dict[str, Any] = {key: current.get(key) for key in _CONFIG_KEYS}

    if sort_mode is not None:
        body["sort_mode"] = sort_mode
    if group is not None:
        body["group_by_saved_search"] = group
    if clear_threshold:
        body["score_threshold"] = None
    elif score_threshold is not None:
        body["score_threshold"] = score_threshold
    if score_direction is not None:
        body["score_direction"] = score_direction

    resp = _api_request("put", f"{_LAUNCHPAD}/signal-preferences", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint("[green]Updated signal preferences[/green]")
