# +--------------------------------------------------------------------------+
# | Admin Intelligence — Signals                                       |
# +--------------------------------------------------------------------------+
# | Role                                                                     |
# | Read + create + delete over the append-only intel_signals log,  |
# | plus the intel_signal_sources citations. No update: the API has no PATCH. |
# +--------------------------------------------------------------------------+

from __future__ import annotations

import typer

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.admin.intelligence import (
    _INTEL,
    _list_params,
    _write_body,
    signals_app,
)
from ac_cli.formatting import print_detail, print_json, print_table

# No `update` verb: intel_signals is append-only and the API exposes no PATCH.
# Correct a signal by deleting and recreating it.


@signals_app.command("list")
def signals_list(
    ctx: typer.Context,
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
    sort: str | None = typer.Option(None, help="Sort field"),
    order: str | None = typer.Option(None, help="Sort order (asc/desc)"),
    limit: int = typer.Option(50, "--limit", help="Page size"),
    offset: int = typer.Option(0, "--offset", help="Row offset"),
    subject_type: str | None = typer.Option(
        None, "--subject-type", help="Filter by subject type (company/person)"
    ),
    signal_type: str | None = typer.Option(None, "--signal-type", help="Filter by signal type"),
    subject_id: str | None = typer.Option(None, "--subject-id", help="Filter by subject ID"),
    related_company_id: str | None = typer.Option(
        None, "--related-company", help="Filter by rolled-up company ID"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """List intel signals."""
    set_json_mode(json_output)
    params = _list_params(
        query,
        sort,
        order,
        limit,
        offset,
        subject_type=subject_type,
        signal_type=signal_type,
        subject_id=subject_id,
        related_company_id=related_company_id,
    )
    resp = _api_request("get", f"{_INTEL}/signals", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data.get("data", []),
        [
            ("signal_type", "Type"),
            ("subject_name", "Subject"),
            ("description", "Description"),
            ("observed_at", "Observed"),
            ("id", "ID"),
        ],
        title=f"Intel signals ({data.get('total', '?')} total)",
    )


@signals_app.command("get")
def signals_get(
    ctx: typer.Context,
    signal_id: str = typer.Argument(..., help="Intel signal ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get an intel signal, its subject, and every source that reported it."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_INTEL}/signals/{signal_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data.get("signal", {}),
        [
            ("id", "ID"),
            ("signal_type", "Type"),
            ("subject_type", "Subject type"),
            ("subject_name", "Subject"),
            ("related_company_name", "Rolls up to"),
            ("description", "Description"),
            ("observed_at", "Observed"),
            ("ingested_at", "Ingested"),
        ],
    )
    print_table(
        data.get("sources", []),
        [
            ("provider", "Provider"),
            ("ref", "Ref"),
            ("is_primary", "Discovering"),
            ("cost_usd", "Cost (USD)"),
            ("linked_at", "Linked"),
        ],
        title="Sources",
    )


@signals_app.command("create")
def signals_create(
    ctx: typer.Context,
    subject_type: str = typer.Option(..., "--subject-type", help="company or person"),
    subject_id: str = typer.Option(..., "--subject-id", help="intel_companies / intel_people ID"),
    signal_type: str = typer.Option(..., "--signal-type", help="One of the 12 signal types"),
    observed_at: str = typer.Option(
        ..., "--observed-at", help="When the event happened (ISO 8601)"
    ),
    description: str | None = typer.Option(None, help="Human-readable summary"),
    related_company_id: str | None = typer.Option(
        None, "--related-company", help="Company the signal rolls up to"
    ),
    source_id: str | None = typer.Option(None, "--source-id", help="Discovering fetch ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create an intel signal. The dedup key is derived server-side."""
    set_json_mode(json_output)
    body = _write_body(
        subject_type=subject_type,
        subject_id=subject_id,
        signal_type=signal_type,
        observed_at=observed_at,
        description=description,
        related_company_id=related_company_id,
        source_id=source_id,
    )
    resp = _api_request("post", f"{_INTEL}/signals", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    print_detail(data, [("id", "ID"), ("signal_type", "Type"), ("subject_id", "Subject")])


@signals_app.command("delete")
def signals_delete(
    ctx: typer.Context,
    signal_id: str = typer.Argument(..., help="Intel signal ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete an intel signal (its source links cascade)."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete intel signal {signal_id}?", abort=True)
    resp = _api_request("delete", f"{_INTEL}/signals/{signal_id}")
    if json_output:
        print_json(resp.json())
        return
    typer.echo(f"Deleted intel signal {signal_id}")


@signals_app.command("bulk-delete")
def signals_bulk_delete(
    ctx: typer.Context,
    ids: list[str] = typer.Option(..., "--id", help="Intel signal ID (repeatable)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete many intel signals in one request."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete {len(ids)} intel signals?", abort=True)
    resp = _api_request("post", f"{_INTEL}/signals/bulk-delete", json={"ids": ids})
    data = resp.json()
    if json_output:
        print_json(data)
        return
    typer.echo(f"Deleted {data.get('deleted', 0)} of {data.get('requested', len(ids))}")


@signals_app.command("link-source")
def signals_link_source(
    ctx: typer.Context,
    signal_id: str = typer.Argument(..., help="Intel signal ID"),
    source_id: str = typer.Option(..., "--source-id", help="Intel source ID"),
    primary: bool = typer.Option(False, "--primary", help="Mark as the discovering fetch"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Cite one more source on a signal (a corroborating outlet)."""
    set_json_mode(json_output)
    body = {"source_id": source_id, "is_primary": primary}
    resp = _api_request("post", f"{_INTEL}/signals/{signal_id}/sources", json=body)
    if json_output:
        print_json(resp.json())
        return
    typer.echo(f"Linked source {source_id} to signal {signal_id}")


@signals_app.command("unlink-source")
def signals_unlink_source(
    ctx: typer.Context,
    signal_id: str = typer.Argument(..., help="Intel signal ID"),
    source_id: str = typer.Option(..., "--source-id", help="Intel source ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Drop one citation. The signal and the source both survive."""
    set_json_mode(json_output)
    resp = _api_request("delete", f"{_INTEL}/signals/{signal_id}/sources/{source_id}")
    if json_output:
        print_json(resp.json())
        return
    typer.echo(f"Unlinked source {source_id} from signal {signal_id}")
