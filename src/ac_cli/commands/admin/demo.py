"""Admin demo account management commands."""

from __future__ import annotations

import typer
from rich import print as rprint
from rich.pretty import Pretty

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_json, print_table, styled

demo_app = typer.Typer(help="Demo account management")


@demo_app.command("scrape-website")
def demo_scrape_website(
    ctx: typer.Context,
    url: str = typer.Option(..., help="URL to scrape"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Scrape a website for company data."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_ADMIN}/demo/scrape-website", json={"url": url})

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(Pretty(data))


@demo_app.command("generate-org")
def demo_generate_org(
    ctx: typer.Context,
    industry: str = typer.Option(..., help="Industry"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Generate a random demo organization."""
    set_json_mode(json_output)
    body = {"industry": industry}

    resp = _api_request("post", f"{_ADMIN}/demo/generate-random-org", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(Pretty(data))


@demo_app.command("generate-profile")
def demo_generate_profile(
    ctx: typer.Context,
    role: str = typer.Option(..., help="Job role of the profile"),
    industry: str | None = typer.Option(None, help="Industry"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Generate a random demo profile."""
    set_json_mode(json_output)
    body = _build_body(role=role, industry=industry)

    resp = _api_request("post", f"{_ADMIN}/demo/generate-random-profile", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(Pretty(data))


@demo_app.command("prepare-account")
def demo_prepare_account(
    ctx: typer.Context,
    org_name: str = typer.Option(..., "--org-name", help="Organization name"),
    user_email: str = typer.Option(..., "--user-email", help="Email of the demo user"),
    user_first_name: str = typer.Option(
        ..., "--user-first-name", help="First name of the demo user"
    ),
    user_last_name: str = typer.Option(..., "--user-last-name", help="Last name of the demo user"),
    empty: bool = typer.Option(
        False,
        "--empty",
        "--skip-crm-data",
        help="Create an empty account (org + user only, no CRM companies/people/deals/activities)",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Prepare a demo account."""
    set_json_mode(json_output)
    body = _build_body(
        company_name=org_name,
        user_email=user_email,
        user_first_name=user_first_name,
        user_last_name=user_last_name,
        skip_crm_data=True if empty else None,
    )

    resp = _api_request("post", f"{_ADMIN}/demo/prepare-account", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(Pretty(data))


@demo_app.command("list-accounts")
def demo_list_accounts(
    ctx: typer.Context,
    page: int = typer.Option(1, help="Page number"),
    page_size: int = typer.Option(50, "--page-size", help="Page size"),
    sort: str | None = typer.Option(None, help="Sort field"),
    order: str | None = typer.Option(None, help="Sort order (asc/desc)"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List demo accounts."""
    set_json_mode(json_output)
    params: dict = {"page": page, "page_size": page_size}
    if sort:
        params["sort"] = sort
    if order:
        params["order"] = order

    resp = _api_request("get", f"{_ADMIN}/demo/accounts", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data.get("data", []),
        [
            ("org_id", "Org ID"),
            ("org_name", "Org Name"),
            ("status", "Status"),
            ("created_at", "Created"),
        ],
        title=f"Demo Accounts ({data.get('total', '?')} total)",
    )


@demo_app.command("get-account")
def demo_get_account(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organization ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a demo account by organization ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/demo/accounts/{org_id}")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(Pretty(data))


@demo_app.command("update-account")
def demo_update_account(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organization ID"),
    first_name: str | None = typer.Option(None, "--first-name", help="First name of the demo user"),
    last_name: str | None = typer.Option(None, "--last-name", help="Last name of the demo user"),
    job_title: str | None = typer.Option(None, "--job-title", help="Job title of the demo user"),
    bio: str | None = typer.Option(None, "--bio", help="Bio of the demo user"),
    avatar_url: str | None = typer.Option(None, "--avatar-url", help="Avatar URL of the demo user"),
    website: str | None = typer.Option(None, "--website", help="Website of the demo user"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update the profile of the demo account user."""
    set_json_mode(json_output)
    body = _build_body(
        first_name=first_name,
        last_name=last_name,
        job_title=job_title,
        bio=bio,
        avatar_url=avatar_url,
        website=website,
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_ADMIN}/demo/accounts/{org_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Updated demo account {}[/green]", org_id))


@demo_app.command("delete-account")
def demo_delete_account(
    org_id: str = typer.Argument(..., help="Organization ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a demo account."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete demo account {org_id}?", abort=True)

    _api_request("delete", f"{_ADMIN}/demo/accounts/{org_id}")

    rprint(styled("[green]Deleted demo account {}[/green]", org_id))


@demo_app.command("cleanup")
def demo_cleanup(
    max_age_days: int | None = typer.Option(None, "--max-age-days", help="Max age in days"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Clean up old demo accounts."""
    if not should_skip_confirm(yes):
        typer.confirm("Clean up old demo accounts?", abort=True)

    body = _build_body(days_old=max_age_days)

    resp = _api_request("post", f"{_ADMIN}/demo/cleanup", json=body)

    rprint("[green]Cleanup complete[/green]")
    rprint(Pretty(resp.json()))


@demo_app.command("stats")
def demo_stats(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Show demo account statistics."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/demo/stats")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(Pretty(data))
