"""CRM commands: search, companies, people, deals, activities, dashboard, lists."""

from datetime import datetime, timezone
from typing import Optional

import httpx
import typer
from rich import print as rprint

from ac_cli.client import get_api_client
from ac_cli.formatting import print_detail, print_json, print_table

app = typer.Typer(help="CRM commands")

# -- Shared helpers -----------------------------------------------------------

_json_flag = False


@app.callback()
def crm_callback(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    global _json_flag
    _json_flag = json_output


def _handle_error(exc: httpx.HTTPStatusError) -> None:
    """Print API error detail and exit."""
    try:
        detail = exc.response.json().get("detail", exc.response.text)
    except Exception:
        detail = exc.response.text
    rprint(f"[red]Error {exc.response.status_code}:[/red] {detail}")
    raise typer.Exit(code=1)


# =============================================================================
# SEARCH
# =============================================================================


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
) -> None:
    """Search across companies, contacts, and deals."""
    with get_api_client() as client:
        try:
            resp = client.get("/crm/search", params={"q": query})
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
        return

    companies = data.get("companies", [])
    contacts = data.get("contacts", [])
    deals = data.get("deals", [])

    if companies:
        print_table(
            companies,
            [("name", "Name"), ("industry", "Industry"), ("id", "ID")],
            title="Companies",
        )
    if contacts:
        print_table(
            contacts,
            [("full_name", "Name"), ("email", "Email"), ("id", "ID")],
            title="Contacts",
        )
    if deals:
        print_table(
            deals,
            [("name", "Name"), ("stage", "Stage"), ("id", "ID")],
            title="Deals",
        )

    if not companies and not contacts and not deals:
        rprint("[dim]No results found.[/dim]")


# =============================================================================
# COMPANIES
# =============================================================================

companies_app = typer.Typer(help="Company operations")
app.add_typer(companies_app, name="companies")


@companies_app.callback()
def companies_callback() -> None:
    pass


@companies_app.command("list")
def companies_list(
    limit: int = typer.Option(100, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
) -> None:
    """List companies."""
    with get_api_client() as client:
        try:
            resp = client.get("/crm/companies", params={"limit": limit, "offset": offset})
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
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
    company_id: str = typer.Argument(..., help="Company ID"),
) -> None:
    """Get a company by ID."""
    with get_api_client() as client:
        try:
            resp = client.get(f"/crm/companies/{company_id}")
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
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
    name: str = typer.Option(..., help="Company name"),
    website: Optional[str] = typer.Option(None, help="Website URL"),
    industry: Optional[str] = typer.Option(None, help="Industry"),
    lifecycle_stage: Optional[str] = typer.Option(None, "--lifecycle-stage", help="Lifecycle stage"),
    tags: Optional[str] = typer.Option(None, help="Comma-separated tags"),
    location: Optional[str] = typer.Option(None, help="Location"),
    country: Optional[str] = typer.Option(None, help="Country"),
    description: Optional[str] = typer.Option(None, help="Description"),
) -> None:
    """Create a new company."""
    body: dict = {"name": name}
    if website:
        body["website"] = website
    if industry:
        body["industry"] = industry
    if lifecycle_stage:
        body["lifecycle_stage"] = lifecycle_stage
    if tags:
        body["tags"] = [t.strip() for t in tags.split(",")]
    if location:
        body["location"] = location
    if country:
        body["country"] = country
    if description:
        body["description"] = description

    with get_api_client() as client:
        try:
            # Fetch org ID from whoami
            me = client.get("/whoami")
            me.raise_for_status()
            body["organization_id"] = me.json()["organization_id"]

            resp = client.post("/crm/companies", json=body)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
    else:
        rprint(f"[green]Created company:[/green] {data['name']} ({data['id']})")


