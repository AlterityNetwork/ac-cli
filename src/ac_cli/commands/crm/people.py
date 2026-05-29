"""CRM people commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _get_org_id,
    _require_id,
    _resolve_company_id,
    _resolve_contact_id,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.crm import _CRM, _api_request, _build_body
from ac_cli.formatting import print_detail, print_json, print_table

people_app = typer.Typer(help="People/contact operations")


@people_app.command("list")
def people_list(
    ctx: typer.Context,
    company_id: str | None = typer.Option(None, "--company-id", help="Filter by company"),
    limit: int = typer.Option(100, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    approved: bool | None = typer.Option(
        None,
        "--approved/--unapproved",
        help="Filter by approval state (--approved = human-vetted, "
        "--unapproved = not yet approved)",
    ),
    added_by_type: str | None = typer.Option(
        None, "--added-by-type", help="Filter by who added: 'user' or 'agent'"
    ),
    added_by_user: str | None = typer.Option(
        None, "--added-by-user", help="Filter to records added by a specific user ID"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """List people."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset}
    if company_id:
        params["company_id"] = company_id
    if approved is not None:
        params["approved"] = approved
    if added_by_type:
        params["added_by_type"] = added_by_type
    if added_by_user:
        params["added_by_user_id"] = added_by_user

    resp = _api_request("get", f"{_CRM}/people", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data.get("data", []),
        [
            ("full_name", "Name"),
            ("email", "Email"),
            ("current_title", "Title"),
            ("lifecycle_stage", "Stage"),
            ("id", "ID"),
        ],
        title=f"People ({data.get('total', '?')} total)",
    )


