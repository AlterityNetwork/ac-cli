"""Admin CRM commands: destructive hard-delete escape hatches (super admin)."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_json

admin_crm_app = typer.Typer(help="Admin CRM operations (super admin only — bypasses soft-delete)")


@admin_crm_app.command("hard-delete-company")
def admin_crm_hard_delete_company(
    company_id: str = typer.Argument(..., help="Company ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Hard-delete a company. Bypasses soft-delete; unrecoverable."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(
            f"HARD DELETE company {company_id}? This bypasses soft-delete and is unrecoverable.",
            abort=True,
        )

    _api_request("delete", f"{_ADMIN}/crm/companies/{company_id}/hard")

    if json_output:
        print_json({"ok": True, "id": company_id, "action": "hard-delete-company"})
    else:
        rprint(f"[green]Hard-deleted company {company_id}[/green]")


@admin_crm_app.command("hard-delete-person")
def admin_crm_hard_delete_person(
    person_id: str = typer.Argument(..., help="Person ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Hard-delete a person. Bypasses soft-delete; unrecoverable."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(
            f"HARD DELETE person {person_id}? This bypasses soft-delete and is unrecoverable.",
            abort=True,
        )

    _api_request("delete", f"{_ADMIN}/crm/people/{person_id}/hard")

    if json_output:
        print_json({"ok": True, "id": person_id, "action": "hard-delete-person"})
    else:
        rprint(f"[green]Hard-deleted person {person_id}[/green]")