@companies_app.command("update")
def companies_update(
    company_id: str = typer.Argument(..., help="Company ID"),
    name: Optional[str] = typer.Option(None, help="Company name"),
    website: Optional[str] = typer.Option(None, help="Website URL"),
    industry: Optional[str] = typer.Option(None, help="Industry"),
    lifecycle_stage: Optional[str] = typer.Option(None, "--lifecycle-stage", help="Lifecycle stage"),
    tags: Optional[str] = typer.Option(None, help="Comma-separated tags"),
    location: Optional[str] = typer.Option(None, help="Location"),
    country: Optional[str] = typer.Option(None, help="Country"),
    description: Optional[str] = typer.Option(None, help="Description"),
) -> None:
    """Update an existing company."""
    body: dict = {}
    if name is not None:
        body["name"] = name
    if website is not None:
        body["website"] = website
    if industry is not None:
        body["industry"] = industry
    if lifecycle_stage is not None:
        body["lifecycle_stage"] = lifecycle_stage
    if tags is not None:
        body["tags"] = [t.strip() for t in tags.split(",")]
    if location is not None:
        body["location"] = location
    if country is not None:
        body["country"] = country
    if description is not None:
        body["description"] = description

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    with get_api_client() as client:
        try:
            resp = client.patch(f"/crm/companies/{company_id}", json=body)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
    else:
        rprint(f"[green]Updated company:[/green] {data['name']} ({data['id']})")


