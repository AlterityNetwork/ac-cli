"""CRM company duplicate-merge commands (ENG-1963, ENG-1964).

Three steps, deliberately separate: `candidates` finds components, `preview`
shows what a merge would move, `apply` writes. `--include-deleted` widens all of
them to tombstones — companies soft-deleted before merge machinery existed,
whose history is unreachable from the live sibling.
"""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.crm import _CRM, _api_request, _build_body
from ac_cli.formatting import as_text, print_json, print_table, styled

merge_app = typer.Typer(help="Find and merge duplicate companies")

_MERGE = f"{_CRM}/companies/merge"

INCLUDE_DELETED_OPTION = typer.Option(
    False,
    "--include-deleted",
    help=(
        "Include soft-deleted companies. On `candidates`, returns components "
        "pairing a tombstone with a live sibling; on `apply`, lets the survivor "
        "absorb an already-deleted loser."
    ),
)


def _parse_selections(pairs: list[str] | None) -> dict[str, str]:
    """`--set website=<company_id>` -> {"website": "<company_id>"}."""
    selections: dict[str, str] = {}
    for pair in pairs or []:
        field, sep, source = pair.partition("=")
        if not sep or not field.strip() or not source.strip():
            rprint(styled("[red]Invalid --set {}; expected field=company_id[/red]", f"{pair!r}"))
            raise typer.Exit(code=2)
        selections[field.strip()] = source.strip()
    return selections


@merge_app.command("candidates")
def merge_candidates(
    ctx: typer.Context,
    kinds: list[str] | None = typer.Option(
        None,
        "--kind",
        help="Evidence to match on: linkedin, domain, name. Repeatable.",
    ),
    include_deleted: bool = INCLUDE_DELETED_OPTION,
    limit: int = typer.Option(50, help="Max groups"),
    offset: int = typer.Option(0, help="Offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List duplicate company candidate groups."""
    set_json_mode(json_output)
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if include_deleted:
        params["include_deleted"] = "true"
    if kinds:
        params["kinds"] = kinds

    data = _api_request("get", f"{_MERGE}/candidates", params=params).json()
    if json_output:
        print_json(data)
        return

    groups = data.get("data", [])
    if not groups:
        rprint("[dim]No duplicate candidates found.[/dim]")
        return

    for index, group in enumerate(groups, start=offset + 1):
        reasons = ", ".join(group.get("match_reasons", [])) or "none"
        rprint(styled("\n[bold]Group {}[/bold]  (matched on: {})", index, reasons))
        print_table(
            [
                {
                    "name": c.get("name"),
                    "state": "deleted" if c.get("deleted_at") else "live",
                    "linkedin_url": c.get("linkedin_url"),
                    "normalized_domain": c.get("normalized_domain"),
                    "id": c.get("id"),
                }
                for c in group.get("companies", [])
            ],
            [
                ("name", "Name"),
                ("state", "State"),
                ("normalized_domain", "Domain"),
                ("linkedin_url", "LinkedIn"),
                ("id", "ID"),
            ],
        )

    rprint(styled("\n[dim]{} of {} group(s).[/dim]", len(groups), data.get("total", 0)))


@merge_app.command("preview")
def merge_preview(
    ctx: typer.Context,
    company_ids: list[str] = typer.Option(
        ...,
        "--company-id",
        help="Company in the component. Repeat for each (at least two).",
    ),
    survivor_id: str = typer.Option(
        ..., "--survivor", help="Company that stays live and absorbs the rest"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show what a merge would move, without writing anything."""
    set_json_mode(json_output)
    body = _build_body(company_ids=company_ids, survivor_id=survivor_id)
    data = _api_request("post", f"{_MERGE}/preview", json=body).json()

    if json_output:
        print_json(data)
        return

    print_table(
        [
            {
                "name": c.get("name"),
                "state": "deleted" if c.get("deleted_at") else "live",
                "role": "survivor" if c.get("id") == survivor_id else "loser",
                "id": c.get("id"),
            }
            for c in data.get("companies", [])
        ],
        [("name", "Name"), ("role", "Role"), ("state", "State"), ("id", "ID")],
        title="Companies",
    )

    plan = data.get("plan", [])
    if plan:
        print_table(
            plan,
            [("table", "Table"), ("repoint", "Repoint"), ("drop", "Drop")],
            title="Reference plan",
        )
    else:
        rprint("[dim]No references to move.[/dim]")

    conflicts = [f for f in data.get("fields", []) if f.get("conflict")]
    if conflicts:
        print_table(
            [{"field": f["field"], "survivor_value": f.get("survivor_value")} for f in conflicts],
            [("field", "Field"), ("survivor_value", "Survivor keeps")],
            title="Field conflicts (override with --set field=company_id)",
        )

    if data.get("already_merged"):
        rprint(styled("[dim]Already merged: {}[/dim]", ", ".join(data["already_merged"])))


@merge_app.command("apply")
def merge_apply(
    ctx: typer.Context,
    company_ids: list[str] = typer.Option(
        ...,
        "--company-id",
        help="Company in the component. Repeat for each (at least two).",
    ),
    survivor_id: str = typer.Option(
        ..., "--survivor", help="Company that stays live and absorbs the rest"
    ),
    set_fields: list[str] | None = typer.Option(
        None,
        "--set",
        help="Take a field from a loser: --set website=<company_id>. Repeatable.",
    ),
    include_deleted: bool = INCLUDE_DELETED_OPTION,
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Merge a component: repoint references, then soft-delete the losers."""
    set_json_mode(json_output)
    selections = _parse_selections(set_fields)

    if not should_skip_confirm(yes):
        losers = [c for c in company_ids if c != survivor_id]
        typer.confirm(f"Merge {len(losers)} company(ies) into {survivor_id}?", abort=True)

    body = _build_body(
        company_ids=company_ids,
        survivor_id=survivor_id,
        field_selections=selections or None,
        include_deleted=include_deleted or None,
    )
    data = _api_request("post", _MERGE, json=body).json()

    if json_output:
        print_json(data)
        return

    merged = data.get("merged", [])
    rprint(
        styled("[green]Merged {} company(ies) into {}[/green]", len(merged), data["survivor_id"])
    )
    for company_id in merged:
        rprint(as_text(f"  - {company_id}"))
    if data.get("already_merged"):
        rprint(styled("[dim]Skipped (already merged): {}[/dim]", ", ".join(data["already_merged"])))
    for field, change in (data.get("field_updates") or {}).items():
        rprint(
            styled(
                "[dim]{}: {} -> {}[/dim]", field, f"{change.get('from')!r}", f"{change.get('to')!r}"
            )
        )
