"""CRM companies commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _get_org_id,
    _require_id,
    _resolve_company_id,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.crm import _CRM, _api_request, _build_body
from ac_cli.formatting import print_detail, print_json, print_table

companies_app = typer.Typer(help="Company operations")


@companies_app.command("list")
def companies_list(
    ctx: typer.Context,
    limit: int = typer.Option(100, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List companies."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/companies", params={"limit": limit, "offset": offset})

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data.get("data", []),
        [
            ("name", "Name"),
            ("industry", "Industry"),
            ("lifecycle_stage", "Stage"),
            ("location", "Location"),
            ("id", "ID"),
        ],
        title=f"Companies ({data.get('total', '?')} total)",
    )


@companies_app.command("get")
def companies_get(
    ctx: typer.Context,
    company_id: str | None = typer.Argument(None, help="Company ID"),
    company_name: str | None = typer.Option(None, "--company-name", help="Company name (auto-resolves to ID)"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a company by ID or name."""
    set_json_mode(json_output)
    resolved = _require_id(
        _resolve_company_id(company_id, company_name, _CRM),
        id_label="company ID", name_flag="--company-name",
    )
    resp = _api_request("get", f"{_CRM}/companies/{resolved}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, [
        ("id", "ID"),
        ("name", "Name"),
        ("website", "Website"),
        ("industry", "Industry"),
        ("lifecycle_stage", "Stage"),
        ("location", "Location"),
        ("country", "Country"),
        ("employee_count_band", "Size"),
        ("tags", "Tags"),
        ("description", "Description"),
        ("created_at", "Created"),
        ("updated_at", "Updated"),
    ])


@companies_app.command("create")
def companies_create(
    ctx: typer.Context,
    name: str = typer.Option(..., help="Company name"),
    website: str | None = typer.Option(None, help="Website URL"),
    industry: str | None = typer.Option(None, help="Industry"),
    lifecycle_stage: str | None = typer.Option(None, "--lifecycle-stage", help="Lifecycle stage"),
    tags: str | None = typer.Option(None, help="Comma-separated tags"),
    location: str | None = typer.Option(None, help="Location"),
    country: str | None = typer.Option(None, help="Country"),
    description: str | None = typer.Option(None, help="Description"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new company."""
    set_json_mode(json_output)
    body = _build_body(
        name=name, website=website, industry=industry,
        lifecycle_stage=lifecycle_stage, tags=tags,
        location=location, country=country, description=description,
    )

    body["organization_id"] = _get_org_id()

    resp = _api_request("post", f"{_CRM}/companies", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Created company:[/green] {data['name']} ({data['id']})")


@companies_app.command("update")
def companies_update(
    ctx: typer.Context,
    company_id: str | None = typer.Argument(None, help="Company ID"),
    company_name: str | None = typer.Option(None, "--company-name", help="Company name (auto-resolves to ID)"),
    name: str | None = typer.Option(None, help="New company name"),
    website: str | None = typer.Option(None, help="Website URL"),
    industry: str | None = typer.Option(None, help="Industry"),
    lifecycle_stage: str | None = typer.Option(None, "--lifecycle-stage", help="Lifecycle stage"),
    tags: str | None = typer.Option(None, help="Comma-separated tags"),
    location: str | None = typer.Option(None, help="Location"),
    country: str | None = typer.Option(None, help="Country"),
    description: str | None = typer.Option(None, help="Description"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update an existing company."""
    set_json_mode(json_output)
    resolved = _require_id(
        _resolve_company_id(company_id, company_name, _CRM),
        id_label="company ID", name_flag="--company-name",
    )
    body = _build_body(
        name=name, website=website, industry=industry,
        lifecycle_stage=lifecycle_stage, tags=tags,
        location=location, country=country, description=description,
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_CRM}/companies/{resolved}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated company:[/green] {data['name']} ({data['id']})")


@companies_app.command("delete")
def companies_delete(
    company_id: str | None = typer.Argument(None, help="Company ID"),
    company_name: str | None = typer.Option(None, "--company-name", help="Company name (auto-resolves to ID)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete a company."""
    set_json_mode(json_output)
    resolved = _require_id(
        _resolve_company_id(company_id, company_name, _CRM),
        id_label="company ID", name_flag="--company-name",
    )
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete company {resolved}?", abort=True)

    _api_request("delete", f"{_CRM}/companies/{resolved}")

    rprint(f"[green]Deleted company {resolved}[/green]")
