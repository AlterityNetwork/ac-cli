"""Commands for the Outreach email draft review.

`ac agentic outreach drafts` reads the emails an Outreach Run drafted and that
wait for a person, then saves, approves or rejects one. The draft is named by
its decision id.

Approve sends back the `version` and the `content_hash` that `get` (or the
last `save`) printed. The API answers 409 when either one moved, so a person
approves exactly the text they read. Approval goes only through this review.
"""

from __future__ import annotations

import re
from pathlib import Path

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    refuse_local,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.formatting import as_text, print_detail, print_json, print_table, styled

app = typer.Typer(help="Outreach (agentic): review the email drafts")
drafts_app = typer.Typer(help="Read, save, approve and reject Outreach email drafts")

_OUTREACH = "/api/v1/agentic/outreach"
_PAGE_DEFAULT = 50
_PAGE_MIN = 1
_PAGE_MAX = 100
_MODES = ("regenerate", "skip", "exit")
_HASH = re.compile(r"^[0-9a-f]{64}$")

_LIST_FIELDS = [
    ("decision_id", "Draft ID"),
    ("subject", "Subject"),
    ("to_emails", "To"),
    ("outcome", "Outcome"),
    ("campaign_id", "Campaign"),
    ("created_at", "Created"),
]
_DETAIL_FIELDS = [
    ("decision_id", "Draft ID"),
    ("outcome", "Outcome"),
    ("enrollment_state", "Enrollment"),
    ("campaign_status", "Campaign"),
    ("version", "Version"),
    ("content_hash", "Content hash"),
    ("reviewable", "Reviewable"),
    ("locked", "Locked"),
    ("approval_expires_at", "Approval expires"),
    ("reason", "Why now"),
    ("reviewer_note", "Reviewer note"),
    ("failure_code", "Failure"),
]


def _print_review(data: dict) -> None:
    """Print one draft review, its text, and the approve command it allows."""
    print_detail(data, _DETAIL_FIELDS)
    draft = data.get("draft")
    if draft:
        rprint("[bold]To:[/bold]", as_text(", ".join(draft.get("to_emails") or [])))
        rprint("[bold]Subject:[/bold]", as_text(draft.get("subject") or ""))
        rprint("[bold]Body:[/bold]")
        rprint(as_text(draft.get("body") or ""))
    if data.get("reviewable") and not data.get("locked"):
        rprint(
            "[dim]Approve:[/dim]",
            as_text(
                f"ac agentic outreach drafts approve {data['decision_id']} "
                f"--version {data['version']} --content-hash {data['content_hash']}"
            ),
        )


@drafts_app.command("list")
def drafts_list(
    campaign_id: str | None = typer.Option(None, "--campaign-id", help="Only this campaign"),
    limit: int = typer.Option(_PAGE_DEFAULT, "--limit", help="How many drafts, 1 to 100"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the email drafts that wait for review, newest first."""
    set_json_mode(json_output)
    if not _PAGE_MIN <= limit <= _PAGE_MAX:
        refuse_local(f"--limit is not between {_PAGE_MIN} and {_PAGE_MAX}", limit)
    params: dict[str, object] = {"limit": limit}
    if campaign_id is not None:
        params["campaign_id"] = campaign_id
    data = _api_request("get", f"{_OUTREACH}/drafts", params=params).json()
    if json_output:
        print_json(data)
        return
    rows = [
        {**item, "to_emails": ", ".join(item.get("to_emails") or [])}
        for item in data.get("items", [])
    ]
    print_table(rows, _LIST_FIELDS, title="Outreach drafts")


@drafts_app.command("get")
def drafts_get(
    decision_id: str = typer.Argument(..., help="Draft ID (the decision id)"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Read one draft, its version and its content hash."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_OUTREACH}/drafts/{decision_id}").json()
    if json_output:
        print_json(data)
        return
    _print_review(data)


@drafts_app.command("save")
def drafts_save(
    decision_id: str = typer.Argument(..., help="Draft ID (the decision id)"),
    subject: str | None = typer.Option(None, "--subject", help="New subject"),
    body: str | None = typer.Option(None, "--body", help="New plain text body"),
    body_file: Path | None = typer.Option(
        None, "--body-file", help="Read the new body from this file", exists=True, dir_okay=False
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Save the draft text. A save after the approval fails with 409."""
    set_json_mode(json_output)
    if body is not None and body_file is not None:
        refuse_local("give --body or --body-file, not both")
    if body_file is not None:
        body = body_file.read_text(encoding="utf-8")
    patch: dict[str, str] = {}
    if subject is not None:
        patch["subject"] = subject
    if body is not None:
        patch["body"] = body
    if not patch:
        refuse_local("nothing to save: give --subject, --body or --body-file")
    data = _api_request("patch", f"{_OUTREACH}/drafts/{decision_id}", json=patch).json()
    if json_output:
        print_json(data)
        return
    _print_review(data)


@drafts_app.command("approve")
def drafts_approve(
    decision_id: str = typer.Argument(..., help="Draft ID (the decision id)"),
    version: int = typer.Option(..., "--version", help="The version `get` printed"),
    content_hash: str = typer.Option(
        ..., "--content-hash", help="The content hash of the text you read"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Approve the text you read. The Run then sends it once."""
    set_json_mode(json_output)
    if not _HASH.match(content_hash):
        refuse_local("--content-hash is not a 64 character hex digest", content_hash)
    data = _api_request(
        "post",
        f"{_OUTREACH}/drafts/{decision_id}/approve",
        json={"version": version, "content_hash": content_hash},
    ).json()
    if json_output:
        print_json(data)
        return
    rprint(styled("[green]Draft {} is approved.[/green]", decision_id))
    _print_review(data)


@drafts_app.command("reject")
def drafts_reject(
    decision_id: str = typer.Argument(..., help="Draft ID (the decision id)"),
    mode: str = typer.Option(
        ...,
        "--mode",
        help=(
            "regenerate: plan a new email now. skip: send nothing and look again "
            "later. exit: end the enrollment."
        ),
    ),
    note: str | None = typer.Option(None, "--note", help="Feedback that later Runs read"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation for --mode exit"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Reject the email, then regenerate, skip or exit the campaign."""
    set_json_mode(json_output)
    if mode not in _MODES:
        refuse_local(f"--mode must be one of: {', '.join(_MODES)}", mode)
    if mode == "exit" and not should_skip_confirm(yes):
        typer.confirm("End this person's enrollment in the campaign?", abort=True)
    body: dict[str, str] = {"mode": mode}
    if note is not None:
        body["note"] = note
    data = _api_request("post", f"{_OUTREACH}/drafts/{decision_id}/reject", json=body).json()
    if json_output:
        print_json(data)
        return
    rprint(styled("[yellow]Draft {} is rejected ({}).[/yellow]", decision_id, mode))


app.add_typer(drafts_app, name="drafts")
