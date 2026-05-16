"""User profile management commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, _build_body, set_json_mode
from ac_cli.formatting import print_detail, print_json, print_table

app = typer.Typer(help="User profile management")

_PROFILES = "/api/v1/profiles"


@app.callback()
def profiles_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@app.command("me")
def profiles_me(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Get the current user's profile."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_PROFILES}/me")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("first_name", "First Name"),
            ("last_name", "Last Name"),
            ("email", "Email"),
            ("job_title", "Job Title"),
            ("bio", "Bio"),
            ("is_superadmin", "Superadmin"),
            ("selected_organization", "Organization"),
        ],
    )


@app.command("update")
def profiles_update(
    ctx: typer.Context,
    first_name: str | None = typer.Option(None, "--first-name", help="First name"),
    last_name: str | None = typer.Option(None, "--last-name", help="Last name"),
    bio: str | None = typer.Option(None, "--bio", help="Bio"),
    job_title: str | None = typer.Option(None, "--job-title", help="Job title"),
    avatar_url: str | None = typer.Option(None, "--avatar-url", help="Avatar URL"),
    email: str | None = typer.Option(None, "--email", help="Email address"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update the current user's profile."""
    set_json_mode(json_output)
    body = _build_body(
        first_name=first_name,
        last_name=last_name,
        bio=bio,
        job_title=job_title,
        avatar_url=avatar_url,
        email=email,
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_PROFILES}/me", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint("[green]Profile updated.[/green]")


@app.command("set-organization")
def profiles_set_organization(
    ctx: typer.Context,
    organization_id: str = typer.Argument(..., help="Organization ID to select"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Switch the current user's selected organization."""
    set_json_mode(json_output)
    resp = _api_request(
        "patch",
        f"{_PROFILES}/me/organization",
        json={"organization_id": organization_id},
    )
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Selected organization {organization_id}[/green]")


@app.command("set-password")
def profiles_set_password(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Mark current user's password as set (post-Supabase magic-link signup)."""
    set_json_mode(json_output)
    _api_request("patch", f"{_PROFILES}/me/password-set")
    if json_output:
        print_json({"ok": True})
    else:
        rprint("[green]Password marked as set[/green]")


@app.command("subscription")
def profiles_subscription(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Show the current user's organization subscription."""
    set_json_mode(json_output)
    resp = _api_request("get", "/api/v1/subscriptions/me")
    data = resp.json()
    if json_output:
        print_json(data)
        return
    print_detail(
        data,
        [
            ("id", "ID"),
            ("plan_id", "Plan"),
            ("billing_period", "Billing"),
            ("status", "Status"),
            ("started_at", "Started"),
            ("ended_at", "Ended"),
            ("trial_ends_at", "Trial Ends"),
        ],
    )


@app.command("members")
def profiles_members(
    ctx: typer.Context,
    limit: int = typer.Option(50, help="Max items to return"),
    offset: int = typer.Option(0, help="Offset for pagination"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List organization members."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_PROFILES}/members", params={"limit": limit, "offset": offset})

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("data", [])
    if not items:
        rprint("[dim]No members found.[/dim]")
        return

    print_table(
        items,
        [
            ("id", "ID"),
            ("first_name", "First Name"),
            ("last_name", "Last Name"),
            ("email", "Email"),
            ("job_title", "Job Title"),
        ],
        title=f"Members ({data.get('total', '?')} total)",
    )
