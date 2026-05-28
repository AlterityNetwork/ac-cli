"""CRM companies commands."""

from __future__ import annotations

from enum import Enum

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


class CompaniesListView(str, Enum):
    """Projection mode for ``ac crm companies list`` (ENG-933).

    ``full`` (default) returns the wide list payload used by the CRM table.
    ``options`` switches to the slim selector / picker / hover-card shape.
    """

    full = "full"
    options = "options"


companies_app = typer.Typer(help="Company operations")


@companies_app.command("list")
def companies_list(
    ctx: typer.Context,
    limit: int = typer.Option(100, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    query: str | None = typer.Option(
        None,
        "--query",
        "--search",
        help="Search company names. Sends the API's canonical `q` query parameter.",
    ),
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
    view: CompaniesListView = typer.Option(
        CompaniesListView.full,
        "--view",
        case_sensitive=False,
        help="Projection mode: 'full' (default, wide CRM table shape) or "
        "'options' (slim selector / picker / hover-card payload — ENG-933).",
    ),
    lean: bool = typer.Option(
        False,
        "--lean",
        help="Shortcut for --view options (ENG-933).",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """List companies."""
    set_json_mode(json_output)
    effective_view = CompaniesListView.options if lean else view
    params: dict[str, object] = {
        "limit": limit,
        "offset": offset,
        "view": effective_view.value,
    }
    if approved is not None:
        params["approved"] = approved
    if query:
        params["q"] = query
    if added_by_type:
        params["added_by_type"] = added_by_type
    if added_by_user:
        params["added_by_user_id"] = added_by_user
    resp = _api_request("get", f"{_CRM}/companies", params=params)

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
    company_name: str | None = typer.Option(
        None, "--company-name", help="Company name (auto-resolves to ID)"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a company by ID or name."""
    set_json_mode(json_output)
    resolved = _require_id(
        _resolve_company_id(company_id, company_name, _CRM),
        id_label="company ID",
        name_flag="--company-name",
    )
    resp = _api_request("get", f"{_CRM}/companies/{resolved}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
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
            ("created_by_user_id", "Added By (user)"),
            ("approved_by", "Approved By"),
            ("approved_at", "Approved At"),
        ],
    )


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
        name=name,
        website=website,
        industry=industry,
        lifecycle_stage=lifecycle_stage,
        tags=tags,
        location=location,
        country=country,
        description=description,
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
    company_name: str | None = typer.Option(
        None, "--company-name", help="Company name (auto-resolves to ID)"
    ),
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
        id_label="company ID",
        name_flag="--company-name",
    )
    body = _build_body(
        name=name,
        website=website,
        industry=industry,
        lifecycle_stage=lifecycle_stage,
        tags=tags,
        location=location,
        country=country,
        description=description,
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
    company_name: str | None = typer.Option(
        None, "--company-name", help="Company name (auto-resolves to ID)"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete a company."""
    set_json_mode(json_output)
    resolved = _require_id(
        _resolve_company_id(company_id, company_name, _CRM),
        id_label="company ID",
        name_flag="--company-name",
    )
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete company {resolved}?", abort=True)

    _api_request("delete", f"{_CRM}/companies/{resolved}")

    if json_output:
        print_json({"ok": True, "id": resolved, "action": "delete"})
    else:
        rprint(f"[green]Deleted company {resolved}[/green]")


@companies_app.command("bulk-delete")
def companies_bulk_delete(
    ids: str = typer.Option(..., "--ids", help="Comma-separated company IDs"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Bulk delete companies by ID list."""
    set_json_mode(json_output)
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        rprint("[red]No IDs provided[/red]")
        raise typer.Exit(code=1)

    if not should_skip_confirm(yes):
        typer.confirm(f"Delete {len(id_list)} companies?", abort=True)

    _api_request("post", f"{_CRM}/companies/bulk-delete", json={"ids": id_list})

    if json_output:
        print_json({"ok": True, "ids": id_list, "count": len(id_list), "action": "bulk-delete"})
    else:
        rprint(f"[green]Deleted {len(id_list)} companies[/green]")


@companies_app.command("by-ids")
def companies_by_ids(
    ids: str = typer.Option(..., "--ids", help="Comma-separated company IDs (max 200)"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Batch-fetch companies by ID list in a single request (ENG-924).

    Replaces N parallel ``GET /crm/companies/{id}`` calls when hydrating linked
    companies for multiple rows. Returns the same paginated shape as ``list``;
    unknown / soft-deleted / cross-org ids are silently dropped.
    """
    set_json_mode(json_output)
    id_list = _split_ids(ids)

    resp = _api_request("post", f"{_CRM}/companies/by-ids", json={"ids": id_list})
    data = resp.json()

    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Fetched {data.get('total', 0)} companies[/green]")


def _split_ids(ids: str) -> list[str]:
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        rprint("[red]No IDs provided[/red]")
        raise typer.Exit(code=1)
    return id_list


@companies_app.command("approve")
def companies_approve(
    ids: str = typer.Option(..., "--ids", help="Comma-separated company IDs"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Mark companies as human-approved (ENG-819)."""
    set_json_mode(json_output)
    id_list = _split_ids(ids)
    resp = _api_request(
        "post", f"{_CRM}/companies/approve", json={"ids": id_list, "approved": True}
    )
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Approved {data.get('updated_count', 0)} companies[/green]")


@companies_app.command("unapprove")
def companies_unapprove(
    ids: str = typer.Option(..., "--ids", help="Comma-separated company IDs"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Clear human approval on companies (ENG-819)."""
    set_json_mode(json_output)
    id_list = _split_ids(ids)
    resp = _api_request(
        "post", f"{_CRM}/companies/approve", json={"ids": id_list, "approved": False}
    )
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[yellow]Unapproved {data.get('updated_count', 0)} companies[/yellow]")
