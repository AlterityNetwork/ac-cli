"""Network commands: referrals, news, slack invites."""

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
from ac_cli.formatting import print_detail, print_json, print_table, styled

app = typer.Typer(help="Network features")

_NET = "/api/v1/network"


@app.callback()
def network_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


# -- Referrals -----------------------------------------------------------------

referrals_app = typer.Typer(help="Referral operations")


@referrals_app.command("list")
def referrals_list(
    ctx: typer.Context,
    status: str | None = typer.Option(None, help="Filter by status"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List referrals."""
    set_json_mode(json_output)
    params: dict = {}
    if status:
        params["status"] = status

    resp = _api_request("get", f"{_NET}/referrals", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("id", "ID"),
            ("company_name", "Company"),
            ("status", "Status"),
            ("created_at", "Created"),
        ],
        title=f"Referrals ({len(items)})",
    )


@referrals_app.command("get")
def referrals_get(
    ctx: typer.Context,
    referral_id: str = typer.Argument(..., help="Referral ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a referral by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_NET}/referrals/{referral_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("company_name", "Company"),
            ("status", "Status"),
            ("description", "Description"),
            ("created_at", "Created"),
        ],
    )


@referrals_app.command("create")
def referrals_create(
    ctx: typer.Context,
    company_name: str = typer.Option(..., "--company-name", help="Referred company name"),
    description: str | None = typer.Option(None, "--description", help="Referral description"),
    contact_name: str | None = typer.Option(None, "--contact-name", help="Contact person name"),
    contact_email: str | None = typer.Option(None, "--contact-email", help="Contact email"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a referral."""
    set_json_mode(json_output)
    body = _build_body(
        company_name=company_name,
        description=description,
        contact_name=contact_name,
        contact_email=contact_email,
    )

    resp = _api_request("post", f"{_NET}/referrals", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Created referral:[/green] {}", data.get("id", data)))


@referrals_app.command("update")
def referrals_update(
    ctx: typer.Context,
    referral_id: str = typer.Argument(..., help="Referral ID"),
    status: str | None = typer.Option(None, "--status", help="Referral status"),
    description: str | None = typer.Option(None, "--description", help="Description"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a referral."""
    set_json_mode(json_output)
    body = _build_body(status=status, description=description)
    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_NET}/referrals/{referral_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Updated referral {}[/green]", referral_id))


@referrals_app.command("delete")
def referrals_delete(
    referral_id: str = typer.Argument(..., help="Referral ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a referral."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete referral {referral_id}?", abort=True)

    _api_request("delete", f"{_NET}/referrals/{referral_id}")

    rprint(styled("[green]Deleted referral {}[/green]", referral_id))


@referrals_app.command("view")
def referrals_view(
    ctx: typer.Context,
    referral_id: str = typer.Argument(..., help="Referral ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Increment view count for a referral."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_NET}/referrals/{referral_id}/view")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Viewed referral {}[/green]", referral_id))


@referrals_app.command("claim")
def referrals_claim(
    ctx: typer.Context,
    referral_id: str = typer.Argument(..., help="Referral ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Claim a referral."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_NET}/referrals/{referral_id}/claim")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Claimed referral {}[/green]", referral_id))


# -- News ----------------------------------------------------------------------

news_app = typer.Typer(help="Network news")


@news_app.command("list")
def news_list(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """List news items."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_NET}/news")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [("id", "ID"), ("title", "Title"), ("created_at", "Created")],
        title=f"News ({len(items)})",
    )


@news_app.command("create")
def news_create(
    ctx: typer.Context,
    title: str = typer.Option(..., "--title", help="News title"),
    content: str = typer.Option(..., "--content", help="News content"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a news item."""
    set_json_mode(json_output)
    body = _build_body(title=title, content=content)

    resp = _api_request("post", f"{_NET}/news", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Created news:[/green] {}", data.get("id", data)))


@news_app.command("update")
def news_update(
    ctx: typer.Context,
    news_id: str = typer.Argument(..., help="News ID"),
    title: str | None = typer.Option(None, "--title", help="Title"),
    content: str | None = typer.Option(None, "--content", help="Content"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a news item."""
    set_json_mode(json_output)
    body = _build_body(title=title, content=content)
    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_NET}/news/{news_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Updated news {}[/green]", news_id))


@news_app.command("delete")
def news_delete(
    news_id: str = typer.Argument(..., help="News ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a news item."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete news {news_id}?", abort=True)

    _api_request("delete", f"{_NET}/news/{news_id}")

    rprint(styled("[green]Deleted news {}[/green]", news_id))


# -- Slack Invites -------------------------------------------------------------

slack_app = typer.Typer(help="Slack invite operations")


@slack_app.command("status")
def slack_status(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Check Slack invite status."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_NET}/slack-invites/status")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, [("status", "Status"), ("requested_at", "Requested At")])


@slack_app.command("request")
def slack_request(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Request a Slack invite."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_NET}/slack-invites")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint("[green]Slack invite requested[/green]")


# Register sub-groups
app.add_typer(referrals_app, name="referrals")
app.add_typer(news_app, name="news")
app.add_typer(slack_app, name="slack-invites")
