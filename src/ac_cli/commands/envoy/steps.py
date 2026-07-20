"""Envoy sequence steps commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, set_json_mode, should_skip_confirm
from ac_cli.commands.crm import _api_request, _build_body
from ac_cli.commands.envoy import _ENVOY
from ac_cli.formatting import print_json, print_table

steps_app = typer.Typer(help="Sequence step operations")


@steps_app.command("create")
def steps_create(
    ctx: typer.Context,
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
    step_type: str = typer.Option(..., "--type", help="Step type (message, delay, task)"),
    step_order: int | None = typer.Option(None, "--step-order", help="Position in sequence"),
    message_template: str | None = typer.Option(
        None, "--message-template", help="Message template"
    ),
    prompt: str | None = typer.Option(None, help="AI prompt for message generation"),
    delay_value: int | None = typer.Option(None, "--delay-value", help="Delay value"),
    delay_unit: str | None = typer.Option(None, "--delay-unit", help="Delay unit (hours, days)"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a step in a sequence."""
    set_json_mode(json_output)
    body = _build_body(
        type=step_type,
        step_order=step_order,
        message_template=message_template,
        prompt=prompt,
        delay_value=delay_value,
        delay_unit=delay_unit,
    )

    resp = _api_request("post", f"{_ENVOY}/sequences/{sequence_id}/steps", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Created step:[/green] {data.get('step_type', step_type)} ({data['id']})")


@steps_app.command("update")
def steps_update(
    ctx: typer.Context,
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
    step_id: str = typer.Argument(..., help="Step ID"),
    message_template: str | None = typer.Option(
        None, "--message-template", help="Message template"
    ),
    prompt: str | None = typer.Option(None, help="AI prompt"),
    delay_value: int | None = typer.Option(None, "--delay-value", help="Delay value"),
    delay_unit: str | None = typer.Option(None, "--delay-unit", help="Delay unit"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a sequence step."""
    set_json_mode(json_output)
    body = _build_body(
        message_template=message_template,
        prompt=prompt,
        delay_value=delay_value,
        delay_unit=delay_unit,
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_ENVOY}/sequences/{sequence_id}/steps/{step_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated step {step_id}[/green]")


@steps_app.command("delete")
def steps_delete(
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
    step_id: str = typer.Argument(..., help="Step ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a sequence step."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete step {step_id}?", abort=True)

    _api_request("delete", f"{_ENVOY}/sequences/{sequence_id}/steps/{step_id}")

    rprint(f"[green]Deleted step {step_id}[/green]")


@steps_app.command("reorder")
def steps_reorder(
    ctx: typer.Context,
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
    step_ids: str = typer.Option(
        ..., "--step-ids", help="Comma-separated step IDs in desired order"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Reorder steps in a sequence."""
    set_json_mode(json_output)
    ids_list = [s.strip() for s in step_ids.split(",")]
    resp = _api_request(
        "put", f"{_ENVOY}/sequences/{sequence_id}/steps/reorder", json={"step_ids": ids_list}
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Reordered {len(ids_list)} steps in sequence {sequence_id}[/green]")


@steps_app.command("stats")
def steps_stats(
    ctx: typer.Context,
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show step execution statistics for a sequence."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ENVOY}/sequences/{sequence_id}/step-stats")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    if not items:
        rprint("[dim]No step statistics available.[/dim]")
        return

    print_table(
        items,
        [
            ("step_order", "Order"),
            ("step_type", "Type"),
            ("total", "Total"),
            ("sent", "Sent"),
            ("replied", "Replied"),
            ("bounced", "Bounced"),
        ],
        title="Step Statistics",
    )


@steps_app.command("retry")
def steps_retry(
    ctx: typer.Context,
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
    step_id: str = typer.Argument(..., help="Step ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Re-queue a step's failed recipients so the poller runs them again."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_ENVOY}/sequences/{sequence_id}/steps/{step_id}/retry")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(
            f"[green]Re-queued {data.get('retried', 0)} failed recipient(s) "
            f"for step {step_id}[/green]"
        )
