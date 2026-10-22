"""Commands for Outreach: campaigns, enrollments, the stop and the draft review.

`ac agentic outreach campaigns` creates, edits, activates, pauses, resumes and
archives a campaign, and enrolls one person. `list` and `get` print the count
of live enrollments against the cap and the count per state.
`ac agentic outreach enrollments` lists the enrollments of a campaign (each row
names the person, the email and the last decision; `--search` matches the
name), reads one enrollment and its timeline, asks for a Run now (`evaluate`:
re-evaluate, retry, or retry after an added email) and ends it (`exit`).
`ac agentic outreach organization` reads, stops and resumes Outreach for the
whole organization. Only an organization admin stops or resumes.

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

app = typer.Typer(help="Outreach (agentic): campaigns, enrollments and draft review")
drafts_app = typer.Typer(help="Read, save, approve and reject Outreach email drafts")
campaigns_app = typer.Typer(help="Create, edit, pause and archive Outreach campaigns")
enrollments_app = typer.Typer(help="Read, re-evaluate and end Outreach enrollments")
organization_app = typer.Typer(help="Stop or resume Outreach for the organization")

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


# Campaigns.

_STATUSES = ("draft", "active", "paused", "archived")
_STATES = ("active", "awaiting_approval", "needs_contact_data", "ended")
_PERSON_KINDS = ("crm.person", "prospect.person")
_ENROLLMENT_PAGE_DEFAULT = 100
_ENROLLMENT_PAGE_MAX = 200
_SEARCH_MAX = 100
_ORDERS = ("desc", "asc")
# The word that clears a link on update.
_CLEAR = "none"

_CAMPAIGN_LIST_FIELDS = [
    ("id", "Campaign ID"),
    ("name", "Name"),
    ("status", "Status"),
    ("people", "People"),
    ("awaiting", "Awaiting"),
    ("needs_email", "Needs email"),
    ("ended", "Ended"),
    ("created_at", "Created"),
]
_CAMPAIGN_FIELDS = [
    ("id", "Campaign ID"),
    ("name", "Name"),
    ("status", "Status"),
    ("goal", "Goal"),
    ("instructions", "Instructions"),
    ("max_emails", "Max emails"),
    ("min_days_between_emails", "Min days between emails"),
    ("writing_style_id", "Writing style"),
    ("playbook_id", "Playbook"),
    ("battlecard_id", "Battlecard"),
    ("created_by", "Owner"),
    ("updated_at", "Updated"),
]
# A write answers no counts, so only the read prints these lines.
_CAMPAIGN_READ_FIELDS = [
    *_CAMPAIGN_FIELDS,
    ("people", "People"),
    ("active", "Active"),
    ("awaiting", "Awaiting"),
    ("needs_email", "Needs email"),
    ("ended", "Ended"),
]
_ENROLLMENT_LIST_FIELDS = [
    ("id", "Enrollment ID"),
    ("person_name", "Name"),
    ("email", "Email"),
    ("state", "State"),
    ("last_action", "Last decision"),
    ("next_due_at", "Next look"),
]
_ENROLLMENT_FIELDS = [
    ("id", "Enrollment ID"),
    ("campaign_id", "Campaign"),
    ("person_kind", "Kind"),
    ("person_id", "Person"),
    ("state", "State"),
    ("ended_reason", "Ended reason"),
    ("next_due_at", "Next look"),
    ("active_run_id", "Run holding it"),
    ("version", "Version"),
    ("enrolled_at", "Enrolled"),
    ("ended_at", "Ended at"),
]
_STOP_FIELDS = [("stopped", "Stopped"), ("stopped_at", "Since")]


def _with_counts(campaign: dict) -> dict:
    """Adds the enrollment count cells to one campaign row."""
    counts = campaign.get("enrollment_counts")
    if not isinstance(counts, dict):
        return campaign
    return {
        **campaign,
        "people": f"{counts.get('live', 0)}/{counts.get('cap', 0)}",
        "active": counts.get("active"),
        "awaiting": counts.get("awaiting_approval"),
        "needs_email": counts.get("needs_contact_data"),
        "ended": counts.get("ended"),
    }


def _with_last_action(row: dict) -> dict:
    """Adds one cell that names the last decision of an enrollment row."""
    last = row.get("last_decision")
    if not isinstance(last, dict):
        return row
    parts = [last.get("action_type"), last.get("outcome")]
    return {**row, "last_action": " · ".join(str(part) for part in parts if part)}


def _campaign_body(
    *,
    name: str | None,
    goal: str | None,
    instructions: str | None,
    max_emails: int | None,
    min_days: int | None,
    writing_style_id: str | None,
    playbook_id: str | None,
    battlecard_id: str | None,
) -> dict[str, object]:
    """Build a campaign body from the given options. A link of `none` clears it."""
    body: dict[str, object] = {}
    for key, value in (
        ("name", name),
        ("goal", goal),
        ("instructions", instructions),
        ("max_emails", max_emails),
        ("min_days_between_emails", min_days),
    ):
        if value is not None:
            body[key] = value
    for key, link in (
        ("writing_style_id", writing_style_id),
        ("playbook_id", playbook_id),
        ("battlecard_id", battlecard_id),
    ):
        if link is not None:
            body[key] = None if link.lower() == _CLEAR else link
    return body


_MAX_EMAILS = 20
_MAX_MIN_DAYS = 30


def _check_campaign_bounds(max_emails: int | None, min_days: int | None) -> None:
    """Refuse a count the API would refuse, before any HTTP call."""
    if max_emails is not None and not 1 <= max_emails <= _MAX_EMAILS:
        refuse_local(f"--max-emails is not between 1 and {_MAX_EMAILS}", max_emails)
    if min_days is not None and not 1 <= min_days <= _MAX_MIN_DAYS:
        refuse_local(f"--min-days is not between 1 and {_MAX_MIN_DAYS}", min_days)


_NAME_OPTION = typer.Option(None, "--name", help="Campaign name")
_GOAL_OPTION = typer.Option(None, "--goal", help="What a reply should achieve")
_INSTRUCTIONS_OPTION = typer.Option(None, "--instructions", help="Guidance the planner reads")
_MAX_EMAILS_OPTION = typer.Option(None, "--max-emails", help="Most emails per person, 1 to 20")
_MIN_DAYS_OPTION = typer.Option(None, "--min-days", help="Fewest days between emails, 1 to 30")
_STYLE_OPTION = typer.Option(None, "--writing-style-id", help="Writing style ID, or none")
_PLAYBOOK_OPTION = typer.Option(None, "--playbook-id", help="Playbook ID, or none")
_BATTLECARD_OPTION = typer.Option(None, "--battlecard-id", help="Battlecard ID, or none")


@campaigns_app.command("list")
def campaigns_list(
    status: str | None = typer.Option(None, "--status", help="draft, active, paused or archived"),
    limit: int = typer.Option(_PAGE_DEFAULT, "--limit", help="How many campaigns, 1 to 100"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the campaigns, newest first."""
    set_json_mode(json_output)
    if status is not None and status not in _STATUSES:
        refuse_local(f"--status must be one of: {', '.join(_STATUSES)}", status)
    if not _PAGE_MIN <= limit <= _PAGE_MAX:
        refuse_local(f"--limit is not between {_PAGE_MIN} and {_PAGE_MAX}", limit)
    params: dict[str, object] = {"limit": limit}
    if status is not None:
        params["status"] = status
    data = _api_request("get", f"{_OUTREACH}/campaigns", params=params).json()
    if json_output:
        print_json(data)
        return
    rows = [_with_counts(item) for item in data.get("items", [])]
    print_table(rows, _CAMPAIGN_LIST_FIELDS, title="Outreach campaigns")


