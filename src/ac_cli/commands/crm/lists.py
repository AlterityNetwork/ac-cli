"""CRM lists commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _get_org_id, set_json_mode, should_skip_confirm
from ac_cli.commands.crm import _CRM, _api_request, _build_body
from ac_cli.formatting import print_detail, print_json, print_table

lists_app = typer.Typer(help="List management operations")


@lists_app.command("list")
def lists_list(
    ctx: typer.Context,
    limit: int = typer.Option(100, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List all CRM lists."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/lists", params={"limit": limit, "offset": offset})

    data = resp.json()
    if json_output:
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
    ctx: typer.Context,
    list_id: str = typer.Argument(..., help="List ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a list by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/lists/{list_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("name", "Name"),
            ("description", "Description"),
            ("type", "Type"),
            ("member_type", "Member Type"),
            ("member_count", "Members"),
            ("created_at", "Created"),
            ("updated_at", "Updated"),
        ],
    )


@lists_app.command("create")
def lists_create(
    ctx: typer.Context,
    name: str = typer.Option(..., help="List name"),
    member_type: str = typer.Option("mixed", "--member-type", help="person, company, or mixed"),
    description: str | None = typer.Option(None, help="Description"),
    list_type: str = typer.Option("static", "--type", help="static or dynamic"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new list."""
    set_json_mode(json_output)
    body = _build_body(
        name=name,
        type=list_type,
        member_type=member_type,
        description=description,
    )

    body["organization_id"] = _get_org_id()

    resp = _api_request("post", f"{_CRM}/lists", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Created list:[/green] {data['name']} ({data['id']})")


@lists_app.command("update")
def lists_update(
    ctx: typer.Context,
    list_id: str = typer.Argument(..., help="List ID"),
    name: str | None = typer.Option(None, help="List name"),
    description: str | None = typer.Option(None, help="Description"),
    list_type: str | None = typer.Option(None, "--type", help="static or dynamic"),
    member_type: str | None = typer.Option(None, "--member-type", help="person, company, or mixed"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update an existing list."""
    set_json_mode(json_output)
    body = _build_body(
        name=name,
        description=description,
        type=list_type,
        member_type=member_type,
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_CRM}/lists/{list_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated list:[/green] {data['name']} ({data['id']})")


@lists_app.command("members")
def lists_members(
    ctx: typer.Context,
    list_id: str = typer.Argument(..., help="List ID"),
    limit: int = typer.Option(100, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List members of a list."""
    set_json_mode(json_output)
    resp = _api_request(
        "get",
        f"{_CRM}/lists/{list_id}/members",
        params={"limit": limit, "offset": offset},
    )

    data = resp.json()
    if json_output:
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


@lists_app.command("lists-for-member")
def lists_for_member(
    ctx: typer.Context,
    person_id: str | None = typer.Option(None, "--person-id", help="Person ID"),
    company_id: str | None = typer.Option(None, "--company-id", help="Company ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List CRM lists that contain the given person or company."""
    set_json_mode(json_output)
    if person_id:
        member_type, member_id = "person", person_id
    elif company_id:
        member_type, member_id = "company", company_id
    else:
        rprint("[red]Must specify --person-id or --company-id[/red]")
        raise typer.Exit(code=1)

    resp = _api_request("get", f"{_CRM}/members/{member_type}/{member_id}/lists")
    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data,
        [
            ("id", "ID"),
            ("name", "Name"),
            ("type", "Type"),
            ("member_type", "Member Type"),
        ],
        title=f"Lists for {member_type} {member_id} ({len(data)} total)",
    )


@lists_app.command("add-member")
def lists_add_member(
    ctx: typer.Context,
    list_id: str = typer.Argument(..., help="List ID"),
    person_id: str | None = typer.Option(None, "--person-id", help="Person ID"),
    company_id: str | None = typer.Option(None, "--company-id", help="Company ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Add a member to a list."""
    set_json_mode(json_output)
    if not person_id and not company_id:
        rprint("[red]Must specify --person-id or --company-id[/red]")
        raise typer.Exit(code=1)

    body = _build_body(person_id=person_id, company_id=company_id)

    resp = _api_request("post", f"{_CRM}/lists/{list_id}/members", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        member_label = person_id or company_id
        rprint(f"[green]Added {member_label} to list {list_id}[/green]")


@lists_app.command("remove-member")
def lists_remove_member(
    list_id: str = typer.Argument(..., help="List ID"),
    person_id: str | None = typer.Option(None, "--person-id", help="Person ID"),
    company_id: str | None = typer.Option(None, "--company-id", help="Company ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Remove a member from a list."""
    set_json_mode(json_output)
    if person_id:
        member_type = "person"
        member_id = person_id
    elif company_id:
        member_type = "company"
        member_id = company_id
    else:
        rprint("[red]Must specify --person-id or --company-id[/red]")
        raise typer.Exit(code=1)

    _api_request("delete", f"{_CRM}/lists/{list_id}/members/{member_type}/{member_id}")

    if json_output:
        print_json(
            {
                "ok": True,
                "list_id": list_id,
                "member_type": member_type,
                "member_id": member_id,
                "action": "remove-member",
            }
        )
    else:
        rprint(f"[green]Removed {member_type} {member_id} from list {list_id}[/green]")


@lists_app.command("add-members")
def lists_add_members(
    list_id: str = typer.Argument(..., help="List ID"),
    member_type: str = typer.Option(..., "--member-type", help="person or company"),
    ids: str = typer.Option(..., "--ids", help="Comma-separated member IDs"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Bulk-add members (person or company) to a list with server-side dedup."""
    set_json_mode(json_output)
    if member_type not in ("person", "company"):
        rprint("[red]--member-type must be 'person' or 'company'[/red]")
        raise typer.Exit(code=1)

    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        rprint("[red]No IDs provided[/red]")
        raise typer.Exit(code=1)

    resp = _api_request(
        "post",
        f"{_CRM}/lists/{list_id}/members/bulk-add",
        json={"member_type": member_type, "member_ids": id_list},
    )
    body = resp.json() if resp.content else {}
    added = int(body.get("added_count", 0))
    duplicates = int(body.get("duplicate_count", 0))

    if json_output:
        print_json(
            {
                "ok": True,
                "list_id": list_id,
                "member_type": member_type,
                "member_ids": id_list,
                "added_count": added,
                "duplicate_count": duplicates,
                "action": "add-members",
            }
        )
        return

    if duplicates:
        rprint(
            f"[green]Added {added} {member_type}(s) to list {list_id}[/green] "
            f"[dim]({duplicates} already on the list)[/dim]"
        )
    else:
        rprint(f"[green]Added {added} {member_type}(s) to list {list_id}[/green]")


@lists_app.command("bulk-remove-members")
def lists_bulk_remove_members(
    list_id: str = typer.Argument(..., help="List ID"),
    member_type: str = typer.Option(..., "--member-type", help="person or company"),
    ids: str = typer.Option(..., "--ids", help="Comma-separated member IDs"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Bulk remove members (person or company) from a list."""
    set_json_mode(json_output)
    if member_type not in ("person", "company"):
        rprint("[red]--member-type must be 'person' or 'company'[/red]")
        raise typer.Exit(code=1)

    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        rprint("[red]No IDs provided[/red]")
        raise typer.Exit(code=1)

    if not should_skip_confirm(yes):
        typer.confirm(f"Remove {len(id_list)} {member_type}(s) from list {list_id}?", abort=True)

    _api_request(
        "post",
        f"{_CRM}/lists/{list_id}/members/bulk-remove",
        json={"member_type": member_type, "member_ids": id_list},
    )

    if json_output:
        print_json(
            {
                "ok": True,
                "list_id": list_id,
                "member_type": member_type,
                "member_ids": id_list,
                "count": len(id_list),
                "action": "bulk-remove-members",
            }
        )
    else:
        rprint(f"[green]Removed {len(id_list)} {member_type}(s) from list {list_id}[/green]")


@lists_app.command("bulk-move-members")
def lists_bulk_move_members(
    list_id: str = typer.Argument(..., help="Source list ID"),
    target_list_id: str = typer.Option(..., "--target-list-id", help="Destination list ID"),
    member_type: str = typer.Option(..., "--member-type", help="person or company"),
    ids: str = typer.Option(..., "--ids", help="Comma-separated member IDs"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Move members (person or company) from one list to another.

    Adds to the target with server-side dedup, then removes from the source.
    Members already on the target are reported as duplicates and still
    removed from the source.
    """
    set_json_mode(json_output)
    if member_type not in ("person", "company"):
        rprint("[red]--member-type must be 'person' or 'company'[/red]")
        raise typer.Exit(code=1)

    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        rprint("[red]No IDs provided[/red]")
        raise typer.Exit(code=1)

    if not should_skip_confirm(yes):
        typer.confirm(
            f"Move {len(id_list)} {member_type}(s) from list {list_id} to list {target_list_id}?",
            abort=True,
        )

    resp = _api_request(
        "post",
        f"{_CRM}/lists/{list_id}/members/bulk-move",
        json={
            "target_list_id": target_list_id,
            "member_type": member_type,
            "member_ids": id_list,
        },
    )
    body = resp.json() if resp.content else {}
    moved = int(body.get("moved_count", 0))
    duplicates = int(body.get("duplicate_count", 0))

    if json_output:
        print_json(
            {
                "ok": True,
                "list_id": list_id,
                "target_list_id": target_list_id,
                "member_type": member_type,
                "member_ids": id_list,
                "moved_count": moved,
                "duplicate_count": duplicates,
                "action": "bulk-move-members",
            }
        )
        return

    if duplicates:
        rprint(
            f"[green]Moved {moved} {member_type}(s) from list {list_id} "
            f"to list {target_list_id}[/green] "
            f"[dim]({duplicates} already on the target, removed from source)[/dim]"
        )
    else:
        rprint(
            f"[green]Moved {moved} {member_type}(s) from list {list_id} "
            f"to list {target_list_id}[/green]"
        )


@lists_app.command("delete")
def lists_delete(
    list_id: str = typer.Argument(..., help="List ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete a list."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete list {list_id}?", abort=True)

    _api_request("delete", f"{_CRM}/lists/{list_id}")

    if json_output:
        print_json({"ok": True, "id": list_id, "action": "delete"})
    else:
        rprint(f"[green]Deleted list {list_id}[/green]")