@companies_app.command("delete")
def companies_delete(
    company_id: str = typer.Argument(..., help="Company ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a company."""
    if not yes:
        typer.confirm(f"Delete company {company_id}?", abort=True)

    with get_api_client() as client:
        try:
            resp = client.delete(f"/crm/companies/{company_id}")
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    rprint(f"[green]Deleted company {company_id}[/green]")


# =============================================================================
# PEOPLE
# =============================================================================

people_app = typer.Typer(help="People/contact operations")
app.add_typer(people_app, name="people")


@people_app.callback()
def people_callback() -> None:
    pass


@people_app.command("list")
def people_list(
    company_id: Optional[str] = typer.Option(None, "--company-id", help="Filter by company"),
    limit: int = typer.Option(100, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
) -> None:
    """List people."""
    params: dict = {"limit": limit, "offset": offset}
    if company_id:
        params["company_id"] = company_id

    with get_api_client() as client:
        try:
            resp = client.get("/crm/people", params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
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
    person_id: str = typer.Argument(..., help="Person ID"),
) -> None:
    """Get a person by ID."""
    with get_api_client() as client:
        try:
            resp = client.get(f"/crm/people/{person_id}")
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
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
    email: Optional[str] = typer.Option(None, help="Email address"),
    full_name: Optional[str] = typer.Option(None, "--full-name", help="Full name"),
    current_title: Optional[str] = typer.Option(None, "--current-title", help="Job title"),
    company_id: Optional[str] = typer.Option(None, "--company-id", help="Company ID"),
    lifecycle_stage: Optional[str] = typer.Option(None, "--lifecycle-stage", help="Lifecycle stage"),
    tags: Optional[str] = typer.Option(None, help="Comma-separated tags"),
    linkedin_url: Optional[str] = typer.Option(None, "--linkedin-url", help="LinkedIn URL"),
    location: Optional[str] = typer.Option(None, help="Location"),
    country: Optional[str] = typer.Option(None, help="Country"),
) -> None:
    """Create a new person."""
    body: dict = {}
    if email:
        body["email"] = email
    if full_name:
        body["full_name"] = full_name
    if current_title:
        body["current_title"] = current_title
    if company_id:
        body["company_id"] = company_id
    if lifecycle_stage:
        body["lifecycle_stage"] = lifecycle_stage
    if tags:
        body["tags"] = [t.strip() for t in tags.split(",")]
    if linkedin_url:
        body["linkedin_url"] = linkedin_url
    if location:
        body["location"] = location
    if country:
        body["country"] = country

    with get_api_client() as client:
        try:
            me = client.get("/whoami")
            me.raise_for_status()
            body["organization_id"] = me.json()["organization_id"]

            resp = client.post("/crm/people", json=body)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
    else:
        label = data.get("full_name") or data.get("email") or data["id"]
        rprint(f"[green]Created person:[/green] {label} ({data['id']})")


@people_app.command("update")
def people_update(
    person_id: str = typer.Argument(..., help="Person ID"),
    email: Optional[str] = typer.Option(None, help="Email address"),
    full_name: Optional[str] = typer.Option(None, "--full-name", help="Full name"),
    current_title: Optional[str] = typer.Option(None, "--current-title", help="Job title"),
    company_id: Optional[str] = typer.Option(None, "--company-id", help="Company ID"),
    lifecycle_stage: Optional[str] = typer.Option(None, "--lifecycle-stage", help="Lifecycle stage"),
    tags: Optional[str] = typer.Option(None, help="Comma-separated tags"),
    linkedin_url: Optional[str] = typer.Option(None, "--linkedin-url", help="LinkedIn URL"),
    location: Optional[str] = typer.Option(None, help="Location"),
    country: Optional[str] = typer.Option(None, help="Country"),
) -> None:
    """Update an existing person."""
    body: dict = {}
    if email is not None:
        body["email"] = email
    if full_name is not None:
        body["full_name"] = full_name
    if current_title is not None:
        body["current_title"] = current_title
    if company_id is not None:
        body["company_id"] = company_id
    if lifecycle_stage is not None:
        body["lifecycle_stage"] = lifecycle_stage
    if tags is not None:
        body["tags"] = [t.strip() for t in tags.split(",")]
    if linkedin_url is not None:
        body["linkedin_url"] = linkedin_url
    if location is not None:
        body["location"] = location
    if country is not None:
        body["country"] = country

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    with get_api_client() as client:
        try:
            resp = client.patch(f"/crm/people/{person_id}", json=body)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
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
    if not yes:
        typer.confirm(f"Delete person {person_id}?", abort=True)

    with get_api_client() as client:
        try:
            resp = client.delete(f"/crm/people/{person_id}")
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    rprint(f"[green]Deleted person {person_id}[/green]")


# =============================================================================
# DEALS
# =============================================================================

deals_app = typer.Typer(help="Deal operations")
app.add_typer(deals_app, name="deals")


@deals_app.callback()
def deals_callback() -> None:
    pass


@deals_app.command("list")
def deals_list(
    stage: Optional[str] = typer.Option(None, help="Filter by stage"),
    company_id: Optional[str] = typer.Option(None, "--company-id", help="Filter by company"),
    owner_id: Optional[str] = typer.Option(None, "--owner-id", help="Filter by owner"),
    limit: int = typer.Option(100, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
) -> None:
    """List deals."""
    params: dict = {"limit": limit, "offset": offset}
    if stage:
        params["stage"] = stage
    if company_id:
        params["company_id"] = company_id
    if owner_id:
        params["owner_user_id"] = owner_id

    with get_api_client() as client:
        try:
            resp = client.get("/crm/deals", params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
        return

    # API returns a flat list
    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("name", "Name"),
            ("stage", "Stage"),
            ("amount", "Amount"),
            ("expected_close_date", "Close Date"),
            ("id", "ID"),
        ],
        title=f"Deals ({len(items)})",
    )


@deals_app.command("get")
def deals_get(
    deal_id: str = typer.Argument(..., help="Deal ID"),
) -> None:
    """Get a deal by ID."""
    with get_api_client() as client:
        try:
            resp = client.get(f"/crm/deals/{deal_id}")
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
        return

    print_detail(data, [
        ("id", "ID"),
        ("name", "Name"),
        ("stage", "Stage"),
        ("amount", "Amount"),
        ("currency", "Currency"),
        ("probability", "Probability"),
        ("expected_close_date", "Expected Close"),
        ("actual_close_date", "Actual Close"),
        ("company_id", "Company ID"),
        ("primary_contact_id", "Contact ID"),
        ("owner_user_id", "Owner ID"),
        ("tags", "Tags"),
        ("next_steps", "Next Steps"),
        ("lost_reason", "Lost Reason"),
        ("created_at", "Created"),
        ("updated_at", "Updated"),
    ])


@deals_app.command("create")
def deals_create(
    name: str = typer.Option(..., help="Deal name"),
    stage: Optional[str] = typer.Option(None, help="Deal stage"),
    amount: Optional[float] = typer.Option(None, help="Deal amount"),
    currency: Optional[str] = typer.Option(None, help="Currency code"),
    company_id: Optional[str] = typer.Option(None, "--company-id", help="Company ID"),
    contact_id: Optional[str] = typer.Option(None, "--contact-id", help="Primary contact ID"),
    expected_close_date: Optional[str] = typer.Option(None, "--expected-close-date", help="ISO date"),
    tags: Optional[str] = typer.Option(None, help="Comma-separated tags"),
    next_steps: Optional[str] = typer.Option(None, "--next-steps", help="Next steps"),
) -> None:
    """Create a new deal."""
    body: dict = {"name": name}
    if stage:
        body["stage"] = stage
    if amount is not None:
        body["amount"] = amount
    if currency:
        body["currency"] = currency
    if company_id:
        body["company_id"] = company_id
    if contact_id:
        body["primary_contact_id"] = contact_id
    if expected_close_date:
        body["expected_close_date"] = expected_close_date
    if tags:
        body["tags"] = [t.strip() for t in tags.split(",")]
    if next_steps:
        body["next_steps"] = next_steps

    with get_api_client() as client:
        try:
            me = client.get("/whoami")
            me.raise_for_status()
            body["organization_id"] = me.json()["organization_id"]

            resp = client.post("/crm/deals", json=body)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
    else:
        rprint(f"[green]Created deal:[/green] {data['name']} ({data['id']})")


@deals_app.command("update")
def deals_update(
    deal_id: str = typer.Argument(..., help="Deal ID"),
    name: Optional[str] = typer.Option(None, help="Deal name"),
    stage: Optional[str] = typer.Option(None, help="Deal stage"),
    amount: Optional[float] = typer.Option(None, help="Deal amount"),
    currency: Optional[str] = typer.Option(None, help="Currency code"),
    company_id: Optional[str] = typer.Option(None, "--company-id", help="Company ID"),
    contact_id: Optional[str] = typer.Option(None, "--contact-id", help="Primary contact ID"),
    expected_close_date: Optional[str] = typer.Option(None, "--expected-close-date", help="ISO date"),
    tags: Optional[str] = typer.Option(None, help="Comma-separated tags"),
    next_steps: Optional[str] = typer.Option(None, "--next-steps", help="Next steps"),
) -> None:
    """Update an existing deal."""
    body: dict = {}
    if name is not None:
        body["name"] = name
    if stage is not None:
        body["stage"] = stage
    if amount is not None:
        body["amount"] = amount
    if currency is not None:
        body["currency"] = currency
    if company_id is not None:
        body["company_id"] = company_id
    if contact_id is not None:
        body["primary_contact_id"] = contact_id
    if expected_close_date is not None:
        body["expected_close_date"] = expected_close_date
    if tags is not None:
        body["tags"] = [t.strip() for t in tags.split(",")]
    if next_steps is not None:
        body["next_steps"] = next_steps

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    with get_api_client() as client:
        try:
            resp = client.patch(f"/crm/deals/{deal_id}", json=body)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
    else:
        rprint(f"[green]Updated deal:[/green] {data['name']} ({data['id']})")


@deals_app.command("move")
def deals_move(
    deal_id: str = typer.Argument(..., help="Deal ID"),
    stage: str = typer.Option(..., help="New stage"),
) -> None:
    """Move a deal to a new stage."""
    with get_api_client() as client:
        try:
            resp = client.patch(f"/crm/deals/{deal_id}/stage", json={"stage": stage})
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
    else:
        rprint(f"[green]Moved deal to {data['stage']}:[/green] {data['name']} ({data['id']})")


@deals_app.command("delete")
def deals_delete(
    deal_id: str = typer.Argument(..., help="Deal ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a deal."""
    if not yes:
        typer.confirm(f"Delete deal {deal_id}?", abort=True)

    with get_api_client() as client:
        try:
            resp = client.delete(f"/crm/deals/{deal_id}")
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    rprint(f"[green]Deleted deal {deal_id}[/green]")


# =============================================================================
# ACTIVITIES
# =============================================================================

activities_app = typer.Typer(help="Activity operations")
app.add_typer(activities_app, name="activities")


@activities_app.callback()
def activities_callback() -> None:
    pass


@activities_app.command("list")
def activities_list(
    deal_id: Optional[str] = typer.Option(None, "--deal-id", help="Filter by deal"),
    company_id: Optional[str] = typer.Option(None, "--company-id", help="Filter by company"),
    contact_id: Optional[str] = typer.Option(None, "--contact-id", help="Filter by contact"),
    activity_type: Optional[str] = typer.Option(None, "--type", help="Filter by type"),
    status: Optional[str] = typer.Option(None, help="Filter by status"),
    sort_by: Optional[str] = typer.Option(None, "--sort-by", help="Sort field: due_date or created_at"),
    limit: int = typer.Option(100, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
) -> None:
    """List activities."""
    params: dict = {"limit": limit, "offset": offset}
    if deal_id:
        params["deal_id"] = deal_id
    if company_id:
        params["company_id"] = company_id
    if contact_id:
        params["contact_id"] = contact_id
    if activity_type:
        params["type"] = activity_type
    if status:
        params["status"] = status
    if sort_by:
        params["sort_by"] = sort_by

    with get_api_client() as client:
        try:
            resp = client.get("/crm/activities", params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
        return

    # API returns a flat list
    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("title", "Title"),
            ("type", "Type"),
            ("status", "Status"),
            ("priority", "Priority"),
            ("due_date", "Due Date"),
            ("id", "ID"),
        ],
        title=f"Activities ({len(items)})",
    )


@activities_app.command("get")
def activities_get(
    activity_id: str = typer.Argument(..., help="Activity ID"),
) -> None:
    """Get an activity by ID."""
    with get_api_client() as client:
        try:
            resp = client.get(f"/crm/activities/{activity_id}")
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
        return

    print_detail(data, [
        ("id", "ID"),
        ("title", "Title"),
        ("type", "Type"),
        ("status", "Status"),
        ("priority", "Priority"),
        ("due_date", "Due Date"),
        ("completed_at", "Completed At"),
        ("description", "Description"),
        ("company_id", "Company ID"),
        ("contact_id", "Contact ID"),
        ("deal_id", "Deal ID"),
        ("assigned_to", "Assigned To"),
        ("created_at", "Created"),
        ("updated_at", "Updated"),
    ])


@activities_app.command("create")
def activities_create(
    activity_type: str = typer.Option(..., "--type", help="Activity type (call, meeting, email, task, note)"),
    title: str = typer.Option(..., help="Activity title"),
    due_date: Optional[str] = typer.Option(None, "--due-date", help="Due date (ISO format)"),
    priority: Optional[str] = typer.Option(None, help="Priority (low, medium, high, urgent)"),
    deal_id: Optional[str] = typer.Option(None, "--deal-id", help="Deal ID"),
    company_id: Optional[str] = typer.Option(None, "--company-id", help="Company ID"),
    contact_id: Optional[str] = typer.Option(None, "--contact-id", help="Contact ID"),
    description: Optional[str] = typer.Option(None, help="Description"),
) -> None:
    """Create a new activity."""
    body: dict = {"type": activity_type, "title": title}
    if due_date:
        body["due_date"] = due_date
    if priority:
        body["priority"] = priority
    if deal_id:
        body["deal_id"] = deal_id
    if company_id:
        body["company_id"] = company_id
    if contact_id:
        body["contact_id"] = contact_id
    if description:
        body["description"] = description

    with get_api_client() as client:
        try:
            me = client.get("/whoami")
            me.raise_for_status()
            body["organization_id"] = me.json()["organization_id"]

            resp = client.post("/crm/activities", json=body)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
    else:
        rprint(f"[green]Created activity:[/green] {data['title']} ({data['id']})")


@activities_app.command("complete")
def activities_complete(
    activity_id: str = typer.Argument(..., help="Activity ID"),
) -> None:
    """Mark an activity as completed."""
    now = datetime.now(timezone.utc).isoformat()
    with get_api_client() as client:
        try:
            resp = client.patch(
                f"/crm/activities/{activity_id}",
                json={"status": "completed", "completed_at": now},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
    else:
        rprint(f"[green]Completed activity:[/green] {data['title']} ({data['id']})")


@activities_app.command("delete")
def activities_delete(
    activity_id: str = typer.Argument(..., help="Activity ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete an activity."""
    if not yes:
        typer.confirm(f"Delete activity {activity_id}?", abort=True)

    with get_api_client() as client:
        try:
            resp = client.delete(f"/crm/activities/{activity_id}")
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    rprint(f"[green]Deleted activity {activity_id}[/green]")


# =============================================================================
# DASHBOARD
# =============================================================================


@app.command("dashboard")
def dashboard(
    period: int = typer.Option(30, "--period", help="Period in days"),
) -> None:
    """Show CRM dashboard summary."""
    with get_api_client() as client:
        try:
            resp = client.get("/crm/dashboard", params={"period_days": period})
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
        return

    pipeline = data.get("pipeline", {})
    active = data.get("active_pipeline", {})
    leads = data.get("leads", {})
    messages = data.get("messages_sent", {})

    rprint(f"\n[bold]CRM Dashboard[/bold] (last {data.get('period_days', period)} days)\n")

    rprint("[bold]Pipeline[/bold]")
    rprint(f"  Total deals: {pipeline.get('total_deals', 0)}")
    rprint(f"  Total value: ${pipeline.get('total_value', 0):,.2f}")
    stages = pipeline.get("deals_by_stage", {})
    for stage_name, stats in stages.items():
        rprint(f"    {stage_name}: {stats.get('count', 0)} deals (${stats.get('value', 0):,.2f})")

    rprint(f"\n[bold]Active Pipeline[/bold]")
    rprint(f"  Active deals: {active.get('active_deals_count', 0)}")
    rprint(f"  Total value: ${active.get('total_value', 0):,.2f}")
    rprint(f"  Adjusted value: ${active.get('adjusted_value', 0):,.2f}")

    rprint(f"\n[bold]Leads[/bold]")
    rprint(f"  This period: {leads.get('current_period', 0)}")
    rprint(f"  Previous: {leads.get('previous_period', 0)}")
    rprint(f"  Change: {leads.get('change', 0):+d}")
    rprint(f"  Total: {leads.get('total', 0)}")

    rprint(f"\n[bold]Messages Sent[/bold]")
    rprint(f"  This period: {messages.get('current_period', 0)}")
    rprint(f"  Previous: {messages.get('previous_period', 0)}")
    rprint(f"  Change: {messages.get('change', 0):+d}")


# =============================================================================
# LISTS
# =============================================================================

lists_app = typer.Typer(help="List management operations")
app.add_typer(lists_app, name="lists")


@lists_app.callback()
def lists_callback() -> None:
    pass


@lists_app.command("list")
def lists_list(
    limit: int = typer.Option(100, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
) -> None:
    """List all CRM lists."""
    with get_api_client() as client:
        try:
            resp = client.get("/crm/lists/", params={"limit": limit, "offset": offset})
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
        return

    print_table(
        data.get("data", []),
        [
            ("name", "Name"),
            ("type", "Type"),
            ("member_type", "Member Type"),
            ("member_count", "Members"),
            ("id", "ID"),
        ],
        title=f"Lists ({data.get('total', '?')} total)",
    )


@lists_app.command("get")
def lists_get(
    list_id: str = typer.Argument(..., help="List ID"),
) -> None:
    """Get a list by ID."""
    with get_api_client() as client:
        try:
            resp = client.get(f"/crm/lists/{list_id}")
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
        return

    print_detail(data, [
        ("id", "ID"),
        ("name", "Name"),
        ("description", "Description"),
        ("type", "Type"),
        ("member_type", "Member Type"),
        ("member_count", "Members"),
        ("created_at", "Created"),
        ("updated_at", "Updated"),
    ])


@lists_app.command("create")
def lists_create(
    name: str = typer.Option(..., help="List name"),
    member_type: str = typer.Option("mixed", "--member-type", help="person, company, or mixed"),
    description: Optional[str] = typer.Option(None, help="Description"),
    list_type: str = typer.Option("static", "--type", help="static or dynamic"),
) -> None:
    """Create a new list."""
    body: dict = {"name": name, "type": list_type, "member_type": member_type}
    if description:
        body["description"] = description

    with get_api_client() as client:
        try:
            me = client.get("/whoami")
            me.raise_for_status()
            body["organization_id"] = me.json()["organization_id"]

            resp = client.post("/crm/lists/", json=body)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
    else:
        rprint(f"[green]Created list:[/green] {data['name']} ({data['id']})")


@lists_app.command("members")
def lists_members(
    list_id: str = typer.Argument(..., help="List ID"),
    limit: int = typer.Option(100, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
) -> None:
    """List members of a list."""
    with get_api_client() as client:
        try:
            resp = client.get(
                f"/crm/lists/{list_id}/members",
                params={"limit": limit, "offset": offset},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
        return

    print_table(
        data.get("data", []),
        [
            ("person_id", "Person ID"),
            ("company_id", "Company ID"),
            ("added_at", "Added At"),
            ("position", "Position"),
        ],
        title=f"Members ({data.get('total', '?')} total)",
    )


@lists_app.command("add-member")
def lists_add_member(
    list_id: str = typer.Argument(..., help="List ID"),
    person_id: Optional[str] = typer.Option(None, "--person-id", help="Person ID"),
    company_id: Optional[str] = typer.Option(None, "--company-id", help="Company ID"),
) -> None:
    """Add a member to a list."""
    if not person_id and not company_id:
        rprint("[red]Must specify --person-id or --company-id[/red]")
        raise typer.Exit(code=1)

    body: dict = {}
    if person_id:
        body["person_id"] = person_id
    if company_id:
        body["company_id"] = company_id

    with get_api_client() as client:
        try:
            resp = client.post(f"/crm/lists/{list_id}/members", json=body)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    data = resp.json()
    if _json_flag:
        print_json(data)
    else:
        member_label = person_id or company_id
        rprint(f"[green]Added {member_label} to list {list_id}[/green]")


@lists_app.command("remove-member")
def lists_remove_member(
    list_id: str = typer.Argument(..., help="List ID"),
    person_id: Optional[str] = typer.Option(None, "--person-id", help="Person ID"),
    company_id: Optional[str] = typer.Option(None, "--company-id", help="Company ID"),
) -> None:
    """Remove a member from a list."""
    if person_id:
        member_type = "person"
        member_id = person_id
    elif company_id:
        member_type = "company"
        member_id = company_id
    else:
        rprint("[red]Must specify --person-id or --company-id[/red]")
        raise typer.Exit(code=1)

    with get_api_client() as client:
        try:
            resp = client.delete(f"/crm/lists/{list_id}/members/{member_type}/{member_id}")
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    rprint(f"[green]Removed {member_type} {member_id} from list {list_id}[/green]")


@lists_app.command("delete")
def lists_delete(
    list_id: str = typer.Argument(..., help="List ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a list."""
    if not yes:
        typer.confirm(f"Delete list {list_id}?", abort=True)

    with get_api_client() as client:
        try:
            resp = client.delete(f"/crm/lists/{list_id}")
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)

    rprint(f"[green]Deleted list {list_id}[/green]")
