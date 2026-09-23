"""Commands for the agentic saved-search surface."""

from __future__ import annotations

import json

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    checked_header_key,
    refuse_local,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.formatting import as_text, console, print_detail, print_json, print_table

app = typer.Typer(help="Manage repeatable agentic saved searches")

_SAVED_SEARCHES = "/api/v1/agentic/saved-searches"
#: The three search capabilities that hold a saved brief. An enrich capability
#: takes the rows it works on, so the API refuses a saved brief for one.
_CAPABILITIES = ("signals.search", "people.search", "company.search")
_CAPABILITY_HELP = f"Which product saves the brief: {', '.join(_CAPABILITIES)}"
_PAGE_DEFAULT = 50
_PAGE_MIN = 1
_PAGE_MAX = 100

# The caller names one capability to list, so a column repeating it on every
# row carries nothing and costs the width the other columns need.
_SUMMARY_FIELDS = [
    ("id", "Saved search ID"),
    ("name", "Name"),
    ("schedule", "Schedule"),
    ("last_run_id", "Last run"),
    ("last_run_at", "Last run at"),
    ("updated_at", "Token"),
]
_DETAIL_FIELDS = [
    ("id", "Saved search ID"),
    ("capability_id", "Capability"),
    ("name", "Name"),
    ("description", "Description"),
    ("last_run_id", "Last run"),
    ("last_run_at", "Last run at"),
    ("created_at", "Created"),
    ("updated_at", "Token"),
]
_DIFF_FIELDS = [
    ("prospect_id", "Prospect ID"),
    ("company_name", "Company"),
    ("company_domain", "Domain"),
    ("change_kinds", "Changes"),
    ("opportunity_score", "Score"),
    ("first_seen_at", "First seen"),
    ("last_seen_at", "Last seen"),
]


def _parse_object(raw: str, flag: str) -> dict:
    """Parse one required JSON object flag."""
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        refuse_local(f"{flag} is not valid JSON")
    if not isinstance(value, dict):
        refuse_local(f"{flag} must be a JSON object")
    return value


def _checked_limit(limit: int) -> int:
    """Refuse a page size that the API refuses."""
    if _PAGE_MIN <= limit <= _PAGE_MAX:
        return limit
    refuse_local(f"--limit is not between {_PAGE_MIN} and {_PAGE_MAX}", limit)


def _checked_capability(capability: str) -> str:
    """Refuse a capability that holds no saved search."""
    if capability in _CAPABILITIES:
        return capability
    refuse_local(f"--capability must be one of: {', '.join(_CAPABILITIES)}", capability)


def _page_params(limit: int, cursor: str | None) -> dict[str, object]:
    """Build one page query and preserve an explicit empty cursor."""
    params: dict[str, object] = {"limit": _checked_limit(limit)}
    if cursor is not None:
        params["cursor"] = cursor
    return params


def _print_next_page(next_cursor: str | None, limit: int, capability: str | None = None) -> None:
    """Print the options that continue the same page walk."""
    if not next_cursor:
        return
    parts: list[object] = ["[dim]Next page:[/dim]"]
    if capability is not None:
        parts += ["--capability", as_text(capability)]
    if limit != _PAGE_DEFAULT:
        parts += ["--limit", as_text(limit)]
    parts += ["--cursor", as_text(next_cursor)]
    console.print(*parts, soft_wrap=True)


def _schedule_text(schedule: dict | None) -> str | None:
    """Render one schedule as its cron and zone, or None when there is none."""
    if not schedule:
        return None
    return f"{schedule['cron']} {schedule['timezone']}"


def _print_schedule(data: dict) -> None:
    """Print the schedule one read or write answered."""
    text = _schedule_text(data.get("schedule"))
    if text is None:
        rprint("No schedule. The saved search runs only when someone starts it.")
        return
    rprint("[bold]Schedule:[/bold]", as_text(text))


