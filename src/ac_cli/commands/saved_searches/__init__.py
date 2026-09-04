"""Commands for the agentic saved-search surface."""

from __future__ import annotations

import json
from typing import NoReturn

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    header_safe_key,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.formatting import as_text, console, print_detail, print_json, print_table

app = typer.Typer(help="Manage repeatable agentic saved searches")

_SAVED_SEARCHES = "/api/v1/agentic/saved-searches"
_PAGE_DEFAULT = 50
_PAGE_MIN = 1
_PAGE_MAX = 100

_SUMMARY_FIELDS = [
    ("id", "Saved search ID"),
    ("name", "Name"),
    ("last_run_id", "Last run"),
    ("last_run_at", "Last run at"),
    ("updated_at", "Token"),
]
_DETAIL_FIELDS = [
    ("id", "Saved search ID"),
    ("name", "Name"),
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


def _refuse(detail: str, *, json_output: bool) -> NoReturn:
    """Report one local input error in the requested output shape."""
    if json_output:
        print_json({"error": True, "status_code": None, "detail": detail})
    else:
        rprint("[red]Invalid option:[/red]", as_text(detail))
    raise typer.Exit(code=2)


def _parse_object(raw: str, flag: str, *, json_output: bool) -> dict:
    """Parse one required JSON object flag."""
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        _refuse(f"{flag} is not valid JSON", json_output=json_output)
    if not isinstance(value, dict):
        _refuse(f"{flag} must be a JSON object", json_output=json_output)
    return value


def _checked_limit(limit: int, *, json_output: bool) -> int:
    """Refuse a page size that the API refuses."""
    if _PAGE_MIN <= limit <= _PAGE_MAX:
        return limit
    _refuse(
        f"--limit is not between {_PAGE_MIN} and {_PAGE_MAX}: {limit}",
        json_output=json_output,
    )


def _checked_contract_version(version: int, *, json_output: bool) -> int:
    """Refuse a version that the stable capability contract refuses."""
    if version >= 1:
        return version
    _refuse("--contract-version must be positive", json_output=json_output)


def _checked_key(key: str, *, json_output: bool) -> str:
    """Refuse a key that cannot travel in the request header."""
    if header_safe_key(key):
        return key
    _refuse(
        "--idempotency-key must contain 1–200 header-safe ASCII characters",
        json_output=json_output,
    )


def _page_params(limit: int, cursor: str | None, *, json_output: bool) -> dict[str, object]:
    """Build one page query and preserve an explicit empty cursor."""
    params: dict[str, object] = {"limit": _checked_limit(limit, json_output=json_output)}
    if cursor is not None:
        params["cursor"] = cursor
    return params


def _print_next_page(next_cursor: str | None, limit: int) -> None:
    """Print the options that continue the same page walk."""
    if not next_cursor:
        return
    parts: list[object] = ["[dim]Next page:[/dim]"]
    if limit != _PAGE_DEFAULT:
        parts += ["--limit", as_text(limit)]
    parts += ["--cursor", as_text(next_cursor)]
    console.print(*parts, soft_wrap=True)


def _print_saved_search(data: dict) -> None:
    """Print one saved search and its complete brief."""
    print_detail(data, _DETAIL_FIELDS)
    rprint("[bold]Brief:[/bold]", as_text(json.dumps(data["brief"], sort_keys=True)))


@app.command("create")
def saved_searches_create(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", help="What to call the saved search"),
    brief: str = typer.Option(
        ...,
        "--brief",
        help="Brief JSON with persona lists: titles, departments, seniority, country_codes",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create one repeatable Signals Search brief."""
    set_json_mode(json_output)
    body = {
        "name": name,
        "brief": _parse_object(brief, "--brief", json_output=json_output),
    }
    data = _api_request("post", _SAVED_SEARCHES, json=body).json()
    if json_output:
        print_json(data)
        return
    _print_saved_search(data)


@app.command("list")
def saved_searches_list(
    ctx: typer.Context,
    cursor: str | None = typer.Option(None, "--cursor", help="Page to continue"),
    limit: int = typer.Option(_PAGE_DEFAULT, "--limit", help="Page size, 1 to 100"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List saved-search summaries, newest first."""
    set_json_mode(json_output)
    data = _api_request(
        "get",
        _SAVED_SEARCHES,
        params=_page_params(limit, cursor, json_output=json_output),
    ).json()
    if json_output:
        print_json(data)
        return
    print_table(data.get("items", []), _SUMMARY_FIELDS, title="Saved searches")
    _print_next_page(data.get("next_cursor"), limit)


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
        help="Full replacement brief JSON; preserve other fields and correct persona lists",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Replace the name, brief, or both under one write token."""
    set_json_mode(json_output)
    if name is None and brief is None:
        _refuse("provide --name or --brief", json_output=json_output)
    body: dict = {"expected_updated_at": expected_updated_at}
    if name is not None:
        body["name"] = name
    if brief is not None:
        body["brief"] = _parse_object(brief, "--brief", json_output=json_output)
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
    contract_version: int = typer.Option(
        ..., "--contract-version", help="Published Signals Search contract version"
    ),
    idempotency_key: str = typer.Option(
        ...,
        "--idempotency-key",
        help="Delivery identity. Reuse it only for the same saved-search request.",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Start one Run with the stored brief and current baseline."""
    set_json_mode(json_output)
    version = _checked_contract_version(contract_version, json_output=json_output)
    key = _checked_key(idempotency_key, json_output=json_output)
    data = _api_request(
        "post",
        f"{_SAVED_SEARCHES}/{search_id}/runs",
        json={"contract_version": version},
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
    """Read material changes from the latest published successful Run."""
    set_json_mode(json_output)
    data = _api_request(
        "get",
        f"{_SAVED_SEARCHES}/{search_id}/diff",
        params=_page_params(limit, cursor, json_output=json_output),
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
