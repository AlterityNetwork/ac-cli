"""CRM activities commands."""

from __future__ import annotations

from datetime import datetime, timezone

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _get_org_id,
    _resolve_company_id,
    _resolve_contact_id,
    _resolve_deal_id,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.crm import _CRM, _api_request, _build_body
from ac_cli.formatting import print_detail, print_json, print_table

activities_app = typer.Typer(help="Activity operations")


@activities_app.command("list")
def activities_list(
    ctx: typer.Context,
    deal_id: str | None = typer.Option(None, "--deal-id", help="Filter by deal"),
    company_id: str | None = typer.Option(None, "--company-id", help="Filter by company"),
    contact_id: str | None = typer.Option(None, "--contact-id", help="Filter by contact"),
    activity_type: str | None = typer.Option(None, "--type", help="Filter by type"),
    status: str | None = typer.Option(None, help="Filter by status"),
    search: str | None = typer.Option(
        None, "--search", help="Search activity title and description"
    ),
    assigned_to: str | None = typer.Option(
        None,
        "--assigned-to",
        help="Filter by assignee user_id. Pass 'me' to resolve to the authenticated user.",
    ),
    sort_by: str | None = typer.Option(
        None, "--sort-by", help="Sort field: due_date or created_at"
    ),
    limit: int = typer.Option(100, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List activities."""
    set_json_mode(json_output)
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
    if search:
        params["search"] = search
    if assigned_to:
        # Sentinel: 'me' resolves to the authenticated user via /whoami so
        # agents don't have to pre-resolve the user_id.
        if assigned_to == "me":
            whoami_resp = _api_request("get", "/whoami")
            whoami = whoami_resp.json()
            assigned_to = whoami.get("user_id") or assigned_to
        params["assigned_to"] = assigned_to
    if sort_by:
        params["sort_by"] = sort_by

    resp = _api_request("get", f"{_CRM}/activities", params=params)

    data = resp.json()
    if json_output:
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
    ctx: typer.Context,
    activity_id: str = typer.Argument(..., help="Activity ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get an activity by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/activities/{activity_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
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
        ],
    )


@activities_app.command("create")
def activities_create(
    ctx: typer.Context,
    activity_type: str = typer.Option(
        ..., "--type", help="Activity type (call, meeting, email, task, note)"
    ),
    title: str = typer.Option(..., help="Activity title"),
    due_date: str | None = typer.Option(None, "--due-date", help="Due date (ISO format)"),
    priority: str | None = typer.Option(None, help="Priority (low, medium, high, urgent)"),
    deal_id: str | None = typer.Option(None, "--deal-id", help="Deal ID"),
    deal_name: str | None = typer.Option(
        None, "--deal-name", help="Deal name (auto-resolves to ID)"
    ),
    company_id: str | None = typer.Option(None, "--company-id", help="Company ID"),
    company_name: str | None = typer.Option(
        None, "--company-name", help="Company name (auto-resolves to ID)"
    ),
    contact_id: str | None = typer.Option(None, "--contact-id", help="Contact ID"),
    contact_name: str | None = typer.Option(
        None, "--contact-name", help="Contact name (auto-resolves to ID)"
    ),
    description: str | None = typer.Option(None, help="Description"),
    assigned_to: str | None = typer.Option(
        None,
        "--assigned-to",
        help="Assignee user_id. Pass 'me' to resolve to the authenticated user.",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new activity."""
    set_json_mode(json_output)
    resolved_deal = _resolve_deal_id(deal_id, deal_name, _CRM)
    resolved_company = _resolve_company_id(company_id, company_name, _CRM)
    resolved_contact = _resolve_contact_id(contact_id, contact_name, _CRM)
    if assigned_to == "me":
        whoami = _api_request("get", "/whoami").json()
        assigned_to = whoami.get("user_id") or assigned_to
    body = _build_body(
        type=activity_type,
        title=title,
        due_date=due_date,
        priority=priority,
        deal_id=resolved_deal,
        company_id=resolved_company,
        contact_id=resolved_contact,
        description=description,
        assigned_to=assigned_to,
    )

    body["organization_id"] = _get_org_id()

    resp = _api_request("post", f"{_CRM}/activities", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Created activity:[/green] {data['title']} ({data['id']})")


@activities_app.command("bulk-create")
def activities_bulk_create(
    ctx: typer.Context,
    title: str = typer.Option(..., help="Activity title (applied to every record)"),
    member_type: str = typer.Option(..., "--member-type", help="person or company"),
    ids: str = typer.Option(..., "--ids", help="Comma-separated person or company IDs"),
    activity_type: str = typer.Option(
        "task", "--type", help="Activity type (task, note, call, meeting)"
    ),
    description: str | None = typer.Option(None, help="Description"),
    due_date: str | None = typer.Option(None, "--due-date", help="Due date (ISO format)"),
    priority: str | None = typer.Option(None, help="Priority (low, medium, high, urgent)"),
    assigned_to: str | None = typer.Option(
        None,
        "--assigned-to",
        help="Assignee user_id. Pass 'me' to resolve to the authenticated user.",
    ),
    duration_minutes: int | None = typer.Option(
        None, "--duration-minutes", help="Duration in minutes (call/meeting)"
    ),
    location: str | None = typer.Option(None, help="Location (meeting)"),
    source_app: str = typer.Option(
        "manual",
        "--source-app",
        help="Source slug; 'manual' stamps the records Actioned/Approved",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create one activity per selected person/company (bulk).

    The same content is applied to every record, mirroring the People/Companies
    list 'Create activity' action. organization_id comes from the authenticated
    user, not the body.
    """
    set_json_mode(json_output)
    if member_type not in ("person", "company"):
        rprint("[red]--member-type must be 'person' or 'company'[/red]")
        raise typer.Exit(code=1)

    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        rprint("[red]No IDs provided[/red]")
        raise typer.Exit(code=1)

    if assigned_to == "me":
        whoami = _api_request("get", "/whoami").json()
        assigned_to = whoami.get("user_id") or assigned_to

    body = _build_body(
        type=activity_type,
        title=title,
        description=description,
        due_date=due_date,
        priority=priority,
        assigned_to=assigned_to,
        duration_minutes=duration_minutes,
        location=location,
        source_app=source_app,
    )
    body["member_type"] = member_type
    body["member_ids"] = id_list

    resp = _api_request("post", f"{_CRM}/activities/bulk-create", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    created = int(data.get("created_count", 0))
    noun = activity_type if created == 1 else f"{activity_type}s"
    rprint(f"[green]Created {created} {noun}[/green] for {len(id_list)} {member_type}(s)")


@activities_app.command("update")
def activities_update(
    ctx: typer.Context,
    activity_id: str = typer.Argument(..., help="Activity ID"),
    title: str | None = typer.Option(None, help="Activity title"),
    activity_type: str | None = typer.Option(
        None, "--type", help="Activity type (call, meeting, email, task, note)"
    ),
    status: str | None = typer.Option(
        None, help="Status (pending, in_progress, completed, cancelled)"
    ),
    priority: str | None = typer.Option(None, help="Priority (low, medium, high, urgent)"),
    due_date: str | None = typer.Option(None, "--due-date", help="Due date (ISO format)"),
    description: str | None = typer.Option(None, help="Description"),
    deal_id: str | None = typer.Option(None, "--deal-id", help="Deal ID"),
    deal_name: str | None = typer.Option(
        None, "--deal-name", help="Deal name (auto-resolves to ID)"
    ),
    company_id: str | None = typer.Option(None, "--company-id", help="Company ID"),
    company_name: str | None = typer.Option(
        None, "--company-name", help="Company name (auto-resolves to ID)"
    ),
    contact_id: str | None = typer.Option(None, "--contact-id", help="Contact ID"),
    contact_name: str | None = typer.Option(
        None, "--contact-name", help="Contact name (auto-resolves to ID)"
    ),
    assigned_to: str | None = typer.Option(
        None,
        "--assigned-to",
        help="Assignee user_id. Pass 'me' to resolve to the authenticated user.",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update an existing activity."""
    set_json_mode(json_output)
    resolved_deal = _resolve_deal_id(deal_id, deal_name, _CRM)
    resolved_company = _resolve_company_id(company_id, company_name, _CRM)
    resolved_contact = _resolve_contact_id(contact_id, contact_name, _CRM)
    if assigned_to == "me":
        whoami = _api_request("get", "/whoami").json()
        assigned_to = whoami.get("user_id") or assigned_to
    body = _build_body(
        title=title,
        type=activity_type,
        status=status,
        priority=priority,
        due_date=due_date,
        description=description,
        deal_id=resolved_deal,
        company_id=resolved_company,
        contact_id=resolved_contact,
        assigned_to=assigned_to,
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_CRM}/activities/{activity_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated activity:[/green] {data['title']} ({data['id']})")


@activities_app.command("complete")
def activities_complete(
    ctx: typer.Context,
    activity_id: str = typer.Argument(..., help="Activity ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Mark an activity as completed."""
    set_json_mode(json_output)
    now = datetime.now(timezone.utc).isoformat()
    resp = _api_request(
        "patch",
        f"{_CRM}/activities/{activity_id}",
        json={"status": "completed", "completed_at": now},
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Completed activity:[/green] {data['title']} ({data['id']})")


@activities_app.command("delete")
def activities_delete(
    activity_id: str = typer.Argument(..., help="Activity ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete an activity."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete activity {activity_id}?", abort=True)

    _api_request("delete", f"{_CRM}/activities/{activity_id}")

    if json_output:
        print_json({"ok": True, "id": activity_id, "action": "delete"})
    else:
        rprint(f"[green]Deleted activity {activity_id}[/green]")
