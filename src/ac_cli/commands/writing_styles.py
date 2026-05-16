"""Writing styles commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    _get_org_id,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.formatting import print_detail, print_json, print_table

app = typer.Typer(help="Writing style operations")

_STYLES = "/api/v1/writing-styles"


@app.callback()
def styles_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@app.command("list")
def styles_list(
    ctx: typer.Context,
    include_inactive: bool = typer.Option(
        False, "--include-inactive", help="Include inactive styles"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """List writing styles."""
    set_json_mode(json_output)
    params: dict = {}
    if include_inactive:
        params["include_inactive"] = True

    resp = _api_request("get", _STYLES, params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("name", "Name"),
            ("tone", "Tone"),
            ("status", "Status"),
            ("id", "ID"),
        ],
        title=f"Writing Styles ({len(items)})",
    )


@app.command("get")
def styles_get(
    ctx: typer.Context,
    style_id: str = typer.Argument(..., help="Writing style ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a writing style by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_STYLES}/{style_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("name", "Name"),
            ("description", "Description"),
            ("tone", "Tone"),
            ("formality", "Formality"),
            ("status", "Status"),
            ("created_at", "Created"),
            ("updated_at", "Updated"),
        ],
    )


@app.command("create")
def styles_create(
    ctx: typer.Context,
    name: str = typer.Option(..., help="Style name"),
    description: str | None = typer.Option(None, help="Style description"),
    tone: str | None = typer.Option(None, help="Tone"),
    formality: str | None = typer.Option(None, help="Formality level"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new writing style."""
    set_json_mode(json_output)
    body = _build_body(
        name=name,
        description=description,
        tone=tone,
        formality=formality,
    )

    body["organization_id"] = _get_org_id()

    resp = _api_request("post", _STYLES, json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Created style:[/green] {data['name']} ({data['id']})")


@app.command("update")
def styles_update(
    ctx: typer.Context,
    style_id: str = typer.Argument(..., help="Writing style ID"),
    name: str | None = typer.Option(None, help="Style name"),
    description: str | None = typer.Option(None, help="Style description"),
    tone: str | None = typer.Option(None, help="Tone"),
    formality: str | None = typer.Option(None, help="Formality level"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update an existing writing style."""
    set_json_mode(json_output)
    body = _build_body(
        name=name,
        description=description,
        tone=tone,
        formality=formality,
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("put", f"{_STYLES}/{style_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated style:[/green] {data['name']} ({data['id']})")


@app.command("delete")
def styles_delete(
    style_id: str = typer.Argument(..., help="Writing style ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a writing style."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete style {style_id}?", abort=True)

    _api_request("delete", f"{_STYLES}/{style_id}")

    rprint(f"[green]Deleted style {style_id}[/green]")


@app.command("train")
def styles_train(
    ctx: typer.Context,
    style_id: str = typer.Argument(..., help="Writing style ID"),
    sample_text: str = typer.Option(..., "--sample-text", help="Sample text for training"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Start a training session for a writing style."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_STYLES}/{style_id}/train", json={"sample_text": sample_text})

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Training session started:[/green] {data['session_id']}")


@app.command("feedback")
def styles_feedback(
    ctx: typer.Context,
    session_id: str = typer.Argument(..., help="Training session ID"),
    rating: int = typer.Option(..., help="Rating for the training session"),
    comments: str | None = typer.Option(None, help="Optional comments"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Submit feedback for a training session."""
    set_json_mode(json_output)
    body: dict = {"rating": rating}
    if comments is not None:
        body["comments"] = comments

    resp = _api_request("post", f"{_STYLES}/training-sessions/{session_id}/feedback", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Feedback submitted for session {session_id}[/green]")


@app.command("iterate")
def styles_iterate(
    ctx: typer.Context,
    session_id: str = typer.Argument(..., help="Training session ID"),
    feedback: str = typer.Option(..., help="Feedback for iteration"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Iterate on a training session."""
    set_json_mode(json_output)
    resp = _api_request(
        "post", f"{_STYLES}/training-sessions/{session_id}/iterate", json={"feedback": feedback}
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Iteration submitted for session {session_id}[/green]")


@app.command("analyze")
def styles_analyze(
    ctx: typer.Context,
    text: str = typer.Option(..., help="Text to analyze"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Analyze text for writing style characteristics."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_STYLES}/analyze", json={"text": text})

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Analysis:[/green] {data.get('analysis', data)}")
