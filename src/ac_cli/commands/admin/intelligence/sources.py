# +--------------------------------------------------------------------------+
# | Admin Intelligence — Sources                                       |
# +--------------------------------------------------------------------------+
# | Role                                                                     |
# | CRUD over intel_sources, the shared provenance + cost ledger.   |
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
    sources_app,
)
from ac_cli.formatting import print_detail, print_json, print_table


@sources_app.command("list")
def sources_list(
    ctx: typer.Context,
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
    sort: str | None = typer.Option(None, help="Sort field"),
    order: str | None = typer.Option(None, help="Sort order (asc/desc)"),
    limit: int = typer.Option(50, "--limit", help="Page size"),
    offset: int = typer.Option(0, "--offset", help="Row offset"),
    provider: str | None = typer.Option(None, help="Filter by provider"),
    kind: str | None = typer.Option(None, help="Filter by kind (company/people/signal)"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List intel provenance sources."""
    set_json_mode(json_output)
    params = _list_params(query, sort, order, limit, offset, provider=provider, kind=kind)
    resp = _api_request("get", f"{_INTEL}/sources", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data.get("data", []),
        [
            ("provider", "Provider"),
            ("kind", "Kind"),
            ("ref", "Ref"),
            ("cost_usd", "Cost (USD)"),
            ("fetched_at", "Fetched"),
            ("id", "ID"),
        ],
        title=f"Intel sources ({data.get('total', '?')} total)",
    )


@sources_app.command("get")
def sources_get(
    ctx: typer.Context,
    source_id: str = typer.Argument(..., help="Intel source ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get one provenance row. Use --json to see the raw provider payload."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_INTEL}/sources/{source_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("provider", "Provider"),
            ("kind", "Kind"),
            ("ref", "Ref"),
            ("cost_usd", "Cost (USD)"),
            ("fetched_at", "Fetched"),
        ],
    )


@sources_app.command("create")
def sources_create(
    ctx: typer.Context,
    provider: str = typer.Option(..., help="Provider name (exa, parallel, manual, ...)"),
    kind: str = typer.Option(..., help="Entity kind (company/people/signal)"),
    ref: str | None = typer.Option(None, help="The link or identity the fetch keyed on"),
    cost_usd: float | None = typer.Option(None, "--cost-usd", help="Provider spend"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create an intel source (manual provenance entry)."""
    set_json_mode(json_output)
    body = _write_body(provider=provider, kind=kind, ref=ref, cost_usd=cost_usd)
    resp = _api_request("post", f"{_INTEL}/sources", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    print_detail(data, [("id", "ID"), ("provider", "Provider"), ("kind", "Kind")])


@sources_app.command("update")
def sources_update(
    ctx: typer.Context,
    source_id: str = typer.Argument(..., help="Intel source ID"),
    provider: str | None = typer.Option(None, help="Provider name"),
    kind: str | None = typer.Option(None, help="Entity kind"),
    ref: str | None = typer.Option(None, help="The link or identity the fetch keyed on"),
    cost_usd: float | None = typer.Option(None, "--cost-usd", help="Provider spend"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update an intel source. The pre-image is written to the admin audit log."""
    set_json_mode(json_output)
    body = _write_body(provider=provider, kind=kind, ref=ref, cost_usd=cost_usd)
    if not body:
        typer.echo("No fields to update")
        raise typer.Exit(1)
    resp = _api_request("patch", f"{_INTEL}/sources/{source_id}", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    print_detail(data, [("id", "ID"), ("provider", "Provider"), ("kind", "Kind")])


@sources_app.command("delete")
def sources_delete(
    ctx: typer.Context,
    source_id: str = typer.Argument(..., help="Intel source ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete an intel source (provider takedown). Citations cascade; facts don't."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete intel source {source_id}?", abort=True)
    resp = _api_request("delete", f"{_INTEL}/sources/{source_id}")
    if json_output:
        print_json(resp.json())
        return
    typer.echo(f"Deleted intel source {source_id}")


@sources_app.command("bulk-delete")
def sources_bulk_delete(
    ctx: typer.Context,
    ids: list[str] = typer.Option(..., "--id", help="Intel source ID (repeatable)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete many intel sources in one request."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete {len(ids)} intel sources?", abort=True)
    resp = _api_request("post", f"{_INTEL}/sources/bulk-delete", json={"ids": ids})
    data = resp.json()
    if json_output:
        print_json(data)
        return
    typer.echo(f"Deleted {data.get('deleted', 0)} of {data.get('requested', len(ids))}")
