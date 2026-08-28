"""Commands for the agentic prospect review surface."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.formatting import as_text, console, print_detail, print_json, print_table

app = typer.Typer(help="Review and curate agentic prospects")

_PROSPECTS = "/api/v1/agentic/prospects"
_PAGE_DEFAULT = 50
_PAGE_MIN = 1
_PAGE_MAX = 100

_SUMMARY_FIELDS = [
    ("id", "Prospect ID"),
    ("company_name", "Company"),
    ("company_domain", "Domain"),
    ("review_state", "State"),
    ("opportunity_score", "Score"),
    ("people_state", "People"),
    ("created_at", "Created"),
]
_DETAIL_FIELDS = [
    ("id", "Prospect ID"),
    ("company_name", "Company"),
    ("company_domain", "Domain"),
    ("review_state", "State"),
    ("opportunity_score", "Score"),
    ("opportunity_reason", "Score reason"),
    ("recommended_action", "Recommended action"),
    ("people_state", "People"),
    ("people_state_reason", "People reason"),
    ("crm_company_id", "CRM company ID"),
    ("first_seen_at", "First seen"),
    ("last_seen_at", "Last seen"),
    ("created_at", "Created"),
    ("updated_at", "Updated"),
]
_COMPANY_FIELDS = [
    ("id", "Company ID"),
    ("linkedin_url", "LinkedIn"),
    ("website", "Website"),
    ("industry", "Industry"),
    ("sub_industry", "Sub-industry"),
    ("business_model", "Business model"),
    ("location", "Location"),
    ("employee_count_exact", "Employees"),
    ("employee_count_band", "Employee band"),
    ("annual_revenue", "Annual revenue"),
    ("revenue_band", "Revenue band"),
    ("revenue_currency", "Revenue currency"),
    ("revenue_year", "Revenue year"),
    ("funding_round", "Funding round"),
    ("funding_amount", "Funding amount"),
    ("last_enriched_at", "Last enriched"),
]
_PERSON_FIELDS = [
    ("person_id", "Person ID"),
    ("full_name", "Name"),
    ("current_title", "Title"),
    ("current_company_text", "Company"),
    ("persona_fit_score", "Fit"),
    ("contact_state", "Contact"),
    ("email", "Email"),
]
_SIGNAL_FIELDS = [
    ("signal_type", "Type"),
    ("description", "Description"),
    ("signal_score", "Score"),
    ("observed_at", "Observed"),
    ("provider", "Provider"),
]


def _checked_limit(limit: int, *, json_output: bool) -> int:
    """Refuses a page size that the API refuses."""
    if _PAGE_MIN <= limit <= _PAGE_MAX:
        return limit
    detail = f"--limit is not between {_PAGE_MIN} and {_PAGE_MAX}: {limit}"
    if json_output:
        print_json({"error": True, "status_code": None, "detail": detail})
    else:
        rprint("[red]Invalid page size:[/red]", as_text(limit))
    raise typer.Exit(code=2)


def _page_params(limit: int, cursor: str | None, *, json_output: bool) -> dict[str, object]:
    """Builds the common page query."""
    params: dict[str, object] = {"limit": _checked_limit(limit, json_output=json_output)}
    if cursor is not None:
        params["cursor"] = cursor
    return params


def _print_next_page(
    next_cursor: str | None,
    limit: int,
    *,
    review_state: str | None = None,
) -> None:
    """Prints the options that continue the same page walk."""
    if not next_cursor:
        return
    parts: list[object] = ["[dim]Next page:[/dim]"]
    if review_state is not None:
        parts += ["--review-state", as_text(review_state)]
    if limit != _PAGE_DEFAULT:
        parts += ["--limit", as_text(limit)]
    parts += ["--cursor", as_text(next_cursor)]
    console.print(*parts, soft_wrap=True)


def _print_prospect(data: dict) -> None:
    """Prints one prospect and its bounded company facts."""
    print_detail(data, _DETAIL_FIELDS)
    rprint("[bold]Company[/bold]")
    print_detail(data["company"], _COMPANY_FIELDS)


@app.command("list")
def prospects_list(
    ctx: typer.Context,
    review_state: str = typer.Option("new", "--review-state", help="Review state"),
    cursor: str | None = typer.Option(None, "--cursor", help="Page to continue"),
    limit: int = typer.Option(_PAGE_DEFAULT, "--limit", help="Page size, 1 to 100"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List prospects in one review state, newest first."""
    set_json_mode(json_output)
    params = _page_params(limit, cursor, json_output=json_output)
    params["review_state"] = review_state
    data = _api_request("get", _PROSPECTS, params=params).json()
    if json_output:
        print_json(data)
        return
    print_table(data.get("items", []), _SUMMARY_FIELDS, title="Prospects")
    _print_next_page(data.get("next_cursor"), limit, review_state=review_state)