def _print_saved_search(data: dict) -> None:
    """Print one saved search and its complete brief."""
    print_detail(data, _DETAIL_FIELDS)
    rprint("[bold]Brief:[/bold]", as_text(json.dumps(data["brief"], sort_keys=True)))


@app.command("create")
def saved_searches_create(
    ctx: typer.Context,
    capability: str = typer.Option(..., "--capability", help=_CAPABILITY_HELP),
    name: str = typer.Option(..., "--name", help="What to call the saved search"),
    brief: str = typer.Option(
        ...,
        "--brief",
        help="Brief JSON in the input shape the capability publishes",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create one repeatable search brief for one product."""
    set_json_mode(json_output)
    body = {
        "capability_id": _checked_capability(capability),
        "name": name,
        "brief": _parse_object(brief, "--brief"),
    }
    data = _api_request("post", _SAVED_SEARCHES, json=body).json()
    if json_output:
        print_json(data)
        return
    _print_saved_search(data)


@app.command("list")
def saved_searches_list(
    ctx: typer.Context,
    capability: str = typer.Option(..., "--capability", help=_CAPABILITY_HELP),
    cursor: str | None = typer.Option(None, "--cursor", help="Page to continue"),
    limit: int = typer.Option(_PAGE_DEFAULT, "--limit", help="Page size, 1 to 100"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List one product's saved-search summaries, newest first."""
    set_json_mode(json_output)
    checked = _checked_capability(capability)
    data = _api_request(
        "get",
        _SAVED_SEARCHES,
        params={"capability": checked, **_page_params(limit, cursor)},
    ).json()
    if json_output:
        print_json(data)
        return
    rows = [
        {**item, "schedule": _schedule_text(item.get("schedule"))} for item in data.get("items", [])
    ]
    print_table(rows, _SUMMARY_FIELDS, title="Saved searches")
    _print_next_page(data.get("next_cursor"), limit, checked)


@app.command("get")
def saved_searches_get(
    ctx: typer.Context,
    search_id: str = typer.Argument(..., help="Saved search ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Read one saved search and its complete brief."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_SAVED_SEARCHES}/{search_id}").json()
    if json_output:
        print_json(data)
        return
    _print_saved_search(data)


@app.command("patch")
def saved_searches_patch(
    ctx: typer.Context,
    search_id: str = typer.Argument(..., help="Saved search ID"),
    expected_updated_at: str = typer.Option(
        ...,
        "--expected-updated-at",
        help="The opaque token from the last read",
    ),
    name: str | None = typer.Option(None, "--name", help="Replacement name"),
    brief: str | None = typer.Option(
        None,
        "--brief",
        help="Full replacement brief JSON",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Replace the name, brief, or both under one write token."""
    set_json_mode(json_output)
    if name is None and brief is None:
        refuse_local("provide --name or --brief")
    body: dict = {"expected_updated_at": expected_updated_at}
    if name is not None:
        body["name"] = name
    if brief is not None:
        body["brief"] = _parse_object(brief, "--brief")
    data = _api_request("patch", f"{_SAVED_SEARCHES}/{search_id}", json=body).json()
    if json_output:
        print_json(data)
        return
    _print_saved_search(data)


@app.command("delete")
def saved_searches_delete(
    ctx: typer.Context,
    search_id: str = typer.Argument(..., help="Saved search ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete one saved search. A Run already started keeps its input."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete saved search {search_id}?", abort=True)
    _api_request("delete", f"{_SAVED_SEARCHES}/{search_id}")
    if json_output:
        print_json({"id": search_id, "deleted": True})
        return
    rprint("[green]Saved search deleted:[/green]", as_text(search_id))


@app.command("start")
def saved_searches_start(
    ctx: typer.Context,
    search_id: str = typer.Argument(..., help="Saved search ID"),
    idempotency_key: str = typer.Option(
        ...,
        "--idempotency-key",
        help="Delivery identity. Reuse it only for the same saved-search request.",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Start one Run with the stored brief and active contract."""
    set_json_mode(json_output)
    key = checked_header_key(idempotency_key)
    data = _api_request(
        "post",
        f"{_SAVED_SEARCHES}/{search_id}/runs",
        json={},
        headers={"Idempotency-Key": key},
    ).json()
    if json_output:
        print_json(data)
        return
    if data.get("outcome") == "duplicate":
        rprint(
            "[yellow]Duplicate:[/yellow] this key already started",
            as_text(f"{data['id']} (status: {data['status']})"),
        )
        return
    rprint(
        "[green]Saved-search run started:[/green]",
        as_text(f"{data['id']} ({data['definition_name']}, status: {data['status']})"),
    )


@app.command("diff")
def saved_searches_diff(
    ctx: typer.Context,
    search_id: str = typer.Argument(..., help="Saved search ID"),
    cursor: str | None = typer.Option(None, "--cursor", help="Page to continue"),
    limit: int = typer.Option(_PAGE_DEFAULT, "--limit", help="Page size, 1 to 100"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Read material changes from the latest published successful Run.

    The diff reads the Smart Feed, which only signals.search publishes. A
    saved search of another product answers 409.
    """
    set_json_mode(json_output)
    data = _api_request(
        "get",
        f"{_SAVED_SEARCHES}/{search_id}/diff",
        params=_page_params(limit, cursor),
    ).json()
    if json_output:
        print_json(data)
        return
    run_id = data.get("run_id")
    if run_id is None:
        rprint("[yellow]No published run:[/yellow] this saved search has no diff")
        return
    rprint("[dim]Run:[/dim]", as_text(run_id))
    rows = []
    for item in data.get("items", []):
        prospect = item["prospect"]
        rows.append(
            {
                "prospect_id": prospect["id"],
                "company_name": prospect.get("company_name"),
                "company_domain": prospect.get("company_domain"),
                "change_kinds": ", ".join(item["change_kinds"]),
                "opportunity_score": prospect.get("opportunity_score"),
                "first_seen_at": item["first_seen_at"],
                "last_seen_at": item["last_seen_at"],
            }
        )
    print_table(rows, _DIFF_FIELDS, title="Latest saved-search diff")
    _print_next_page(data.get("next_cursor"), limit)


schedule_app = typer.Typer(help="Run a Signals saved search on a schedule")
app.add_typer(schedule_app, name="schedule")


@schedule_app.command("get")
def saved_search_schedule_get(
    ctx: typer.Context,
    search_id: str = typer.Argument(..., help="Saved search ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show the schedule that starts one saved search."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_SAVED_SEARCHES}/{search_id}/schedule").json()
    if json_output:
        print_json(data)
        return
    _print_schedule(data)


@schedule_app.command("set")
def saved_search_schedule_set(
    ctx: typer.Context,
    search_id: str = typer.Argument(..., help="Saved search ID"),
    cron: str = typer.Option(..., "--cron", help="Five-field cron, such as '0 9 * * 1'"),
    timezone: str = typer.Option("UTC", "--timezone", help="IANA zone the cron is read in"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Start one Signals saved search on a schedule. You become its author."""
    set_json_mode(json_output)
    data = _api_request(
        "put",
        f"{_SAVED_SEARCHES}/{search_id}/schedule",
        json={"cron": cron, "timezone": timezone},
    ).json()
    if json_output:
        print_json(data)
        return
    _print_schedule(data)


@schedule_app.command("clear")
def saved_search_schedule_clear(
    ctx: typer.Context,
    search_id: str = typer.Argument(..., help="Saved search ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Stop the schedule of one saved search. A Run already started continues."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Stop the schedule of saved search {search_id}?", abort=True)
    _api_request("delete", f"{_SAVED_SEARCHES}/{search_id}/schedule")
    if json_output:
        print_json({"id": search_id, "schedule": None})
        return
    rprint("[green]Schedule stopped:[/green]", as_text(search_id))
