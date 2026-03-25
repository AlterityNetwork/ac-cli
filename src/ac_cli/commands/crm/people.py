"""CRM people commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, set_json_mode, should_skip_confirm
from ac_cli.commands.crm import _CRM, _api_request, _build_body
from ac_cli.formatting import print_detail, print_json, print_table

people_app = typer.Typer(help="People/contact operations")


@people_app.command("list")
def people_list(
    ctx: typer.Context,
    company_id: str | None = typer.Option(None, "--company-id", help="Filter by company"),
    limit: int = typer.Option(100, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List people."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset}
    if company_id:
        params["company_id"] = company_id

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
    person_id: str = typer.Argument(..., help="Person ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a person by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/people/{person_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, [
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
    ])


@people_app.command("create")
def people_create(
    ctx: typer.Context,
    email: str | None = typer.Option(None, help="Email address"),
    full_name: str | None = typer.Option(None, "--full-name", help="Full name"),
    current_title: str | None = typer.Option(None, "--current-title", help="Job title"),
    company_id: str | None = typer.Option(None, "--company-id", help="Company ID"),
    lifecycle_stage: str | None = typer.Option(None, "--lifecycle-stage", help="Lifecycle stage"),
    tags: str | None = typer.Option(None, help="Comma-separated tags"),
    linkedin_url: str | None = typer.Option(None, "--linkedin-url", help="LinkedIn URL"),
    location: str | None = typer.Option(None, help="Location"),
    country: str | None = typer.Option(None, help="Country"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new person."""
    set_json_mode(json_output)
    body = _build_body(
        email=email, full_name=full_name, current_title=current_title,
        company_id=company_id, lifecycle_stage=lifecycle_stage, tags=tags,
        linkedin_url=linkedin_url, location=location, country=country,
    )

    me = _api_request("get", "/whoami")
    body["organization_id"] = me.json()["organization_id"]

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
    person_id: str = typer.Argument(..., help="Person ID"),
    email: str | None = typer.Option(None, help="Email address"),
    full_name: str | None = typer.Option(None, "--full-name", help="Full name"),
    current_title: str | None = typer.Option(None, "--current-title", help="Job title"),
    company_id: str | None = typer.Option(None, "--company-id", help="Company ID"),
    lifecycle_stage: str | None = typer.Option(None, "--lifecycle-stage", help="Lifecycle stage"),
    tags: str | None = typer.Option(None, help="Comma-separated tags"),
    linkedin_url: str | None = typer.Option(None, "--linkedin-url", help="LinkedIn URL"),
    location: str | None = typer.Option(None, help="Location"),
    country: str | None = typer.Option(None, help="Country"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update an existing person."""
    set_json_mode(json_output)
    body = _build_body(
        email=email, full_name=full_name, current_title=current_title,
        company_id=company_id, lifecycle_stage=lifecycle_stage, tags=tags,
        linkedin_url=linkedin_url, location=location, country=country,
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_CRM}/people/{person_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        label = data.get("full_name") or data.get("email") or data["id"]
        rprint(f"[green]Updated person:[/green] {label} ({data['id']})")


@people_app.command("delete")
def people_delete(
    person_id: str = typer.Argument(..., help="Person ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a person."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete person {person_id}?", abort=True)

    _api_request("delete", f"{_CRM}/people/{person_id}")

    rprint(f"[green]Deleted person {person_id}[/green]")