@app.command("get")
def prospects_get(
    ctx: typer.Context,
    prospect_id: str = typer.Argument(..., help="Prospect ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Read one prospect and its bounded company facts."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_PROSPECTS}/{prospect_id}").json()
    if json_output:
        print_json(data)
        return
    _print_prospect(data)


@app.command("people")
def prospects_people(
    ctx: typer.Context,
    prospect_id: str = typer.Argument(..., help="Prospect ID"),
    cursor: str | None = typer.Option(None, "--cursor", help="Page to continue"),
    limit: int = typer.Option(_PAGE_DEFAULT, "--limit", help="Page size, 1 to 100"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the people attached to one prospect."""
    set_json_mode(json_output)
    data = _api_request(
        "get",
        f"{_PROSPECTS}/{prospect_id}/people",
        params=_page_params(limit, cursor, json_output=json_output),
    ).json()
    if json_output:
        print_json(data)
        return
    rows = []
    for item in data.get("items", []):
        person = item["person"]
        rows.append(
            {
                **item,
                "person_id": person["id"],
                **person,
            }
        )
    print_table(rows, _PERSON_FIELDS, title="Prospect people")
    _print_next_page(data.get("next_cursor"), limit)


@app.command("signals")
def prospects_signals(
    ctx: typer.Context,
    prospect_id: str = typer.Argument(..., help="Prospect ID"),
    cursor: str | None = typer.Option(None, "--cursor", help="Page to continue"),
    limit: int = typer.Option(_PAGE_DEFAULT, "--limit", help="Page size, 1 to 100"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the signals attached to one prospect."""
    set_json_mode(json_output)
    data = _api_request(
        "get",
        f"{_PROSPECTS}/{prospect_id}/signals",
        params=_page_params(limit, cursor, json_output=json_output),
    ).json()
    if json_output:
        print_json(data)
        return
    rows = []
    for item in data.get("items", []):
        signal = item["signal"]
        source = signal.get("source") or {}
        rows.append(
            {
                **item,
                **signal,
                "provider": source.get("provider"),
            }
        )
    print_table(rows, _SIGNAL_FIELDS, title="Prospect signals")
    _print_next_page(data.get("next_cursor"), limit)


def _print_curation(data: dict, *, json_output: bool) -> None:
    """Prints the durable result of one curation intent."""
    if json_output:
        print_json(data)
        return
    _print_prospect(data)


@app.command("watch")
def prospects_watch(
    ctx: typer.Context,
    prospect_id: str = typer.Argument(..., help="Prospect ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Move one non-promoted prospect to watching."""
    set_json_mode(json_output)
    data = _api_request("post", f"{_PROSPECTS}/{prospect_id}/watch").json()
    _print_curation(data, json_output=json_output)


@app.command("dismiss")
def prospects_dismiss(
    ctx: typer.Context,
    prospect_id: str = typer.Argument(..., help="Prospect ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Move one non-promoted prospect to dismissed."""
    set_json_mode(json_output)
    data = _api_request("post", f"{_PROSPECTS}/{prospect_id}/dismiss").json()
    _print_curation(data, json_output=json_output)


_PROMOTION_FIELDS = [
    ("prospect_id", "Prospect ID"),
    ("review_state", "State"),
    ("crm_company_id", "CRM company ID"),
    ("list_id", "CRM list ID"),
]
_PROMOTED_PERSON_FIELDS = [
    ("prospect_person_id", "Prospect person ID"),
    ("intel_person_id", "Person ID"),
    ("crm_person_id", "CRM person ID"),
]


@app.command("promote")
def prospects_promote(
    ctx: typer.Context,
    prospect_id: str = typer.Argument(..., help="Prospect ID"),
    person: list[str] = typer.Option(
        [],
        "--person",
        help="A prospect person ID to promote. Repeat for each person.",
    ),
    list_id: str = typer.Option(None, "--list", help="A static CRM list the company joins."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation."),
    json_output: bool = JSON_OPTION,
) -> None:
    """Promote one prospect and its selected people into CRM."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(
            f"Promote prospect {prospect_id} and {len(person)} people into CRM?",
            abort=True,
        )
    data = _api_request(
        "post",
        f"{_PROSPECTS}/{prospect_id}/promote",
        json={"person_ids": list(person), "list_id": list_id},
    ).json()
    if json_output:
        print_json(data)
        return
    print_detail(data, _PROMOTION_FIELDS)
    people = data.get("people") or []
    if people:
        print_table(people, _PROMOTED_PERSON_FIELDS, title="Promoted people")