@campaigns_app.command("get")
def campaigns_get(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Read one campaign and the count of its enrollments per state."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_OUTREACH}/campaigns/{campaign_id}").json()
    if json_output:
        print_json(data)
        return
    print_detail(_with_counts(data), _CAMPAIGN_READ_FIELDS)


@campaigns_app.command("create")
def campaigns_create(
    name: str = typer.Option(..., "--name", help="Campaign name"),
    goal: str | None = _GOAL_OPTION,
    instructions: str | None = _INSTRUCTIONS_OPTION,
    max_emails: int | None = _MAX_EMAILS_OPTION,
    min_days: int | None = _MIN_DAYS_OPTION,
    writing_style_id: str | None = _STYLE_OPTION,
    playbook_id: str | None = _PLAYBOOK_OPTION,
    battlecard_id: str | None = _BATTLECARD_OPTION,
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a draft campaign. You own it, and your mailbox sends its emails."""
    set_json_mode(json_output)
    _check_campaign_bounds(max_emails, min_days)
    body = _campaign_body(
        name=name,
        goal=goal,
        instructions=instructions,
        max_emails=max_emails,
        min_days=min_days,
        writing_style_id=writing_style_id,
        playbook_id=playbook_id,
        battlecard_id=battlecard_id,
    )
    data = _api_request("post", f"{_OUTREACH}/campaigns", json=body).json()
    if json_output:
        print_json(data)
        return
    rprint(styled("[green]Campaign {} is created as a draft.[/green]", data["id"]))
    print_detail(data, _CAMPAIGN_FIELDS)


@campaigns_app.command("update")
def campaigns_update(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    name: str | None = _NAME_OPTION,
    goal: str | None = _GOAL_OPTION,
    instructions: str | None = _INSTRUCTIONS_OPTION,
    max_emails: int | None = _MAX_EMAILS_OPTION,
    min_days: int | None = _MIN_DAYS_OPTION,
    writing_style_id: str | None = _STYLE_OPTION,
    playbook_id: str | None = _PLAYBOOK_OPTION,
    battlecard_id: str | None = _BATTLECARD_OPTION,
    json_output: bool = JSON_OPTION,
) -> None:
    """Edit a campaign. Pass `none` to a link option to clear that link."""
    set_json_mode(json_output)
    _check_campaign_bounds(max_emails, min_days)
    body = _campaign_body(
        name=name,
        goal=goal,
        instructions=instructions,
        max_emails=max_emails,
        min_days=min_days,
        writing_style_id=writing_style_id,
        playbook_id=playbook_id,
        battlecard_id=battlecard_id,
    )
    if not body:
        refuse_local("nothing to update: give at least one option")
    data = _api_request("patch", f"{_OUTREACH}/campaigns/{campaign_id}", json=body).json()
    if json_output:
        print_json(data)
        return
    print_detail(data, _CAMPAIGN_FIELDS)


def _set_status(campaign_id: str, status: str, json_output: bool) -> bool:
    """Post the status. Answer True when the caller prints the text line."""
    data = _api_request(
        "post", f"{_OUTREACH}/campaigns/{campaign_id}/status", json={"status": status}
    ).json()
    if json_output:
        print_json(data)
        return False
    return True


@campaigns_app.command("activate")
def campaigns_activate(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Start a draft campaign. Its enrollments get their first Run."""
    set_json_mode(json_output)
    if _set_status(campaign_id, "active", json_output):
        rprint(styled("[green]Campaign {} is active.[/green]", campaign_id))


@campaigns_app.command("pause")
def campaigns_pause(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Pause a campaign. No Run plans or sends until you resume it."""
    set_json_mode(json_output)
    if _set_status(campaign_id, "paused", json_output):
        rprint(styled("[yellow]Campaign {} is paused.[/yellow]", campaign_id))


@campaigns_app.command("resume")
def campaigns_resume(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Resume a paused campaign. Due Runs restart."""
    set_json_mode(json_output)
    if _set_status(campaign_id, "active", json_output):
        rprint(styled("[green]Campaign {} is active.[/green]", campaign_id))


@campaigns_app.command("archive")
def campaigns_archive(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Archive a campaign for good. Every live enrollment ends."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm("Archive the campaign and end every live enrollment?", abort=True)
    if _set_status(campaign_id, "archived", json_output):
        rprint(styled("[yellow]Campaign {} is archived.[/yellow]", campaign_id))


@campaigns_app.command("enroll")
def campaigns_enroll(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    person_kind: str = typer.Option(..., "--person-kind", help="crm.person or prospect.person"),
    person_id: str = typer.Option(..., "--person-id", help="CRM person ID or prospect person ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Enroll one person. A person in another live campaign is refused."""
    set_json_mode(json_output)
    if person_kind not in _PERSON_KINDS:
        refuse_local(f"--person-kind must be one of: {', '.join(_PERSON_KINDS)}", person_kind)
    data = _api_request(
        "post",
        f"{_OUTREACH}/campaigns/{campaign_id}/enrollments",
        json={"person_kind": person_kind, "person_id": person_id},
    ).json()
    if json_output:
        print_json(data)
        return
    rprint(styled("[green]Enrollment {} is created.[/green]", data["id"]))
    print_detail(data, _ENROLLMENT_FIELDS)


# Enrollments.


@enrollments_app.command("list")
def enrollments_list(
    campaign_id: str = typer.Option(..., "--campaign-id", help="Campaign ID"),
    state: str | None = typer.Option(
        None, "--state", help="active, awaiting_approval, needs_contact_data or ended"
    ),
    search: str | None = typer.Option(
        None, "--search", help="Only the people whose name holds this text, in any case"
    ),
    limit: int = typer.Option(
        _ENROLLMENT_PAGE_DEFAULT, "--limit", help="How many enrollments, 1 to 200"
    ),
    offset: int = typer.Option(0, "--offset", help="How many enrollments to skip first"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the enrollments of one campaign, newest first, with each person and last decision."""
    set_json_mode(json_output)
    if state is not None and state not in _STATES:
        refuse_local(f"--state must be one of: {', '.join(_STATES)}", state)
    if not _PAGE_MIN <= limit <= _ENROLLMENT_PAGE_MAX:
        refuse_local(f"--limit is not between {_PAGE_MIN} and {_ENROLLMENT_PAGE_MAX}", limit)
    if offset < 0:
        refuse_local("--offset may not be negative", offset)
    if search is not None and len(search) > _SEARCH_MAX:
        refuse_local(f"--search is longer than {_SEARCH_MAX} characters", len(search))
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if state is not None:
        params["state"] = state
    if search is not None:
        params["search"] = search
    data = _api_request(
        "get", f"{_OUTREACH}/campaigns/{campaign_id}/enrollments", params=params
    ).json()
    if json_output:
        print_json(data)
        return
    rows = [_with_last_action(row) for row in data.get("data", [])]
    total = data.get("total", len(rows))
    shown = f"{offset + 1}-{offset + len(rows)} of {total}" if rows else f"0 of {total}"
    print_table(rows, _ENROLLMENT_LIST_FIELDS, title=f"Outreach enrollments {shown}")
    if data.get("has_more"):
        rprint(styled("[dim]More rows wait: --offset {}[/dim]", offset + len(rows)))


@enrollments_app.command("get")
def enrollments_get(
    enrollment_id: str = typer.Argument(..., help="Enrollment ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Read one enrollment."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_OUTREACH}/enrollments/{enrollment_id}").json()
    if json_output:
        print_json(data)
        return
    print_detail(data, _ENROLLMENT_FIELDS)


_TIMELINE_FIELDS = [
    ("at", "When"),
    ("kind", "Kind"),
    ("what", "What"),
]


def _timeline_text(item: dict) -> str:
    """Answers one line that says what a timeline item holds."""
    kind = item.get("kind")
    if kind == "decision":
        parts = [item.get("action_type"), item.get("outcome"), item.get("subject")]
    elif kind == "email":
        parts = [item.get("direction"), item.get("status"), item.get("subject")]
    elif kind == "activity":
        parts = [item.get("activity_type"), item.get("status"), item.get("title")]
    elif kind == "ended":
        parts = [item.get("ended_reason")]
    else:
        parts = []
    return " · ".join(str(part) for part in parts if part)


@enrollments_app.command("timeline")
def enrollments_timeline(
    enrollment_id: str = typer.Argument(..., help="Enrollment ID"),
    limit: int = typer.Option(
        _PAGE_DEFAULT, "--limit", help="Most decisions, emails and activities, each, 1 to 100"
    ),
    order: str = typer.Option("desc", "--order", help="desc: newest first. asc: oldest first"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Read what happened to one enrollment, newest first unless --order asc."""
    set_json_mode(json_output)
    if not _PAGE_MIN <= limit <= _PAGE_MAX:
        refuse_local(f"--limit is not between {_PAGE_MIN} and {_PAGE_MAX}", limit)
    if order not in _ORDERS:
        refuse_local(f"--order must be one of: {', '.join(_ORDERS)}", order)
    data = _api_request(
        "get",
        f"{_OUTREACH}/enrollments/{enrollment_id}/timeline",
        params={"limit": limit, "order": order},
    ).json()
    if json_output:
        print_json(data)
        return
    rows = [{**item, "what": _timeline_text(item)} for item in data.get("items", [])]
    sequence = "oldest first" if order == "asc" else "newest first"
    print_table(
        rows,
        _TIMELINE_FIELDS,
        title=f"Outreach timeline: {data.get('campaign_name') or ''} ({sequence})",
    )


@enrollments_app.command("evaluate")
def enrollments_evaluate(
    enrollment_id: str = typer.Argument(..., help="Enrollment ID"),
    request_id: str | None = typer.Option(
        None, "--request-id", help="Your id for this request. A repeat starts no second Run"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Ask for a Run now: re-evaluate, retry, or retry after you added an email."""
    set_json_mode(json_output)
    body: dict[str, str] = {} if request_id is None else {"request_id": request_id}
    data = _api_request(
        "post", f"{_OUTREACH}/enrollments/{enrollment_id}/evaluate", json=body
    ).json()
    if json_output:
        print_json(data)
        return
    rprint(styled("[green]A Run is requested:[/green] {}", data["event_id"]))


@enrollments_app.command("exit")
def enrollments_exit(
    enrollment_id: str = typer.Argument(..., help="Enrollment ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """End the enrollment. A draft that waits for review is cancelled."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm("End this person's enrollment in the campaign?", abort=True)
    data = _api_request("post", f"{_OUTREACH}/enrollments/{enrollment_id}/exit").json()
    if json_output:
        print_json(data)
        return
    rprint(styled("[yellow]Enrollment {} ended.[/yellow]", enrollment_id))


# The organization stop.


def _print_stop(data: dict[str, object], json_output: bool) -> None:
    if json_output:
        print_json(data)
        return
    print_detail(data, _STOP_FIELDS)


@organization_app.command("status")
def organization_status(json_output: bool = JSON_OPTION) -> None:
    """Read whether the organization stopped Outreach."""
    set_json_mode(json_output)
    _print_stop(_api_request("get", f"{_OUTREACH}/organization").json(), json_output)


@organization_app.command("stop")
def organization_stop(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Stop every Outreach campaign of the organization from planning or sending."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm("Stop Outreach for the whole organization?", abort=True)
    _print_stop(_api_request("post", f"{_OUTREACH}/organization/stop").json(), json_output)


@organization_app.command("resume")
def organization_resume(json_output: bool = JSON_OPTION) -> None:
    """Resume Outreach for the organization. Due Runs restart."""
    set_json_mode(json_output)
    _print_stop(_api_request("post", f"{_OUTREACH}/organization/resume").json(), json_output)


app.add_typer(drafts_app, name="drafts")
app.add_typer(campaigns_app, name="campaigns")
app.add_typer(enrollments_app, name="enrollments")
app.add_typer(organization_app, name="organization")
