"""Admin managed onboarding account management commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import _api_request, _build_body, should_skip_confirm
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_json, print_table

onboarding_app = typer.Typer(help="Managed onboarding account management")

_ONBOARDING = f"{_ADMIN}/onboarding"


@onboarding_app.command("create")
def onboarding_create(
    ctx: typer.Context,
    email: str = typer.Option(..., help="User email"),
    first_name: str = typer.Option(..., "--first-name", help="First name"),
    last_name: str = typer.Option(..., "--last-name", help="Last name"),
    org_name: str = typer.Option(..., "--org-name", help="Organization name"),
    website_url: str | None = typer.Option(None, "--website-url", help="Organization website URL"),
    country: str | None = typer.Option(None, help="Country code"),
    timezone: str | None = typer.Option(None, help="Timezone"),
    locale: str | None = typer.Option(None, help="Locale"),
    currency: str | None = typer.Option(None, help="Currency code"),
    job_title: str | None = typer.Option(None, "--job-title", help="Job title"),
    bio: str | None = typer.Option(None, help="User bio"),
    user_website: str | None = typer.Option(None, "--user-website", help="User website URL"),
    logo_url: str | None = typer.Option(None, "--logo-url", help="Organization logo URL"),
    linkedin: str | None = typer.Option(None, help="LinkedIn URL"),
    contact_number: str | None = typer.Option(None, "--contact-number", help="Contact phone number"),
    contact_email: str | None = typer.Option(None, "--contact-email", help="Contact email"),
    description: str | None = typer.Option(None, help="Organization description"),
    products_services: str | None = typer.Option(None, "--products-services", help="Products/services"),
    calendly_url: str | None = typer.Option(None, "--calendly-url", help="Calendly URL"),
    show_calendly: bool | None = typer.Option(None, "--show-calendly/--no-show-calendly", help="Show Calendly widget"),
) -> None:
    """Create a new managed onboarding account."""
    body = _build_body(
        email=email,
        first_name=first_name,
        last_name=last_name,
        org_name=org_name,
        website_url=website_url,
        country=country,
        timezone=timezone,
        locale=locale,
        currency=currency,
        job_title=job_title,
        bio=bio,
        user_website=user_website,
        logo_url=logo_url,
        linkedin=linkedin,
        contact_number=contact_number,
        contact_email=contact_email,
        description=description,
        products_services=products_services,
    )

    onboarding_config = _build_body(calendly_url=calendly_url, show_calendly=show_calendly)
    if onboarding_config:
        body["onboarding_config"] = onboarding_config

    resp = _api_request("post", f"{_ONBOARDING}/accounts", json=body)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    print_table(
        [data],
        [
            ("user_id", "User ID"),
            ("organization_id", "Org ID"),
            ("onboarding_link", "Onboarding Link"),
            ("status", "Status"),
        ],
        title="Created Managed Account",
    )


@onboarding_app.command("list")
def onboarding_list(
    ctx: typer.Context,
    status: str | None = typer.Option(None, help="Filter by status (setup/pending/active)"),
    query: str | None = typer.Option(None, "--query", help="Search query"),
    page: int = typer.Option(1, help="Page number"),
    page_size: int = typer.Option(25, "--page-size", help="Page size"),
) -> None:
    """List managed onboarding accounts."""
    params: dict = {"page": page, "page_size": page_size}
    if status:
        params["status"] = status
    if query:
        params["q"] = query

    resp = _api_request("get", f"{_ONBOARDING}/accounts", params=params)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    print_table(
        data.get("items", data.get("data", [])),
        [
            ("organization_id", "Org ID"),
            ("organization_name", "Org Name"),
            ("user_email", "Email"),
            ("onboarding_status", "Status"),
            ("created_at", "Created"),
        ],
        title=f"Managed Accounts ({data.get('total', '?')} total)",
    )


@onboarding_app.command("get")
def onboarding_get(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organization ID"),
) -> None:
    """Get details of a managed onboarding account."""
    resp = _api_request("get", f"{_ONBOARDING}/accounts/{org_id}")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(data)


@onboarding_app.command("delete")
def onboarding_delete(
    org_id: str = typer.Argument(..., help="Organization ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a managed onboarding account."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete managed account {org_id}?", abort=True)

    _api_request("delete", f"{_ONBOARDING}/accounts/{org_id}")

    rprint(f"[green]Deleted managed account {org_id}[/green]")


@onboarding_app.command("send-link")
def onboarding_send_link(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organization ID"),
    send_email: bool = typer.Option(False, "--send-email", help="Send link via email"),
) -> None:
    """Regenerate onboarding link and optionally send email."""
    resp = _api_request(
        "post",
        f"{_ONBOARDING}/accounts/{org_id}/send-link",
        json={"send_email": send_email},
    )

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    rprint(f"[green]Onboarding link:[/green] {data.get('onboarding_link', '')}")
    if data.get("email_sent"):
        rprint("[green]Email sent successfully[/green]")


@onboarding_app.command("impersonate")
def onboarding_impersonate(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organization ID"),
) -> None:
    """Get a magic link to impersonate a managed account."""
    resp = _api_request("post", f"{_ONBOARDING}/accounts/{org_id}/impersonate")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    rprint(f"[green]Magic link:[/green] {data.get('magic_link', '')}")


@onboarding_app.command("end-impersonation")
def onboarding_end_impersonation(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organization ID"),
) -> None:
    """End admin impersonation and sign out the managed account user."""
    resp = _api_request("post", f"{_ONBOARDING}/accounts/{org_id}/end-impersonate")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    rprint(f"[green]Impersonation ended for {org_id}[/green]")


@onboarding_app.command("activate")
def onboarding_activate(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organization ID"),
    send_password_reset: bool = typer.Option(
        True,
        "--send-password-reset/--no-send-password-reset",
        help="Send password reset email",
    ),
) -> None:
    """Activate a managed account."""
    resp = _api_request(
        "post",
        f"{_ONBOARDING}/accounts/{org_id}/activate",
        json={"send_password_reset": send_password_reset},
    )

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    rprint(f"[green]Account {org_id} activated[/green]")
    if data.get("status"):
        rprint(f"Status: {data['status']}")


@onboarding_app.command("deactivate")
def onboarding_deactivate(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organization ID"),
) -> None:
    """Deactivate a managed account (revert to pending)."""
    resp = _api_request("post", f"{_ONBOARDING}/accounts/{org_id}/deactivate")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    rprint(f"[green]Account {org_id} deactivated[/green]")
    if data.get("status"):
        rprint(f"Status: {data['status']}")


@onboarding_app.command("update-config")
def onboarding_update_config(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organization ID"),
    show_calendly: bool | None = typer.Option(
        None, "--show-calendly/--no-show-calendly", help="Show Calendly widget"
    ),
    calendly_url: str | None = typer.Option(None, "--calendly-url", help="Calendly URL"),
) -> None:
    """Update onboarding configuration for a managed account."""
    body = _build_body(show_calendly=show_calendly, calendly_url=calendly_url)

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_ONBOARDING}/accounts/{org_id}/config", json=body)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    rprint(f"[green]Updated onboarding config for {org_id}[/green]")


@onboarding_app.command("get-settings")
def onboarding_get_settings(
    ctx: typer.Context,
) -> None:
    """Get global managed onboarding settings."""
    resp = _api_request("get", f"{_ONBOARDING}/settings")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(data)


@onboarding_app.command("update-settings")
def onboarding_update_settings(
    ctx: typer.Context,
    terms_html: str | None = typer.Option(None, "--terms-html", help="Terms HTML content"),
    calendly_url: str | None = typer.Option(None, "--calendly-url", help="Calendly URL"),
    calendly_enabled: bool | None = typer.Option(
        None, "--calendly-enabled/--no-calendly-enabled", help="Enable Calendly globally"
    ),
) -> None:
    """Update global managed onboarding settings."""
    body = _build_body(
        terms_html=terms_html,
        calendly_url=calendly_url,
        calendly_enabled=calendly_enabled,
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("put", f"{_ONBOARDING}/settings", json=body)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    rprint("[green]Updated onboarding settings[/green]")
