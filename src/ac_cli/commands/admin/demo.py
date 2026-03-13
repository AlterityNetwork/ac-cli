"""Admin demo account management commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import _api_request, _build_body
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_detail, print_json, print_table

demo_app = typer.Typer(help="Demo account management")


@demo_app.command("scrape-website")
def demo_scrape_website(
    ctx: typer.Context,
    url: str = typer.Option(..., help="URL to scrape"),
) -> None:
    """Scrape a website for company data."""
    resp = _api_request("post", f"{_ADMIN}/demo/scrape-website", json={"url": url})

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(data)


@demo_app.command("generate-org")
def demo_generate_org(
    ctx: typer.Context,
    industry: str | None = typer.Option(None, help="Industry"),
    size: str | None = typer.Option(None, help="Organization size"),
) -> None:
    """Generate a random demo organization."""
    body = _build_body(industry=industry, size=size)

    resp = _api_request("post", f"{_ADMIN}/demo/generate-random-org", json=body)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(data)


@demo_app.command("generate-profile")
def demo_generate_profile(
    ctx: typer.Context,
    industry: str | None = typer.Option(None, help="Industry"),
) -> None:
    """Generate a random demo profile."""
    body = _build_body(industry=industry)

    resp = _api_request("post", f"{_ADMIN}/demo/generate-random-profile", json=body)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(data)


@demo_app.command("prepare-account")
def demo_prepare_account(
    ctx: typer.Context,
    org_name: str = typer.Option(..., "--org-name", help="Organization name"),
    template: str | None = typer.Option(None, help="Account template"),
) -> None:
    """Prepare a demo account."""
    body = _build_body(org_name=org_name, template=template)

    resp = _api_request("post", f"{_ADMIN}/demo/prepare-account", json=body)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(data)


@demo_app.command("list-accounts")
def demo_list_accounts(
    ctx: typer.Context,
    page: int = typer.Option(1, help="Page number"),
    page_size: int = typer.Option(50, "--page-size", help="Page size"),
    sort: str | None = typer.Option(None, help="Sort field"),
    order: str | None = typer.Option(None, help="Sort order (asc/desc)"),
) -> None:
    """List demo accounts."""
    params: dict = {"page": page, "page_size": page_size}
    if sort:
        params["sort"] = sort
    if order:
        params["order"] = order

    resp = _api_request("get", f"{_ADMIN}/demo/accounts", params=params)

    data = resp.json()
    if ctx.obj["json"]:
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
) -> None:
    """Get a demo account by organization ID."""
    resp = _api_request("get", f"{_ADMIN}/demo/accounts/{org_id}")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(data)


@demo_app.command("update-account")
def demo_update_account(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organization ID"),
    status: str | None = typer.Option(None, help="Account status"),
    notes: str | None = typer.Option(None, help="Account notes"),
) -> None:
    """Update a demo account."""
    body = _build_body(status=status, notes=notes)

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_ADMIN}/demo/accounts/{org_id}", json=body)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Updated demo account {org_id}[/green]")


@demo_app.command("delete-account")
def demo_delete_account(
    org_id: str = typer.Argument(..., help="Organization ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a demo account."""
    if not yes:
        typer.confirm(f"Delete demo account {org_id}?", abort=True)

    _api_request("delete", f"{_ADMIN}/demo/accounts/{org_id}")

    rprint(f"[green]Deleted demo account {org_id}[/green]")


@demo_app.command("cleanup")
def demo_cleanup(
    max_age_days: int | None = typer.Option(None, "--max-age-days", help="Max age in days"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Clean up old demo accounts."""
    if not yes:
        typer.confirm("Clean up old demo accounts?", abort=True)

    body = _build_body(max_age_days=max_age_days)

    resp = _api_request("post", f"{_ADMIN}/demo/cleanup", json=body)

    rprint(f"[green]Cleanup complete[/green]")
    rprint(resp.json())


@demo_app.command("stats")
def demo_stats(
    ctx: typer.Context,
) -> None:
    """Show demo account statistics."""
    resp = _api_request("get", f"{_ADMIN}/demo/stats")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(data)
