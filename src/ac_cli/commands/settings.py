"""Organization settings commands.

`ac settings framework` reads, saves and publishes the copilot approval
framework of the active organization. `ac settings dossier` prints Memory:
what the apps know about the organization and about you. `ac settings memory`
lists and changes your memory lines. The email writer reads the `all` and
`email` lines. The chat reads the `all` lines. `ac settings memory suggestions`
lists the lines that the app learns from your edits to email drafts. Accept
one to add it as an `email` memory line.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import NoReturn

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
    should_skip_confirm,
)
from ac_cli.formatting import print_detail, print_json, print_table, styled

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


dossier_app = typer.Typer(
    help="Memory: what the apps know about the active organization and about you"
)
app.add_typer(dossier_app, name="dossier")


@dossier_app.command("get")
def dossier_get(
    user: bool = typer.Option(
        False, "--user", help="Add the section about you: profile, signature, writing style"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Print Memory as Markdown.

    The Markdown goes to stdout, so it pipes to a file. The empty fields go to
    stderr with the Settings page that fills each one.
    """
    set_json_mode(json_output)
    params = {"include_user": "true"} if user else None
    response = _api_request("get", f"{_SETTINGS}/dossier", params=params)
    data = response.json()
    if json_output:
        print_json(data)
        return
    typer.echo(data.get("markdown") or "", nl=False)
    gaps = data.get("gaps") or []
    if gaps:
        typer.echo("", err=True)
        typer.echo("Empty fields:", err=True)
        for gap in gaps:
            typer.echo(f"  - {gap.get('message')} ({gap.get('settings_path')})", err=True)


def _write_failed(path: Path, exc: OSError, *, json_output: bool) -> NoReturn:
    """Reports a file the command could not write, then exits 1.

    A write failure is a runtime error, not bad input, so it takes exit code 1
    and not the validation code that refuse_local uses.
    """
    message = f"Could not write {path}: {exc.strerror or exc}"
    if json_output:
        print_json({"error": True, "status_code": None, "detail": message})
    else:
        rprint("[red]Error:[/red]", Text(message))
    raise typer.Exit(code=1)


_FILENAME = re.compile(r'filename="([^"/\\]+)"')


@dossier_app.command("pdf")
def dossier_pdf(
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Where to save the PDF. Defaults to the server file name in this folder",
    ),
    user: bool = typer.Option(
        False, "--user", help="Add the section about you: profile, signature, writing style"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Save Memory as a PDF file."""
    set_json_mode(json_output)
    params = {"include_user": "true"} if user else None
    response = _api_request("get", f"{_SETTINGS}/dossier/pdf", params=params)
    if output is None:
        match = _FILENAME.search(response.headers.get("content-disposition", ""))
        output = Path(match.group(1) if match else "memory.pdf")
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(response.content)
    except OSError as exc:
        _write_failed(output, exc, json_output=json_output)
    if json_output:
        print_json({"path": str(output), "bytes": len(response.content)})
        return
    typer.echo(f"Saved {output}")


memory_app = typer.Typer(help="Your memory lines: standing instructions that the apps read")
app.add_typer(memory_app, name="memory")


class _AppliesTo(str, Enum):
    """The apps that read a memory line."""

    all = "all"
    email = "email"


APPLIES_TO_HELP = "all: every app reads the line. email: only the email writer reads it"

_MEMORY_FIELDS = [
    ("id", "ID"),
    ("text", "Text"),
    ("applies_to", "Applies to"),
    ("source", "Source"),
    ("updated_at", "Updated"),
]


@memory_app.command("list")
def memory_list(json_output: bool = JSON_OPTION) -> None:
    """List your memory lines in the active organization, oldest first."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_SETTINGS}/memory").json()
    if json_output:
        print_json(data)
        return
    lines = data.get("data", [])
    if not lines:
        rprint("[yellow]No memories[/yellow]")
        return
    title = f"Memory ({data.get('total', '?')} of {data.get('max_lines', '?')})"
    print_table(lines, _MEMORY_FIELDS, title=title)


