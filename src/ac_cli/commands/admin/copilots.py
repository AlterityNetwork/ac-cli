"""Admin copilot seat commands.

A copilot seat is a membership row whose role is copilot. A superadmin gives a
copilot user a seat in each customer organization the copilot works in.
"""

from __future__ import annotations

import typer
from rich import print as rprint
from rich.text import Text

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_json, print_table

copilots_app = typer.Typer(help="Copilot seat management")

_COPILOTS = f"{_ADMIN}/copilots"


@copilots_app.command("list")
def copilots_list(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """List copilots and the organizations each one holds a seat in."""
    set_json_mode(json_output)
    resp = _api_request("get", _COPILOTS)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    rows = data.get("data", [])
    if not rows:
        rprint("[dim]No copilots assigned.[/dim]")
        return

    flat = [
        {
            "user_id": row.get("user_id"),
            "email": row.get("email"),
            "name": " ".join(
                part for part in (row.get("first_name"), row.get("last_name")) if part
            ),
            "organizations": ", ".join(
                org.get("name") or org.get("organization_id", "")
                for org in row.get("organizations", [])
            ),
        }
        for row in rows
    ]
    print_table(
        flat,
        [
            ("email", "Email"),
            ("name", "Name"),
            ("user_id", "User ID"),
            ("organizations", "Organizations"),
        ],
        title=f"Copilots ({len(rows)})",
    )


@copilots_app.command("assign")
def copilots_assign(
    user_id: str = typer.Argument(..., help="User ID of the copilot"),
    org_id: str = typer.Argument(..., help="Organization ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Give a user a copilot seat in an organization."""
    set_json_mode(json_output)
    _api_request("post", f"{_COPILOTS}/{user_id}/organizations/{org_id}")
    if json_output:
        print_json({"ok": True, "user_id": user_id, "organization_id": org_id})
        return
    rprint(Text(f"Assigned copilot {user_id} to organization {org_id}", style="green"))


@copilots_app.command("unassign")
def copilots_unassign(
    user_id: str = typer.Argument(..., help="User ID of the copilot"),
    org_id: str = typer.Argument(..., help="Organization ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Remove a copilot seat from an organization."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(
            f"Remove the copilot seat of user {user_id} in organization {org_id}?",
            abort=True,
        )

    _api_request("delete", f"{_COPILOTS}/{user_id}/organizations/{org_id}")
    if json_output:
        print_json({"ok": True, "user_id": user_id, "organization_id": org_id})
        return
    rprint(Text(f"Unassigned copilot {user_id} from organization {org_id}", style="green"))
