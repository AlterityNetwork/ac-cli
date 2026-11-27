"""Launchpad setup checklist commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
)
from ac_cli.commands.launchpad import _LAUNCHPAD
from ac_cli.formatting import print_json, print_table

setup_app = typer.Typer(help="Your Launchpad setup checklist")

_STEP_LABELS = {
    "mailbox": "Connect your mailbox",
    "linkedin": "Connect LinkedIn",
    "ideal_customer": "Describe your ideal customer",
    "signals_search": "Save a Signals search",
    "writing_style": "Create a writing style",
}

_STEP_FIELDS = [("step", "Step"), ("status", "Status")]


def _rows(data: dict) -> list[dict]:
    return [
        {
            "step": _STEP_LABELS.get(step.get("id", ""), step.get("id", "")),
            "status": "Done" if step.get("done") else "Open",
        }
        for step in data.get("steps", [])
    ]


@setup_app.command("get")
def setup_get(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Show your setup checklist and which steps are done."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_LAUNCHPAD}/setup").json()
    if json_output:
        print_json(data)
        return

    title = f"Setup: {data.get('completed', 0)} of {data.get('total', 0)} done"
    if data.get("dismissed"):
        title += " (dismissed)"
    print_table(_rows(data), _STEP_FIELDS, title=title)


@setup_app.command("dismiss")
def setup_dismiss(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Hide the setup checklist from your Launchpad for good."""
    set_json_mode(json_output)
    data = _api_request("post", f"{_LAUNCHPAD}/setup/dismiss").json()
    if json_output:
        print_json(data)
        return
    rprint("[green]Dismissed the setup checklist[/green]")