@memory_app.command("add")
def memory_add(
    text: str = typer.Option(..., "--text", help="One line of 1 to 1000 characters"),
    applies_to: _AppliesTo | None = typer.Option(
        None, "--applies-to", case_sensitive=False, help=f"{APPLIES_TO_HELP}. Default: all"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Add a memory line."""
    set_json_mode(json_output)
    body = _build_body(text=text, applies_to=applies_to.value if applies_to else None)
    data = _api_request("post", f"{_SETTINGS}/memory", json=body).json()
    if json_output:
        print_json(data)
        return
    rprint(styled("[green]Added memory {}[/green]", data.get("id")))
    print_detail(data, _MEMORY_FIELDS)


@memory_app.command("edit")
def memory_edit(
    line_id: str = typer.Argument(..., help="Memory line ID"),
    text: str | None = typer.Option(None, "--text", help="One line of 1 to 1000 characters"),
    applies_to: _AppliesTo | None = typer.Option(
        None, "--applies-to", case_sensitive=False, help=APPLIES_TO_HELP
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Change the text or the apps of a memory line."""
    set_json_mode(json_output)
    body = _build_body(text=text, applies_to=applies_to.value if applies_to else None)
    if not body:
        refuse_local("Provide --text or --applies-to")
    data = _api_request("patch", f"{_SETTINGS}/memory/{line_id}", json=body).json()
    if json_output:
        print_json(data)
        return
    rprint(styled("[green]Updated memory {}[/green]", data.get("id")))
    print_detail(data, _MEMORY_FIELDS)


@memory_app.command("remove")
def memory_remove(
    line_id: str = typer.Argument(..., help="Memory line ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Remove a memory line."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Remove memory {line_id}?", abort=True)
    _api_request("delete", f"{_SETTINGS}/memory/{line_id}")
    if json_output:
        print_json({"ok": True, "id": line_id, "action": "remove"})
        return
    rprint(styled("[green]Removed memory {}[/green]", line_id))


suggestions_app = typer.Typer(
    help="Memory suggestions: lines the app learns from your edits to email drafts"
)
memory_app.add_typer(suggestions_app, name="suggestions")

_SUGGESTION_FIELDS = [
    ("id", "ID"),
    ("text", "Text"),
    ("evidence", "Evidence"),
]


@suggestions_app.command("list")
def suggestions_list(json_output: bool = JSON_OPTION) -> None:
    """List the proposed suggestions. --json also prints the example edits."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_SETTINGS}/memory/suggestions").json()
    if json_output:
        print_json(data)
        return
    suggestions = data.get("data", [])
    if not suggestions:
        rprint("[yellow]No suggestions[/yellow]")
        return
    rows = [
        {
            **suggestion,
            "evidence": (
                f"{suggestion.get('evidence_count', 0)} emails / "
                f"{suggestion.get('recipient_count', 0)} people"
            ),
        }
        for suggestion in suggestions
    ]
    print_table(rows, _SUGGESTION_FIELDS, title=f"Suggestions ({data.get('total', '?')})")


@suggestions_app.command("refresh")
def suggestions_refresh(json_output: bool = JSON_OPTION) -> None:
    """Read your recent email edits again and propose new suggestions."""
    set_json_mode(json_output)
    data = _api_request("post", f"{_SETTINGS}/memory/suggestions/refresh").json()
    if json_output:
        print_json(data)
        return
    rprint(
        styled(
            "Read {} emails. {} new suggestions.",
            data.get("emails_read", 0),
            data.get("proposed", 0),
        )
    )


@suggestions_app.command("accept")
def suggestions_accept(
    suggestion_id: str = typer.Argument(..., help="Suggestion ID"),
    text: str | None = typer.Option(
        None, "--text", help="Save this text instead of the suggested text"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Accept a suggestion. The email writer then reads it as a memory line."""
    set_json_mode(json_output)
    body = _build_body(text=text)
    data = _api_request(
        "post", f"{_SETTINGS}/memory/suggestions/{suggestion_id}/accept", json=body
    ).json()
    if json_output:
        print_json(data)
        return
    rprint(
        styled("[green]Accepted suggestion {} as memory {}[/green]", suggestion_id, data.get("id"))
    )
    print_detail(data, _MEMORY_FIELDS)


@suggestions_app.command("dismiss")
def suggestions_dismiss(
    suggestion_id: str = typer.Argument(..., help="Suggestion ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Dismiss a suggestion. A dismissed suggestion does not come back."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Dismiss suggestion {suggestion_id}? It does not come back.", abort=True)
    _api_request("post", f"{_SETTINGS}/memory/suggestions/{suggestion_id}/dismiss")
    if json_output:
        print_json({"ok": True, "id": suggestion_id, "action": "dismiss"})
        return
    rprint(styled("[green]Dismissed suggestion {}[/green]", suggestion_id))
