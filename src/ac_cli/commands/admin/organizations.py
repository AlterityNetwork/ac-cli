"""Admin organization management commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import _api_request, _build_body, should_skip_confirm, JSON_OPTION, set_json_mode
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_detail, print_json, print_table

organizations_app = typer.Typer(help="Organization management")


@organizations_app.command("list")
def organizations_list(
    ctx: typer.Context,
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
    sort: str | None = typer.Option(None, help="Sort field"),
    order: str | None = typer.Option(None, help="Sort order (asc/desc)"),
    page: int = typer.Option(1, help="Page number"),
    page_size: int = typer.Option(50, "--page-size", help="Page size"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List organizations."""
    set_json_mode(json_output)
    params: dict = {"page": page, "page_size": page_size}
    if query:
        params["query"] = query
    if sort:
        params["sort"] = sort
    if order:
        params["order"] = order

    resp = _api_request("get", f"{_ADMIN}/organizations", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data.get("data", []),
        [
            ("name", "Name"),
            ("id", "ID"),
        ],
        title=f"Organizations ({data.get('total', '?')} total)",
    )


@organizations_app.command("get")
def organizations_get(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organization ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get an organization by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/organizations/{org_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, [
        ("id", "ID"),
        ("name", "Name"),
        ("slug", "Slug"),
        ("plan", "Plan"),
        ("created_at", "Created"),
    ])


@organizations_app.command("create")
def organizations_create(
    ctx: typer.Context,
    name: str = typer.Option(..., help="Organization name"),
    slug: str | None = typer.Option(None, help="Organization slug"),
    plan: str | None = typer.Option(None, help="Plan"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new organization."""
    set_json_mode(json_output)
    body = _build_body(name=name, slug=slug, plan=plan)

    resp = _api_request("post", f"{_ADMIN}/organizations", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Created org:[/green] {data['name']} ({data['id']})")


@organizations_app.command("update")
def organizations_update(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organization ID"),
    name: str | None = typer.Option(None, help="Organization name"),
    slug: str | None = typer.Option(None, help="Organization slug"),
    plan: str | None = typer.Option(None, help="Plan"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update an existing organization."""
    set_json_mode(json_output)
    body = _build_body(name=name, slug=slug, plan=plan)

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_ADMIN}/organizations/{org_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated org:[/green] {data['name']} ({data['id']})")


@organizations_app.command("delete")
def organizations_delete(
    org_id: str = typer.Argument(..., help="Organization ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete an organization."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete organization {org_id}?", abort=True)

    _api_request("delete", f"{_ADMIN}/organizations/{org_id}")

    rprint(f"[green]Deleted organization {org_id}[/green]")


@organizations_app.command("members")
def organizations_members(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organization ID"),
    page: int = typer.Option(1, help="Page number"),
    page_size: int = typer.Option(50, "--page-size", help="Page size"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List members of an organization."""
    set_json_mode(json_output)
    resp = _api_request(
        "get",
        f"{_ADMIN}/organizations/{org_id}/members",
        params={"page": page, "page_size": page_size},
    )

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data.get("data", []),
        [
            ("user_id", "User ID"),
            ("email", "Email"),
            ("role", "Role"),
        ],
        title=f"Members ({data.get('total', '?')} total)",
    )


@organizations_app.command("add-member")
def organizations_add_member(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organization ID"),
    user_id: str = typer.Option(..., "--user-id", help="User ID to add"),
    role: str | None = typer.Option(None, help="Member role"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Add a member to an organization."""
    set_json_mode(json_output)
    body = _build_body(user_id=user_id, role=role)

    resp = _api_request("post", f"{_ADMIN}/organizations/{org_id}/members", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Added user {user_id} to organization {org_id}[/green]")


@organizations_app.command("update-member")
def organizations_update_member(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organization ID"),
    user_id: str = typer.Argument(..., help="User ID"),
    role: str = typer.Option(..., help="New role"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a member's role in an organization."""
    set_json_mode(json_output)
    resp = _api_request(
        "patch",
        f"{_ADMIN}/organizations/{org_id}/members/{user_id}",
        json={"role": role},
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated member {user_id} role to {role}[/green]")


@organizations_app.command("remove-member")
def organizations_remove_member(
    org_id: str = typer.Argument(..., help="Organization ID"),
    user_id: str = typer.Argument(..., help="User ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Remove a member from an organization."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Remove user {user_id} from organization {org_id}?", abort=True)

    _api_request("delete", f"{_ADMIN}/organizations/{org_id}/members/{user_id}")

    rprint(f"[green]Removed user {user_id} from organization {org_id}[/green]")


@organizations_app.command("transfer-ownership")
def organizations_transfer_ownership(
    org_id: str = typer.Argument(..., help="Organization ID"),
    new_owner_id: str = typer.Option(..., "--new-owner-id", help="New owner user ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Transfer organization ownership."""
    if not should_skip_confirm(yes):
        typer.confirm(
            f"Transfer ownership of organization {org_id} to {new_owner_id}?",
            abort=True,
        )

    _api_request(
        "post",
        f"{_ADMIN}/organizations/{org_id}/transfer-ownership",
        json={"new_owner_id": new_owner_id},
    )

    rprint(f"[green]Transferred ownership of organization {org_id} to {new_owner_id}[/green]")
