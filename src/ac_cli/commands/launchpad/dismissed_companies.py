"""Launchpad dismissed-companies commands.

Clearing hides a company from the Launchpad signal feed for the whole
organization until a signal is discovered after the clear, so it is a snooze
rather than a permanent hide. Distinct from `crm companies mark-actioned`
("Mark done"), which is sticky and drives the Sonar inbox worklist.
"""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.launchpad import _LAUNCHPAD
from ac_cli.formatting import print_json, styled

dismissed_companies_app = typer.Typer(help="Companies cleared from the Launchpad signal feed")

# Paths are built inline from `_LAUNCHPAD` (as in signal_preferences.py) rather
# than via a local `_BASE`: audit_endpoints.py resolves f-strings by constant
# NAME, and a generic `_BASE` collides with another command module's, which made
# the audit report these commands against the wrong path.

# Mirrors the API's request-model cap, so an oversized batch fails here with a
# readable message instead of coming back as an opaque 422.
_MAX_IDS = 200


def _fail(detail: str, json_output: bool) -> None:
    """Emit a client-side validation failure and exit 1.

    These checks run before any request, so they never reach `_handle_error`.
    They still have to honour `--json`, or an agent gets Rich markup on stdout
    where it expects a parseable error object.
    """
    if json_output:
        print_json({"error": True, "status_code": 1, "detail": detail})
    else:
        rprint(styled("[red]{}[/red]", detail))
    raise typer.Exit(code=1)


def _split_ids(ids: str, json_output: bool) -> list[str]:
    """Split a comma-separated id list, deduplicating while preserving order.

    Matches the `--ids` shape used by the sibling batch commands (`crm companies
    mark-actioned` and friends), which is what an agent reading the command
    reference will reach for.
    """
    id_list = list(dict.fromkeys(i.strip() for i in ids.split(",") if i.strip()))
    if not id_list:
        _fail("No IDs provided", json_output)
    if len(id_list) > _MAX_IDS:
        _fail(f"Too many IDs: {len(id_list)} (max {_MAX_IDS} per call)", json_output)
    return id_list


@dismissed_companies_app.command("clear")
def dismissed_companies_clear(
    ctx: typer.Context,
    ids: str = typer.Option(..., "--ids", help=f"Comma-separated CRM company IDs (max {_MAX_IDS})"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Clear companies from the Launchpad until a newer signal is discovered."""
    set_json_mode(json_output)

    id_list = _split_ids(ids, json_output)

    if not should_skip_confirm(yes):
        typer.confirm(
            f"Clear {len(id_list)} company(ies) from the Launchpad for the whole organization?",
            abort=True,
        )

    resp = _api_request("post", f"{_LAUNCHPAD}/dismissed-companies", json={"ids": id_list})

    data = resp.json()
    if json_output:
        print_json(data)
        return

    rprint(styled("[green]Cleared {} company(ies)[/green]", data.get("dismissed_count", 0)))


@dismissed_companies_app.command("restore")
def dismissed_companies_restore(
    ctx: typer.Context,
    ids: str = typer.Option(..., "--ids", help=f"Comma-separated CRM company IDs (max {_MAX_IDS})"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Put cleared companies back into the Launchpad signal feed."""
    set_json_mode(json_output)

    id_list = _split_ids(ids, json_output)

    resp = _api_request("post", f"{_LAUNCHPAD}/dismissed-companies/restore", json={"ids": id_list})

    data = resp.json()
    if json_output:
        print_json(data)
        return

    rprint(styled("[green]Restored {} company(ies)[/green]", data.get("restored_count", 0)))
