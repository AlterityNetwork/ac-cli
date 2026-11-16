"""Writing styles commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.formatting import print_detail, print_json, print_table, styled

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

    # GET /writing-styles returns WritingStyleListResponse:
    # {styles, default_style_id, total_count} — not a {data} envelope.
    items = data if isinstance(data, list) else data.get("styles", [])
    print_table(
        items,
        [
            ("style_name", "Name"),
            ("is_default", "Default"),
            ("is_active", "Active"),
            ("training_iterations", "Trained"),
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
            ("style_name", "Name"),
            ("style_prompt", "Prompt"),
            ("is_default", "Default"),
            ("is_active", "Active"),
            ("training_iterations", "Training iterations"),
            ("last_trained_at", "Last trained"),
            ("created_at", "Created"),
            ("updated_at", "Updated"),
        ],
    )


@app.command("create")
def styles_create(
    ctx: typer.Context,
    name: str = typer.Option(..., help="Style name"),
    prompt: str | None = typer.Option(None, "--prompt", help="Initial style prompt"),
    sample_email: list[str] = typer.Option(
        [], "--sample-email", help="Sample email to learn from (repeatable)"
    ),
    default: bool = typer.Option(False, "--default", help="Make this the default style"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new writing style."""
    set_json_mode(json_output)
    body = _build_body(
        style_name=name,
        initial_prompt=prompt,
        sample_emails=list(sample_email) or None,
        is_default=default or None,
    )

    resp = _api_request("post", _STYLES, json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Created style:[/green] {} ({})", data["style_name"], data["id"]))


@app.command("update")
def styles_update(
    ctx: typer.Context,
    style_id: str = typer.Argument(..., help="Writing style ID"),
    name: str | None = typer.Option(None, help="Style name"),
    prompt: str | None = typer.Option(None, "--prompt", help="Style prompt"),
    default: bool | None = typer.Option(
        None, "--default/--no-default", help="Set or clear this style as the default"
    ),
    active: bool | None = typer.Option(
        None, "--active/--inactive", help="Activate or deactivate the style"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update an existing writing style."""
    set_json_mode(json_output)
    body = _build_body(
        style_name=name,
        style_prompt=prompt,
        is_default=default,
        is_active=active,
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("put", f"{_STYLES}/{style_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Updated style:[/green] {} ({})", data["style_name"], data["id"]))


@app.command("delete")
def styles_delete(
    style_id: str = typer.Argument(..., help="Writing style ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a writing style."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete style {style_id}?", abort=True)

    _api_request("delete", f"{_STYLES}/{style_id}")

    rprint(styled("[green]Deleted style {}[/green]", style_id))


@app.command("train")
def styles_train(
    ctx: typer.Context,
    style_id: str = typer.Argument(..., help="Writing style ID"),
    num_examples: int = typer.Option(
        3, "--num-examples", min=1, max=10, help="Number of example emails to generate"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Start a training session for a writing style."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_STYLES}/{style_id}/train", json={"num_examples": num_examples})

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Training session started:[/green] {}", data["session"]["id"]))


@app.command("feedback")
def styles_feedback(
    ctx: typer.Context,
    session_id: str = typer.Argument(..., help="Training session ID"),
    email_id: str = typer.Option(
        ...,
        "--email-id",
        help=(
            "ID of the generated email to rate. "
            "Get it from 'styles train --json' or 'styles iterate --json'."
        ),
    ),
    rating: int = typer.Option(..., min=1, max=5, help="Rating for the email, 1 to 5"),
    comments: str | None = typer.Option(None, help="What to change in the style"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Submit feedback for a training session."""
    set_json_mode(json_output)
    item = _build_body(email_id=email_id, overall_rating=rating, what_to_change=comments)
    resp = _api_request(
        "post",
        f"{_STYLES}/training-sessions/{session_id}/feedback",
        json={"session_id": session_id, "feedback_items": [item]},
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Feedback submitted for session {}[/green]", session_id))


@app.command("iterate")
def styles_iterate(
    ctx: typer.Context,
    session_id: str = typer.Argument(..., help="Training session ID"),
    email_id: str = typer.Option(
        ...,
        "--email-id",
        help=(
            "ID of the generated email to rate. "
            "Get it from 'styles train --json' or 'styles iterate --json'."
        ),
    ),
    feedback: str = typer.Option(..., help="What to change in the style"),
    rating: int = typer.Option(3, min=1, max=5, help="Rating for the email, 1 to 5"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Iterate on a training session."""
    set_json_mode(json_output)
    item = _build_body(email_id=email_id, overall_rating=rating, what_to_change=feedback)
    resp = _api_request(
        "post",
        f"{_STYLES}/training-sessions/{session_id}/iterate",
        json={"feedback_item": item},
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Iteration submitted for session {}[/green]", session_id))


@app.command("analyze")
def styles_analyze(
    ctx: typer.Context,
    text: list[str] = typer.Option(
        ..., help="Sample email text to analyze. Repeat for more samples."
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Analyze text for writing style characteristics."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_STYLES}/analyze", json={"sample_emails": text})

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Analysis:[/green] {}", data.get("analysis", data)))
