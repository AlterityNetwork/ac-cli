"""Admin user management commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_detail, print_json, print_table

_IMPERSONATION = "/api/v1/impersonation"

users_app = typer.Typer(help="User management")


@users_app.command("list")
def users_list(
    ctx: typer.Context,
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
    sort: str | None = typer.Option(None, help="Sort field"),
    order: str | None = typer.Option(None, help="Sort order (asc/desc)"),
    page: int = typer.Option(1, help="Page number"),
    page_size: int = typer.Option(50, "--page-size", help="Page size"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List users."""
    set_json_mode(json_output)
    params: dict = {"page": page, "page_size": page_size}
    if query:
        params["q"] = query
    if sort:
        params["sort"] = sort
    if order:
        params["order"] = order

    resp = _api_request("get", f"{_ADMIN}/users", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data.get("items", []),
        [
            ("email", "Email"),
            ("id", "ID"),
        ],
        title=f"Users ({data.get('total', '?')} total)",
    )


@users_app.command("get")
def users_get(
    ctx: typer.Context,
    user_id: str = typer.Argument(..., help="User ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a user by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/users/{user_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("email", "Email"),
            ("full_name", "Full Name"),
            ("organization_id", "Organization ID"),
            ("is_superadmin", "Superadmin"),
            ("created_at", "Created"),
        ],
    )


@users_app.command("create")
def users_create(
    ctx: typer.Context,
    email: str = typer.Option(..., help="User email"),
    password: str = typer.Option(..., help="User password"),
    full_name: str | None = typer.Option(None, "--full-name", help="Full name"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new user."""
    set_json_mode(json_output)
    first_name: str | None = None
    last_name: str | None = None
    if full_name:
        parts = full_name.strip().split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else None
    body = _build_body(email=email, password=password, first_name=first_name, last_name=last_name)

    resp = _api_request("post", f"{_ADMIN}/users", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Created user:[/green] {data['id']}")


@users_app.command("update")
def users_update(
    ctx: typer.Context,
    user_id: str = typer.Argument(..., help="User ID"),
    full_name: str | None = typer.Option(None, "--full-name", help="Full name"),
    is_superadmin: bool | None = typer.Option(None, "--is-superadmin", help="Superadmin status"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update an existing user."""
    set_json_mode(json_output)
    first_name: str | None = None
    last_name: str | None = None
    if full_name:
        parts = full_name.strip().split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else None
    body = _build_body(first_name=first_name, last_name=last_name, is_superadmin=is_superadmin)

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_ADMIN}/users/{user_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated user:[/green] {data['id']}")


@users_app.command("delete")
def users_delete(
    user_id: str = typer.Argument(..., help="User ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a user."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete user {user_id}?", abort=True)

    _api_request("delete", f"{_ADMIN}/users/{user_id}")

    rprint(f"[green]Deleted user {user_id}[/green]")


@users_app.command("auth-search")
def users_auth_search(
    ctx: typer.Context,
    email: str = typer.Option(..., help="Email to search for in Supabase Auth"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Search for a user in Supabase Auth by email."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/users/auth-search", params={"email": email})

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        print_detail(
            data,
            [
                ("id", "ID"),
                ("email", "Email"),
                ("created_at", "Created"),
                ("email_confirmed_at", "Email Confirmed"),
                ("last_sign_in_at", "Last Sign In"),
            ],
        )


@users_app.command("search")
def users_search(
    ctx: typer.Context,
    email: str = typer.Option(..., help="Email to search for"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Search users by email."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/users/search", params={"email": email})

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(data)


@users_app.command("reset-password")
def users_reset_password(
    user_id: str = typer.Argument(..., help="User ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Reset a user's password."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Reset password for user {user_id}?", abort=True)

    _api_request("post", f"{_ADMIN}/users/{user_id}/reset-password")

    rprint(f"[green]Password reset for user {user_id}[/green]")


@users_app.command("require-tos-resign")
def users_require_tos_resign(
    ctx: typer.Context,
    user_id: str = typer.Argument(..., help="User ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Require a user to re-sign the current Terms of Service."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Require ToS re-sign for user {user_id}?", abort=True)

    resp = _api_request("post", f"{_ADMIN}/users/{user_id}/require-tos-resign")
    data = resp.json() if resp.content else {"id": user_id}

    if json_output:
        print_json(data)
    else:
        rprint(f"[green]ToS re-sign required for user {data['id']}[/green]")


@users_app.command("impersonate")
def users_impersonate(
    user_id: str = typer.Argument(..., help="User ID"),
) -> None:
    """Impersonate a user."""
    _api_request("post", f"{_ADMIN}/users/{user_id}/impersonate")

    rprint(f"[green]Impersonating user {user_id}[/green]")


@users_app.command("exit-impersonation")
def users_exit_impersonation() -> None:
    """Exit impersonation mode."""
    _api_request("post", f"{_ADMIN}/users/impersonate/exit")

    rprint("[green]Exited impersonation[/green]")


@users_app.command("impersonation-status")
def users_impersonation_status(
    ctx: typer.Context,
    session_id: str = typer.Option(..., "--session-id", help="Impersonation session ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get the current state of an impersonation session."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_IMPERSONATION}/me", params={"session_id": session_id})

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("session_id", "Session"),
            ("target_user_id", "Target"),
            ("started_at", "Started"),
            ("expires_at", "Expires"),
            ("active", "Active"),
        ],
    )


@users_app.command("impersonation-end")
def users_impersonation_end(
    ctx: typer.Context,
    session_id: str = typer.Option(..., "--session-id", help="Impersonation session ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """End an active impersonation session."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_IMPERSONATION}/me/end", json={"session_id": session_id})

    data = resp.json() if resp.content else {"ok": True, "session_id": session_id}
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Ended impersonation session {session_id}[/green]")


@users_app.command("generate-link")
def users_generate_link(
    user_id: str = typer.Argument(..., help="User ID"),
    send_email: bool = typer.Option(False, "--send-email", help="Send email with link"),
) -> None:
    """Generate an impersonation link for a user."""
    resp = _api_request(
        "post",
        f"{_ADMIN}/users/{user_id}/generate-impersonation-link",
        params={"send_email": send_email},
    )

    data = resp.json()
    rprint(f"[green]Impersonation link:[/green] {data.get('link', data)}")


@users_app.command("suspension-messages")
def users_suspension_messages(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """List available suspension messages."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/suspension-messages")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("messages", [])
    print_table(items, [("id", "ID"), ("message", "Message")], title="Suspension Messages")


@users_app.command("suspend")
def users_suspend(
    ctx: typer.Context,
    user_id: str = typer.Argument(..., help="User ID"),
    reason: str | None = typer.Option(None, "--reason", help="Suspension reason"),
    message_id: str | None = typer.Option(None, "--message-id", help="Suspension message ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Suspend a user."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Suspend user {user_id}?", abort=True)

    body = _build_body(reason=reason, message_id=message_id)
    resp = _api_request("post", f"{_ADMIN}/users/{user_id}/suspend", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Suspended user {user_id}[/green]")


@users_app.command("activate")
def users_activate(
    ctx: typer.Context,
    user_id: str = typer.Argument(..., help="User ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Activate (unsuspend) a user."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_ADMIN}/users/{user_id}/activate")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Activated user {user_id}[/green]")
