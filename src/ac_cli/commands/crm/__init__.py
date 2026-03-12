"""CRM commands: search, companies, people, deals, activities, dashboard, lists."""

import httpx
import typer
from rich import print as rprint

from ac_cli.client import get_api_client
from ac_cli.formatting import print_json, print_table

app = typer.Typer(help="CRM commands")

# -- Shared helpers -----------------------------------------------------------

_CRM = "/api/v1/crm"


@app.callback()
def crm_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output


def _handle_error(exc: httpx.HTTPStatusError) -> None:
    """Print API error detail and exit."""
    try:
        detail = exc.response.json().get("detail", exc.response.text)
    except Exception:
        detail = exc.response.text
    rprint(f"[red]Error {exc.response.status_code}:[/red] {detail}")
    raise typer.Exit(code=1)


def _api_request(method: str, path: str, **kwargs: object) -> httpx.Response:
    """Make an authenticated API request with standard error handling."""
    with get_api_client() as client:
        try:
            resp = getattr(client, method)(path, **kwargs)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)
        except httpx.HTTPError as exc:
            rprint(f"[red]Connection error:[/red] {exc}")
            raise typer.Exit(code=1)
    return resp


def _build_body(**fields: object) -> dict:
    """Build API request body from non-None fields."""
    body: dict = {}
    for key, value in fields.items():
        if value is not None:
            if key == "tags" and isinstance(value, str):
                body[key] = [t.strip() for t in value.split(",")]
            else:
                body[key] = value
    return body


# =============================================================================
# SEARCH
# =============================================================================


@app.command()
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query"),
) -> None:
    """Search across companies, contacts, and deals."""
    resp = _api_request("get", f"{_CRM}/search", params={"q": query})

    data = resp.json()
    if ctx.obj["json"]:
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
) -> None:
    """Show CRM dashboard summary."""
    resp = _api_request("get", f"{_CRM}/dashboard", params={"period_days": period})

    data = resp.json()
    if ctx.obj["json"]:
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

    rprint(f"\n[bold]Active Pipeline[/bold]")
    rprint(f"  Active deals: {active.get('active_deals_count', 0)}")
    rprint(f"  Total value: ${active.get('total_value', 0):,.2f}")
    rprint(f"  Adjusted value: ${active.get('adjusted_value', 0):,.2f}")

    rprint(f"\n[bold]Leads[/bold]")
    rprint(f"  This period: {leads.get('current_period', 0)}")
    rprint(f"  Previous: {leads.get('previous_period', 0)}")
    rprint(f"  Change: {leads.get('change', 0):+d}")
    rprint(f"  Total: {leads.get('total', 0)}")

    rprint(f"\n[bold]Messages Sent[/bold]")
    rprint(f"  This period: {messages.get('current_period', 0)}")
    rprint(f"  Previous: {messages.get('previous_period', 0)}")
    rprint(f"  Change: {messages.get('change', 0):+d}")


# -- Register sub-command groups from submodules ------------------------------

from ac_cli.commands.crm.companies import companies_app  # noqa: E402
from ac_cli.commands.crm.people import people_app  # noqa: E402
from ac_cli.commands.crm.deals import deals_app  # noqa: E402
from ac_cli.commands.crm.activities import activities_app  # noqa: E402
from ac_cli.commands.crm.lists import lists_app  # noqa: E402
from ac_cli.commands.crm.communications import communications_app  # noqa: E402

app.add_typer(companies_app, name="companies")
app.add_typer(people_app, name="people")
app.add_typer(deals_app, name="deals")
app.add_typer(activities_app, name="activities")
app.add_typer(lists_app, name="lists")
app.add_typer(communications_app, name="comms")
