"""Organization settings commands.

`ac settings framework` reads, saves and publishes the copilot approval
framework of the active organization.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.text import Text

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    _get_org_id,
    refuse_local,
    set_json_mode,
)
from ac_cli.formatting import print_json

app = typer.Typer(help="Organization settings")


@app.callback()
def settings_callback(ctx: typer.Context) -> None:
    """Initialize context shared by the settings subcommands."""
    ctx.ensure_object(dict)


framework_app = typer.Typer(help="The copilot approval framework of the active organization")
app.add_typer(framework_app, name="framework")

_SETTINGS = "/api/v1/settings"

CONTENT_OPTION = typer.Option(
    None, "--content", help="Markdown text (mutually exclusive with --content-file)"
)
CONTENT_FILE_OPTION = typer.Option(
    None,
    "--content-file",
    help="Path to a Markdown file whose contents become the text",
)


def _read_content(content: str | None, content_file: Path | None) -> str | None:
    """Returns the text from one of the two sources, or None when both are absent."""
    if content is not None and content_file is not None:
        refuse_local("--content and --content-file are mutually exclusive")
    if content_file is not None:
        try:
            return content_file.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            refuse_local("--content-file must be a readable UTF-8 file")
    return content


def _print_framework(data: dict) -> None:
    status = str(data.get("status", "draft"))
    rprint(Text.assemble(("Status:", "bold"), f" {status}"))
    if data.get("is_template"):
        rprint("[dim]Nothing saved yet. The text below is the template.[/dim]")
    if data.get("published_at"):
        who = data.get("published_by_name") or "a team member"
        rprint(Text.assemble(("Published by:", "bold"), f" {who} at {data.get('published_at')}"))
    if data.get("updated_at"):
        who = data.get("updated_by_name") or "a team member"
        rprint(Text.assemble(("Last edited by:", "bold"), f" {who} at {data.get('updated_at')}"))
    rprint("")
    Console().print(Text(str(data.get("content_md", ""))))


@framework_app.command("get")
def framework_get(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Show the framework draft of the active organization."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_SETTINGS}/framework")
    data = resp.json()
    if json_output:
        print_json(data)
        return
    _print_framework(data)


@framework_app.command("set")
def framework_set(
    ctx: typer.Context,
    content: str | None = CONTENT_OPTION,
    content_file: Path | None = CONTENT_FILE_OPTION,
    json_output: bool = JSON_OPTION,
) -> None:
    """Save the draft. The published copy does not change."""
    set_json_mode(json_output)
    text = _read_content(content, content_file)
    if text is None:
        refuse_local("Provide --content or --content-file")
    resp = _api_request("put", f"{_SETTINGS}/framework", json={"content_md": text})
    data = resp.json()
    if json_output:
        print_json(data)
        return
    rprint("[green]Draft saved[/green]")


@framework_app.command("publish")
def framework_publish(
    ctx: typer.Context,
    content: str | None = CONTENT_OPTION,
    content_file: Path | None = CONTENT_FILE_OPTION,
    json_output: bool = JSON_OPTION,
) -> None:
    """Publish the given text, or the stored draft when no text is given."""
    set_json_mode(json_output)
    text = _read_content(content, content_file)
    body = _build_body(content_md=text)
    resp = _api_request("post", f"{_SETTINGS}/framework/publish", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    who = data.get("published_by_name") or "you"
    rprint(Text.assemble(("Published", "green"), f" by {who} at {data.get('published_at')}"))


targeting_app = typer.Typer(help="The active organization's ideal customer profiles")
app.add_typer(targeting_app, name="targeting")


@targeting_app.command("set")
def targeting_set(
    profiles_file: Path = typer.Option(
        ...,
        "--profiles-file",
        help="JSON array of customer profiles; [] clears targeting",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Replace targeting as an owner, admin or assigned copilot."""
    set_json_mode(json_output)
    try:
        profiles = json.loads(profiles_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        refuse_local("--profiles-file must contain a JSON array")
    if not isinstance(profiles, list):
        refuse_local("--profiles-file must contain a JSON array")
    org_id = _get_org_id()
    response = _api_request(
        "patch",
        f"/api/v1/organizations/{org_id}/targeting",
        json={"ideal_customer_profiles": profiles},
    )
    if json_output:
        print_json(response.json())
    else:
        rprint("[green]Targeting saved[/green]")
