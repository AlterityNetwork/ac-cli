"""Envoy sequences commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import should_skip_confirm
from ac_cli.commands.crm import _api_request, _build_body
from ac_cli.commands.envoy import _ENVOY
from ac_cli.formatting import print_detail, print_json, print_table

sequences_app = typer.Typer(help="Sequence operations")


@sequences_app.command("list")
def sequences_list(
    ctx: typer.Context,
    status: str | None = typer.Option(None, help="Filter by status"),
) -> None:
    """List outreach sequences."""
    params: dict = {}
    if status:
        params["status_filter"] = status

    resp = _api_request("get", f"{_ENVOY}/sequences", params=params)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("name", "Name"),
            ("status", "Status"),
            ("execution_mode", "Mode"),
            ("id", "ID"),
        ],
        title=f"Sequences ({len(items)})",
    )


@sequences_app.command("get")
def sequences_get(
    ctx: typer.Context,
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
) -> None:
    """Get a sequence by ID."""
    resp = _api_request("get", f"{_ENVOY}/sequences/{sequence_id}")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    print_detail(data, [
        ("id", "ID"),
        ("name", "Name"),
        ("description", "Description"),
        ("status", "Status"),
        ("execution_mode", "Execution Mode"),
        ("writing_style_id", "Writing Style ID"),
        ("playbook_id", "Playbook ID"),
        ("crm_list_id", "CRM List ID"),
        ("created_at", "Created"),
        ("updated_at", "Updated"),
    ])

    steps = data.get("steps", [])
    if steps:
        rprint(f"\n[bold]Steps ({len(steps)})[/bold]")
        print_table(
            steps,
            [
                ("step_order", "Order"),
                ("step_type", "Type"),
                ("id", "ID"),
            ],
        )


@sequences_app.command("create")
def sequences_create(
    ctx: typer.Context,
    name: str = typer.Option(..., help="Sequence name"),
    description: str | None = typer.Option(None, help="Description"),
    writing_style_id: str | None = typer.Option(None, "--writing-style-id", help="Writing style ID"),
    playbook_id: str | None = typer.Option(None, "--playbook-id", help="Playbook ID"),
    crm_list_id: str | None = typer.Option(None, "--crm-list-id", help="CRM list ID"),
    execution_mode: str | None = typer.Option(None, "--execution-mode", help="Execution mode"),
) -> None:
    """Create a new outreach sequence."""
    body = _build_body(
        name=name, description=description, writing_style_id=writing_style_id,
        playbook_id=playbook_id, crm_list_id=crm_list_id, execution_mode=execution_mode,
    )

    me = _api_request("get", "/whoami")
    body["organization_id"] = me.json()["organization_id"]

    resp = _api_request("post", f"{_ENVOY}/sequences", json=body)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Created sequence:[/green] {data['name']} ({data['id']})")


@sequences_app.command("update")
def sequences_update(
    ctx: typer.Context,
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
    name: str | None = typer.Option(None, help="Sequence name"),
    description: str | None = typer.Option(None, help="Description"),
    writing_style_id: str | None = typer.Option(None, "--writing-style-id", help="Writing style ID"),
    playbook_id: str | None = typer.Option(None, "--playbook-id", help="Playbook ID"),
    crm_list_id: str | None = typer.Option(None, "--crm-list-id", help="CRM list ID"),
    execution_mode: str | None = typer.Option(None, "--execution-mode", help="Execution mode"),
) -> None:
    """Update a sequence."""
    body = _build_body(
        name=name, description=description, writing_style_id=writing_style_id,
        playbook_id=playbook_id, crm_list_id=crm_list_id, execution_mode=execution_mode,
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_ENVOY}/sequences/{sequence_id}", json=body)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Updated sequence:[/green] {data['name']} ({data['id']})")


@sequences_app.command("delete")
def sequences_delete(
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a sequence."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete sequence {sequence_id}?", abort=True)

    _api_request("delete", f"{_ENVOY}/sequences/{sequence_id}")

    rprint(f"[green]Deleted sequence {sequence_id}[/green]")


@sequences_app.command("launch")
def sequences_launch(
    ctx: typer.Context,
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
    workflow_id: str = typer.Option(..., "--workflow-id", help="Workflow ID to launch with"),
) -> None:
    """Launch a sequence."""
    resp = _api_request("post", f"{_ENVOY}/sequences/{sequence_id}/launch", json={"workflow_id": workflow_id})

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Launched sequence {sequence_id}[/green]")


@sequences_app.command("pause")
def sequences_pause(
    ctx: typer.Context,
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
) -> None:
    """Pause a running sequence."""
    resp = _api_request("post", f"{_ENVOY}/sequences/{sequence_id}/pause")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Paused sequence {sequence_id}[/green]")


@sequences_app.command("resume")
def sequences_resume(
    ctx: typer.Context,
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
    workflow_id: str = typer.Option(..., "--workflow-id", help="Workflow ID"),
) -> None:
    """Resume a paused sequence."""
    resp = _api_request("post", f"{_ENVOY}/sequences/{sequence_id}/resume", json={"workflow_id": workflow_id})

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Resumed sequence {sequence_id}[/green]")