@people_app.command("get")
def people_get(
    ctx: typer.Context,
    person_id: str | None = typer.Argument(None, help="Person ID"),
    person_name: str | None = typer.Option(
        None, "--person-name", help="Person name (auto-resolves to ID)"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a person by ID or name."""
    set_json_mode(json_output)
    resolved = _require_id(
        _resolve_contact_id(person_id, person_name, _CRM),
        id_label="person ID",
        name_flag="--person-name",
    )
    resp = _api_request("get", f"{_CRM}/people/{resolved}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("full_name", "Name"),
            ("email", "Email"),
            ("current_title", "Title"),
            ("current_company_text", "Company"),
            ("lifecycle_stage", "Stage"),
            ("location", "Location"),
            ("country", "Country"),
            ("tags", "Tags"),
            ("summary", "Summary"),
            ("created_at", "Created"),
            ("updated_at", "Updated"),
            ("created_by_user_id", "Added By (user)"),
            ("approved_by", "Approved By"),
            ("approved_at", "Approved At"),
        ],
    )


@people_app.command("create")
def people_create(
    ctx: typer.Context,
    email: str | None = typer.Option(None, help="Email address"),
    full_name: str | None = typer.Option(None, "--full-name", help="Full name"),
    current_title: str | None = typer.Option(None, "--current-title", help="Job title"),
    company_id: str | None = typer.Option(None, "--company-id", help="Company ID"),
    company_name: str | None = typer.Option(
        None, "--company-name", help="Company name (auto-resolves to ID)"
    ),
    lifecycle_stage: str | None = typer.Option(None, "--lifecycle-stage", help="Lifecycle stage"),
    tags: str | None = typer.Option(None, help="Comma-separated tags"),
    linkedin_url: str | None = typer.Option(None, "--linkedin-url", help="LinkedIn URL"),
    location: str | None = typer.Option(None, help="Location"),
    country: str | None = typer.Option(None, help="Country"),
    phone_number: str | None = typer.Option(
        None, "--phone-number", help="Phone (E.164, e.g. +14155551234)"
    ),
    phone_source: str | None = typer.Option(
        None, "--phone-source", help="Provider/source of phone value"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new person."""
    set_json_mode(json_output)
    resolved_company = _resolve_company_id(company_id, company_name, _CRM)
    body = _build_body(
        email=email,
        full_name=full_name,
        current_title=current_title,
        company_id=resolved_company,
        lifecycle_stage=lifecycle_stage,
        tags=tags,
        linkedin_url=linkedin_url,
        location=location,
        country=country,
        phone_number=phone_number,
        phone_source=phone_source,
    )

    body["organization_id"] = _get_org_id()

    resp = _api_request("post", f"{_CRM}/people", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        label = data.get("full_name") or data.get("email") or data["id"]
        rprint(f"[green]Created person:[/green] {label} ({data['id']})")


@people_app.command("update")
def people_update(
    ctx: typer.Context,
    person_id: str | None = typer.Argument(None, help="Person ID"),
    person_name: str | None = typer.Option(
        None, "--person-name", help="Person name (auto-resolves to ID)"
    ),
    email: str | None = typer.Option(None, help="Email address"),
    full_name: str | None = typer.Option(None, "--full-name", help="New full name"),
    current_title: str | None = typer.Option(None, "--current-title", help="Job title"),
    company_id: str | None = typer.Option(None, "--company-id", help="Company ID"),
    company_name: str | None = typer.Option(
        None, "--company-name", help="Company name (auto-resolves to ID)"
    ),
    lifecycle_stage: str | None = typer.Option(None, "--lifecycle-stage", help="Lifecycle stage"),
    tags: str | None = typer.Option(None, help="Comma-separated tags"),
    linkedin_url: str | None = typer.Option(None, "--linkedin-url", help="LinkedIn URL"),
    location: str | None = typer.Option(None, help="Location"),
    country: str | None = typer.Option(None, help="Country"),
    phone_number: str | None = typer.Option(
        None, "--phone-number", help="Phone (E.164, e.g. +14155551234)"
    ),
    phone_source: str | None = typer.Option(
        None, "--phone-source", help="Provider/source of phone value"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update an existing person."""
    set_json_mode(json_output)
    resolved = _require_id(
        _resolve_contact_id(person_id, person_name, _CRM),
        id_label="person ID",
        name_flag="--person-name",
    )
    resolved_company = _resolve_company_id(company_id, company_name, _CRM)
    body = _build_body(
        email=email,
        full_name=full_name,
        current_title=current_title,
        company_id=resolved_company,
        lifecycle_stage=lifecycle_stage,
        tags=tags,
        linkedin_url=linkedin_url,
        location=location,
        country=country,
        phone_number=phone_number,
        phone_source=phone_source,
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_CRM}/people/{resolved}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        label = data.get("full_name") or data.get("email") or data["id"]
        rprint(f"[green]Updated person:[/green] {label} ({data['id']})")


@people_app.command("delete")
def people_delete(
    person_id: str | None = typer.Argument(None, help="Person ID"),
    person_name: str | None = typer.Option(
        None, "--person-name", help="Person name (auto-resolves to ID)"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete a person."""
    set_json_mode(json_output)
    resolved = _require_id(
        _resolve_contact_id(person_id, person_name, _CRM),
        id_label="person ID",
        name_flag="--person-name",
    )
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete person {resolved}?", abort=True)

    _api_request("delete", f"{_CRM}/people/{resolved}")

    if json_output:
        print_json({"ok": True, "id": resolved, "action": "delete"})
    else:
        rprint(f"[green]Deleted person {resolved}[/green]")


@people_app.command("bulk-upsert")
def people_bulk_upsert(
    ctx: typer.Context,
    file: str = typer.Option(..., "--file", "-f", help="JSON file with people array"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Bulk upsert people from a JSON file."""
    import json as json_mod
    from pathlib import Path

    set_json_mode(json_output)
    path = Path(file)
    if not path.exists():
        rprint(f"[red]File not found:[/red] {file}")
        raise typer.Exit(code=1)

    try:
        items = json_mod.loads(path.read_text())
    except json_mod.JSONDecodeError:
        rprint("[red]Invalid JSON in file[/red]")
        raise typer.Exit(code=1)

    if not isinstance(items, list):
        rprint("[red]File must contain a JSON array of people[/red]")
        raise typer.Exit(code=1)

    resp = _api_request("put", f"{_CRM}/people/bulk", json={"items": items})

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Upserted {data.get('count', 0)} people[/green]")


@people_app.command("bulk-delete")
def people_bulk_delete(
    ids: str = typer.Option(..., "--ids", help="Comma-separated people IDs"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Bulk delete people by ID list."""
    set_json_mode(json_output)
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        rprint("[red]No IDs provided[/red]")
        raise typer.Exit(code=1)

    if not should_skip_confirm(yes):
        typer.confirm(f"Delete {len(id_list)} people?", abort=True)

    _api_request("post", f"{_CRM}/people/bulk-delete", json={"ids": id_list})

    if json_output:
        print_json({"ok": True, "ids": id_list, "count": len(id_list), "action": "bulk-delete"})
    else:
        rprint(f"[green]Deleted {len(id_list)} people[/green]")


def _split_ids(ids: str) -> list[str]:
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        rprint("[red]No IDs provided[/red]")
        raise typer.Exit(code=1)
    return id_list


@people_app.command("approve")
def people_approve(
    ids: str = typer.Option(..., "--ids", help="Comma-separated people IDs"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Mark people as human-approved (ENG-819)."""
    set_json_mode(json_output)
    id_list = _split_ids(ids)
    resp = _api_request("post", f"{_CRM}/people/approve", json={"ids": id_list, "approved": True})
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Approved {data.get('updated_count', 0)} people[/green]")


@people_app.command("mark-actioned")
def people_mark_actioned(
    ids: str = typer.Option(..., "--ids", help="Comma-separated people IDs"),
    note: str | None = typer.Option(
        None,
        "--note",
        help="Optional free-text note. Saved as a CRM activity per person.",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Mark people as actioned (ENG-1127).

    Stamps approved_by / approved_at on each person; with --note, also
    writes a crm_activities row (type=note, source_app=manual) per person.
    Backs the Headhunter Mark done button.
    """
    set_json_mode(json_output)
    id_list = _split_ids(ids)
    resp = _api_request(
        "post",
        f"{_CRM}/people/mark-actioned",
        json={"ids": id_list, "note": note},
    )
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Marked {data.get('updated_count', 0)} people actioned[/green]")


@people_app.command("unapprove")
def people_unapprove(
    ids: str = typer.Option(..., "--ids", help="Comma-separated people IDs"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Clear human approval on people (ENG-819)."""
    set_json_mode(json_output)
    id_list = _split_ids(ids)
    resp = _api_request("post", f"{_CRM}/people/approve", json={"ids": id_list, "approved": False})
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[yellow]Unapproved {data.get('updated_count', 0)} people[/yellow]")
