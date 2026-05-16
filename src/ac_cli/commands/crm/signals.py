"""CRM signals commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, set_json_mode, should_skip_confirm
from ac_cli.commands.crm import _CRM, _api_request, _build_body
from ac_cli.formatting import print_detail, print_json, print_table

signals_app = typer.Typer(help="Signal operations (buying signals attached to companies/people)")


def _build_attach(
    company_id: str | None,
    person_id: str | None,
    score: int | None = None,
) -> dict:
    if bool(company_id) == bool(person_id):
        rprint("[red]Must specify exactly one of --company-id or --person-id[/red]")
        raise typer.Exit(code=1)
    subject_type = "company" if company_id else "person"
    subject_id = company_id or person_id
    attach: dict = {"subject_type": subject_type, "subject_id": subject_id}
    if score is not None:
        attach["attachment_score"] = score
    return attach


@signals_app.command("list")
def signals_list(
    ctx: typer.Context,
    signal_type: str | None = typer.Option(None, "--signal-type", help="Filter by signal type"),
    company_id: str | None = typer.Option(None, "--company-id", help="Filter by company"),
    company_ids: str | None = typer.Option(
        None, "--company-ids", help="Comma-separated company IDs"
    ),
    person_id: str | None = typer.Option(None, "--person-id", help="Filter by person"),
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List signals."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset}
    if signal_type:
        params["signal_type"] = signal_type
    if company_id:
        params["company_id"] = company_id
    if company_ids:
        params["company_ids"] = company_ids
    if person_id:
        params["person_id"] = person_id

    resp = _api_request("get", f"{_CRM}/signals", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data.get("data", []),
        [
            ("signal_type", "Type"),
            ("description", "Description"),
            ("signal_date", "Date"),
            ("source_agent", "Source"),
            ("id", "ID"),
        ],
        title=f"Signals ({data.get('total', '?')} total)",
    )


@signals_app.command("get")
def signals_get(
    ctx: typer.Context,
    signal_id: str = typer.Argument(..., help="Signal ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a signal by ID (includes attachments)."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/signals/{signal_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("signal_type", "Type"),
            ("description", "Description"),
            ("signal_date", "Date"),
            ("source_url", "Source URL"),
            ("source_agent", "Source Agent"),
            ("snippet", "Snippet"),
            ("workflow_run_id", "Workflow Run"),
            ("created_at", "Created"),
        ],
    )


@signals_app.command("create")
def signals_create(
    ctx: typer.Context,
    signal_type: str = typer.Option(
        ...,
        "--signal-type",
        help="hiring, tech_stack, funding, content, leadership, growth, competitor, "
        "compliance, event, news, product, expansion, partnership",
    ),
    description: str = typer.Option(..., "--description", help="Signal description"),
    company_id: str | None = typer.Option(None, "--company-id", help="Attach to company"),
    person_id: str | None = typer.Option(None, "--person-id", help="Attach to person"),
    signal_date: str | None = typer.Option(None, "--signal-date", help="Signal date (YYYY-MM-DD)"),
    source_url: str | None = typer.Option(None, "--source-url", help="Source URL"),
    snippet: str | None = typer.Option(None, "--snippet", help="Source snippet"),
    workflow_run_id: str | None = typer.Option(
        None, "--workflow-run-id", help="Originating workflow run"
    ),
    source_agent: str | None = typer.Option(
        None, "--source-agent", help="sonar | envoy | manual (default: manual)"
    ),
    attach_score: int | None = typer.Option(None, "--attach-score", help="Relevance score 0-100"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a signal and attach it to one company or person."""
    set_json_mode(json_output)
    attach_to = _build_attach(company_id, person_id, attach_score)
    body = _build_body(
        signal_type=signal_type,
        description=description,
        signal_date=signal_date,
        source_url=source_url,
        snippet=snippet,
        workflow_run_id=workflow_run_id,
        source_agent=source_agent,
    )
    body["attach_to"] = attach_to

    resp = _api_request("post", f"{_CRM}/signals", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Created signal:[/green] {data.get('description', '')} ({data['id']})")


@signals_app.command("attach")
def signals_attach(
    ctx: typer.Context,
    signal_id: str = typer.Argument(..., help="Signal ID"),
    company_id: str | None = typer.Option(None, "--company-id", help="Attach to company"),
    person_id: str | None = typer.Option(None, "--person-id", help="Attach to person"),
    score: int | None = typer.Option(None, "--score", help="Relevance score 0-100"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Attach an existing signal to an additional company or person."""
    set_json_mode(json_output)
    attach_to = _build_attach(company_id, person_id, score)

    resp = _api_request("post", f"{_CRM}/signals/{signal_id}/attach", json={"attach_to": attach_to})

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        subj = attach_to["subject_type"]
        rprint(f"[green]Attached signal {signal_id} to {subj} {attach_to['subject_id']}[/green]")


@signals_app.command("delete")
def signals_delete(
    signal_id: str = typer.Argument(..., help="Signal ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete a signal."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete signal {signal_id}?", abort=True)

    _api_request("delete", f"{_CRM}/signals/{signal_id}")

    if json_output:
        print_json({"ok": True, "id": signal_id, "action": "delete"})
    else:
        rprint(f"[green]Deleted signal {signal_id}[/green]")
