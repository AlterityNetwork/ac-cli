# +--------------------------------------------------------------------------+
# | Admin Intelligence — People                                       |
# +--------------------------------------------------------------------------+
# | Role                                                                     |
# | CRUD over intel_people + its intel_sources provenance.           |
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
    people_app,
)
from ac_cli.formatting import print_detail, print_json, print_table


@people_app.command("list")
def people_list(
    ctx: typer.Context,
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
    sort: str | None = typer.Option(None, help="Sort field"),
    order: str | None = typer.Option(None, help="Sort order (asc/desc)"),
    limit: int = typer.Option(50, "--limit", help="Page size"),
    offset: int = typer.Option(0, "--offset", help="Row offset"),
    country: str | None = typer.Option(None, help="Filter by country"),
    industry: str | None = typer.Option(None, help="Filter by industry"),
    title: str | None = typer.Option(None, help="Filter by current title"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List intel people."""
    set_json_mode(json_output)
    params = _list_params(
        query,
        sort,
        order,
        limit,
        offset,
        country=country,
        industry=industry,
        title=title,
    )
    resp = _api_request("get", f"{_INTEL}/people", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data.get("data", []),
        [
            ("full_name", "Name"),
            ("current_title", "Title"),
            ("current_company_text", "Company"),
            ("country", "Country"),
            ("id", "ID"),
        ],
        title=f"Intel people ({data.get('total', '?')} total)",
    )


@people_app.command("get")
def people_get(
    ctx: typer.Context,
    person_id: str = typer.Argument(..., help="Intel person ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get an intel person (with provenance sources) by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_INTEL}/people/{person_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    person = data.get("person", {})
    print_detail(
        person,
        [
            ("id", "ID"),
            ("full_name", "Name"),
            ("linkedin_url", "LinkedIn"),
            ("current_title", "Title"),
            ("current_company_text", "Company"),
            ("location", "Location"),
            ("country", "Country"),
            ("email", "Email"),
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


@people_app.command("create")
def people_create(
    ctx: typer.Context,
    linkedin_url: str = typer.Option(..., "--linkedin", help="LinkedIn URL (identity key)"),
    full_name: str | None = typer.Option(None, "--name", help="Full name"),
    current_title: str | None = typer.Option(None, "--title", help="Current title"),
    current_company_text: str | None = typer.Option(None, "--company", help="Current company"),
    email: str | None = typer.Option(None, help="Email"),
    country: str | None = typer.Option(None, help="Country"),
    location: str | None = typer.Option(None, help="Location"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create an intel person (linkedin_url required)."""
    set_json_mode(json_output)
    body = _write_body(
        linkedin_url=linkedin_url,
        full_name=full_name,
        current_title=current_title,
        current_company_text=current_company_text,
        email=email,
        country=country,
        location=location,
    )
    resp = _api_request("post", f"{_INTEL}/people", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    print_detail(data, [("id", "ID"), ("full_name", "Name"), ("linkedin_url", "LinkedIn")])


@people_app.command("update")
def people_update(
    ctx: typer.Context,
    person_id: str = typer.Argument(..., help="Intel person ID"),
    linkedin_url: str | None = typer.Option(None, "--linkedin", help="LinkedIn URL"),
    full_name: str | None = typer.Option(None, "--name", help="Full name"),
    current_title: str | None = typer.Option(None, "--title", help="Current title"),
    current_company_text: str | None = typer.Option(None, "--company", help="Current company"),
    email: str | None = typer.Option(None, help="Email"),
    country: str | None = typer.Option(None, help="Country"),
    location: str | None = typer.Option(None, help="Location"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update an intel person (only provided fields change)."""
    set_json_mode(json_output)
    body = _write_body(
        linkedin_url=linkedin_url,
        full_name=full_name,
        current_title=current_title,
        current_company_text=current_company_text,
        email=email,
        country=country,
        location=location,
    )
    if not body:
        typer.echo("No fields to update")
        raise typer.Exit(1)
    resp = _api_request("patch", f"{_INTEL}/people/{person_id}", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    print_detail(data, [("id", "ID"), ("full_name", "Name"), ("linkedin_url", "LinkedIn")])


@people_app.command("delete")
def people_delete(
    ctx: typer.Context,
    person_id: str = typer.Argument(..., help="Intel person ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete an intel person."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete intel person {person_id}?", abort=True)
    resp = _api_request("delete", f"{_INTEL}/people/{person_id}")
    if json_output:
        print_json(resp.json())
        return
    typer.echo(f"Deleted intel person {person_id}")


@people_app.command("bulk-delete")
def people_bulk_delete(
    ctx: typer.Context,
    ids: list[str] = typer.Option(..., "--id", help="Intel person ID (repeatable)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete many intel people in one request."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete {len(ids)} intel people?", abort=True)
    resp = _api_request("post", f"{_INTEL}/people/bulk-delete", json={"ids": ids})
    data = resp.json()
    if json_output:
        print_json(data)
        return
    typer.echo(f"Deleted {data.get('deleted', 0)} of {data.get('requested', len(ids))}")
