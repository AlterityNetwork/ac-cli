"""CRM commands: search, companies, people, deals, activities, dashboard, lists."""

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (  # noqa: F401
    JSON_OPTION,
    _api_request,
    _build_body,
    _handle_error,
    set_json_mode,
)
from ac_cli.formatting import print_json, print_table

app = typer.Typer(help="CRM commands")

# -- Shared helpers -----------------------------------------------------------

_CRM = "/api/v1/crm"


@app.callback()
def crm_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


# =============================================================================
# SEARCH
# =============================================================================


@app.command()
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Search across companies, contacts, and deals."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/search", params={"q": query})

    data = resp.json()
    if json_output:
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
# DASHBOARD
# =============================================================================


@app.command("dashboard")
def dashboard(
    ctx: typer.Context,
    period: int = typer.Option(30, "--period", help="Period in days"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show CRM dashboard summary."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/dashboard", params={"period_days": period})

    data = resp.json()
    if json_output:
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

    rprint("\n[bold]Active Pipeline[/bold]")
    rprint(f"  Active deals: {active.get('active_deals_count', 0)}")
    rprint(f"  Total value: ${active.get('total_value', 0):,.2f}")
    rprint(f"  Adjusted value: ${active.get('adjusted_value', 0):,.2f}")

    rprint("\n[bold]Leads[/bold]")
    rprint(f"  This period: {leads.get('current_period', 0)}")
    rprint(f"  Previous: {leads.get('previous_period', 0)}")
    rprint(f"  Change: {leads.get('change', 0):+d}")
    rprint(f"  Total: {leads.get('total', 0)}")

    rprint("\n[bold]Messages Sent[/bold]")
    rprint(f"  This period: {messages.get('current_period', 0)}")
    rprint(f"  Previous: {messages.get('previous_period', 0)}")
    rprint(f"  Change: {messages.get('change', 0):+d}")


# =============================================================================
# ENGAGEMENT DASHBOARD
# =============================================================================


@app.command("engagement-dashboard")
def engagement_dashboard(
    ctx: typer.Context,
    period: int = typer.Option(30, "--period", help="Period in days (1-365)"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show email engagement dashboard."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/engagement-dashboard", params={"period_days": period})

    data = resp.json()
    if json_output:
        print_json(data)
        return

    rprint(
        f"\n[bold]Email Engagement Dashboard[/bold] (last {data.get('period_days', period)} days)\n"
    )

    emails = data.get("emails_sent", {})
    rprint("[bold]Emails Sent[/bold]")
    rprint(f"  Current period: {emails.get('current_period', 0)}")
    rprint(f"  Previous period: {emails.get('previous_period', 0)}")
    rprint(f"  Change: {emails.get('change', 0):+d}")

    rprint("\n[bold]Engagement Rates[/bold]")
    rprint(f"  Open rate: {data.get('open_rate', 0):.1f}%")
    rprint(f"  Click rate: {data.get('click_rate', 0):.1f}%")
    rprint(f"  Reply rate: {data.get('reply_rate', 0):.1f}%")
    rprint(f"  Bounce rate: {data.get('bounce_rate', 0):.1f}%")

    health = data.get("email_health", {})
    if health:
        rprint("\n[bold]Email Health[/bold]")
        rprint(f"  Score: {health.get('score', 'N/A')}")
        rprint(f"  Status: {health.get('status', 'N/A')}")

    top_links = data.get("top_clicked_links", [])
    if top_links:
        from ac_cli.formatting import print_table

        print_table(
            top_links,
            [
                ("url", "URL"),
                ("clicks", "Clicks"),
            ],
            title="Top Clicked Links",
        )


# -- Register sub-command groups from submodules ------------------------------

from ac_cli.commands.crm.activities import activities_app  # noqa: E402
from ac_cli.commands.crm.communications import communications_app  # noqa: E402
from ac_cli.commands.crm.companies import companies_app  # noqa: E402
from ac_cli.commands.crm.deals import deals_app  # noqa: E402
from ac_cli.commands.crm.imports import imports_app  # noqa: E402
from ac_cli.commands.crm.lists import lists_app  # noqa: E402
from ac_cli.commands.crm.people import people_app  # noqa: E402
from ac_cli.commands.crm.signals import signals_app  # noqa: E402

app.add_typer(companies_app, name="companies")
app.add_typer(people_app, name="people")
app.add_typer(deals_app, name="deals")
app.add_typer(activities_app, name="activities")
app.add_typer(lists_app, name="lists")
app.add_typer(communications_app, name="comms")
app.add_typer(imports_app, name="import")
app.add_typer(signals_app, name="signals")
