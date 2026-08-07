# +--------------------------------------------------------------------------+
# | Admin Intelligence — Companies                                       |
# +--------------------------------------------------------------------------+
# | Role                                                                     |
# | CRUD over intel_companies + its intel_sources provenance.  |
# +--------------------------------------------------------------------------+

from __future__ import annotations

import typer

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.admin.intelligence import (
    _INTEL,
    _list_params,
    _write_body,
    companies_app,
)
from ac_cli.formatting import print_detail, print_json, print_table


@companies_app.command("list")
def companies_list(
    ctx: typer.Context,
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
    sort: str | None = typer.Option(None, help="Sort field"),
    order: str | None = typer.Option(None, help="Sort order (asc/desc)"),
    limit: int = typer.Option(50, "--limit", help="Page size"),
    offset: int = typer.Option(0, "--offset", help="Row offset"),
    industry: str | None = typer.Option(None, help="Filter by industry"),
    country: str | None = typer.Option(None, help="Filter by country"),
    business_model: str | None = typer.Option(
        None, "--business-model", help="Filter by business model"
    ),
    revenue_band: str | None = typer.Option(None, "--revenue-band", help="Filter by revenue band"),
    employee_count_band: str | None = typer.Option(
        None, "--employee-band", help="Filter by employee count band"
    ),
    funding_round: str | None = typer.Option(
        None, "--funding-round", help="Filter by funding round"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """List intel companies."""
    set_json_mode(json_output)
    params = _list_params(
        query,
        sort,
        order,
        limit,
        offset,
        industry=industry,
        country=country,
        business_model=business_model,
        revenue_band=revenue_band,
        employee_count_band=employee_count_band,
        funding_round=funding_round,
    )
    resp = _api_request("get", f"{_INTEL}/companies", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data.get("data", []),
        [
            ("name", "Name"),
            ("domain", "Domain"),
            ("industry", "Industry"),
            ("country", "Country"),
            ("id", "ID"),
        ],
        title=f"Intel companies ({data.get('total', '?')} total)",
    )


@companies_app.command("get")
def companies_get(
    ctx: typer.Context,
    company_id: str = typer.Argument(..., help="Intel company ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get an intel company (with provenance sources) by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_INTEL}/companies/{company_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    company = data.get("company", {})
    print_detail(
        company,
        [
            ("id", "ID"),
            ("name", "Name"),
            ("domain", "Domain"),
            ("website", "Website"),
            ("industry", "Industry"),
            ("country", "Country"),
            ("employee_count_band", "Employees"),
            ("revenue_band", "Revenue"),
            ("last_enriched_at", "Last enriched"),
        ],
    )
    print_table(
        data.get("sources", []),
        [
            ("provider", "Provider"),
            ("kind", "Kind"),
            ("cost_usd", "Cost (USD)"),
            ("fetched_at", "Fetched"),
        ],
        title="Sources",
    )


@companies_app.command("create")
def companies_create(
    ctx: typer.Context,
    name: str | None = typer.Option(None, help="Company name"),
    domain: str | None = typer.Option(None, help="Registrable domain (identity key)"),
    website: str | None = typer.Option(None, help="Website URL"),
    linkedin_url: str | None = typer.Option(None, "--linkedin", help="LinkedIn URL"),
    industry: str | None = typer.Option(None, help="Industry"),
    country: str | None = typer.Option(None, help="Country"),
    description: str | None = typer.Option(None, help="Description"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create an intel company (at least one of name/domain/linkedin required)."""
    set_json_mode(json_output)
    body = _write_body(
        name=name,
        domain=domain,
        website=website,
        linkedin_url=linkedin_url,
        industry=industry,
        country=country,
        description=description,
    )
    if not body:
        typer.echo("Provide at least one of --name / --domain / --linkedin")
        raise typer.Exit(1)
    resp = _api_request("post", f"{_INTEL}/companies", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    print_detail(data, [("id", "ID"), ("name", "Name"), ("domain", "Domain")])


@companies_app.command("update")
def companies_update(
    ctx: typer.Context,
    company_id: str = typer.Argument(..., help="Intel company ID"),
    name: str | None = typer.Option(None, help="Company name"),
    domain: str | None = typer.Option(None, help="Registrable domain"),
    website: str | None = typer.Option(None, help="Website URL"),
    linkedin_url: str | None = typer.Option(None, "--linkedin", help="LinkedIn URL"),
    industry: str | None = typer.Option(None, help="Industry"),
    country: str | None = typer.Option(None, help="Country"),
    description: str | None = typer.Option(None, help="Description"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update an intel company (only provided fields change)."""
    set_json_mode(json_output)
    body = _write_body(
        name=name,
        domain=domain,
        website=website,
        linkedin_url=linkedin_url,
        industry=industry,
        country=country,
        description=description,
    )
    if not body:
        typer.echo("No fields to update")
        raise typer.Exit(1)
    resp = _api_request("patch", f"{_INTEL}/companies/{company_id}", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    print_detail(data, [("id", "ID"), ("name", "Name"), ("domain", "Domain")])


@companies_app.command("delete")
def companies_delete(
    ctx: typer.Context,
    company_id: str = typer.Argument(..., help="Intel company ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete an intel company."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete intel company {company_id}?", abort=True)
    resp = _api_request("delete", f"{_INTEL}/companies/{company_id}")
    if json_output:
        print_json(resp.json())
        return
    typer.echo(f"Deleted intel company {company_id}")


@companies_app.command("bulk-delete")
def companies_bulk_delete(
    ctx: typer.Context,
    ids: list[str] = typer.Option(..., "--id", help="Intel company ID (repeatable)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete many intel companies in one request."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete {len(ids)} intel companies?", abort=True)
    resp = _api_request("post", f"{_INTEL}/companies/bulk-delete", json={"ids": ids})
    data = resp.json()
    if json_output:
        print_json(data)
        return
    typer.echo(f"Deleted {data.get('deleted', 0)} of {data.get('requested', len(ids))}")
