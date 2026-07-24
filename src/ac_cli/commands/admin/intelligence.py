# +--------------------------------------------------------------------------+
# | Admin Intelligence — CLI commands (superadmin only)                      |
# +--------------------------------------------------------------------------+
# | Role                                                                     |
# | List / get / create / update / delete over the global intel_companies /  |
# | intel_people tables and their intel_sources provenance. Mirrors the       |
# | /admin/intelligence API one-to-one (API<->CLI parity).                    |
# +--------------------------------------------------------------------------+

from __future__ import annotations

import typer

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_detail, print_json, print_table

intelligence_app = typer.Typer(help="Intelligence data viewer (companies, people)")

companies_app = typer.Typer(help="Intel companies")
people_app = typer.Typer(help="Intel people")
intelligence_app.add_typer(companies_app, name="companies")
intelligence_app.add_typer(people_app, name="people")

_INTEL = f"{_ADMIN}/intelligence"


def _list_params(query, sort, order, limit, offset) -> dict:
    params: dict = {"limit": limit, "offset": offset}
    if query:
        params["q"] = query
    if sort:
        params["sort"] = sort
    if order:
        params["order"] = order
    return params


# +--------------------------------------------------------------------------+
# | Companies                                                                |
# +--------------------------------------------------------------------------+


@companies_app.command("list")
def companies_list(
    ctx: typer.Context,
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
    sort: str | None = typer.Option(None, help="Sort field"),
    order: str | None = typer.Option(None, help="Sort order (asc/desc)"),
    limit: int = typer.Option(50, "--limit", help="Page size"),
    offset: int = typer.Option(0, "--offset", help="Row offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List intel companies."""
    set_json_mode(json_output)
    params = _list_params(query, sort, order, limit, offset)
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
    body = {
        k: v
        for k, v in {
            "name": name,
            "domain": domain,
            "website": website,
            "linkedin_url": linkedin_url,
            "industry": industry,
            "country": country,
            "description": description,
        }.items()
        if v is not None
    }
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
    body = {
        k: v
        for k, v in {
            "name": name,
            "domain": domain,
            "website": website,
            "linkedin_url": linkedin_url,
            "industry": industry,
            "country": country,
            "description": description,
        }.items()
        if v is not None
    }
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


# +--------------------------------------------------------------------------+
# | People                                                                   |
# +--------------------------------------------------------------------------+


@people_app.command("list")
def people_list(
    ctx: typer.Context,
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
    sort: str | None = typer.Option(None, help="Sort field"),
    order: str | None = typer.Option(None, help="Sort order (asc/desc)"),
    limit: int = typer.Option(50, "--limit", help="Page size"),
    offset: int = typer.Option(0, "--offset", help="Row offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List intel people."""
    set_json_mode(json_output)
    params = _list_params(query, sort, order, limit, offset)
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
    body = {
        k: v
        for k, v in {
            "linkedin_url": linkedin_url,
            "full_name": full_name,
            "current_title": current_title,
            "current_company_text": current_company_text,
            "email": email,
            "country": country,
            "location": location,
        }.items()
        if v is not None
    }
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
    body = {
        k: v
        for k, v in {
            "linkedin_url": linkedin_url,
            "full_name": full_name,
            "current_title": current_title,
            "current_company_text": current_company_text,
            "email": email,
            "country": country,
            "location": location,
        }.items()
        if v is not None
    }
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
