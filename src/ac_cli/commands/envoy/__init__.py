"""Commands for Envoy: campaigns, enrollments, the stop and the Review queue.

`ac agentic envoy campaigns` creates, edits, activates, pauses, resumes and
archives a campaign, and enrolls one person (`enroll`) or up to 200 people in
one request (`enroll-batch`). `list` and `get` print the count of live
enrollments against the cap and the count per status.
`ac agentic envoy enrollments` lists the enrollments of a campaign (each row
names the person, the email and the last decision; `--search` matches the
name), reads one enrollment and its timeline, asks for a Run now (`evaluate`:
re-evaluate, retry, or retry after an added email) and ends it (`exit`).
`ac agentic envoy organization` reads, stops and resumes Envoy for the
whole organization. Only an organization admin stops or resumes.

`ac agentic envoy drafts list` and `get` read the Review queue: the
proposed actions (an email, a LinkedIn note or a LinkedIn message) that wait
for a person. `list` reads the `pending_approval` actions by default, oldest
first, and filters by `--status`, `--campaign-id` and `--type`. `get` reads one
action by its action id. Each item names the person, the company, the campaign,
the address read fresh, the reply it answers and the draft.

`approve` takes an action id. With no edit flag it approves the draft as it
is and sends no payload. An edit flag reads the action first and sends the
draft with the edited fields over it, so `--subject` alone keeps the body. A
flag the action type does not take is refused before the approve: an email
takes `--subject` and `--body` (a reply `--body` only), a LinkedIn note
`--note`, a LinkedIn message `--message`. The API checks the edit, reads the address now, and freezes the text, the address
and their hash. A retry of the same approve answers the same action.

`reject` takes an action id and `--then`. `regenerate` needs `--reason`
and asks for one new draft that reads it. `stop` ends the enrollment, and
asks first unless `--yes`. A retry of the same reject answers the same action.
"""

from __future__ import annotations

import uuid
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

app = typer.Typer(help="Envoy (agentic): campaigns, enrollments and the Review queue")
drafts_app = typer.Typer(help="Read, approve and reject Envoy drafts")
campaigns_app = typer.Typer(help="Create, edit, pause and archive Envoy campaigns")
enrollments_app = typer.Typer(help="Read, re-evaluate and end Envoy enrollments")
organization_app = typer.Typer(help="Stop or resume Envoy for the organization")

_ENVOY = "/api/v1/agentic/envoy"
_PAGE_DEFAULT = 50
_PAGE_MIN = 1
_PAGE_MAX = 100
_THENS = ("regenerate", "stop")

_ACTION_STATUSES = (
    "pending_approval",
    "approved",
    "sending",
    "executed",
    "rejected",
    "invalidated",
    "failed",
)
_ACTION_TYPES = ("email", "linkedin_connection", "linkedin_message")

# The edit flags each action takes. A reply email keeps no subject.
_EDIT_FLAGS = {
    "email": ("--subject", "--body"),
    "email_reply": ("--body",),
    "linkedin_connection": ("--note",),
    "linkedin_message": ("--message",),
}

_LIST_FIELDS = [
    ("id", "Action ID"),
    ("person_name", "Person"),
    ("type", "Type"),
    ("to", "To"),
    ("campaign_name", "Campaign"),
    ("status", "Status"),
    ("created_at", "Created"),
]
_ACTION_FIELDS = [
    ("id", "Action ID"),
    ("decision_id", "Decision ID"),
    ("type", "Type"),
    ("status", "Status"),
    ("person_name", "Person"),
    ("company_name", "Company"),
    ("campaign_name", "Campaign"),
    ("campaign_status", "Campaign status"),
    ("to", "To"),
    ("created_at", "Created"),
    ("rationale", "Why"),
    ("objective", "Objective"),
]


def _flat(item: dict) -> dict:
    """One action with the person and the campaign names at the top level.

    A person with no name, or a deleted one, shows the address instead. A
    deleted person also has no address, so the cell is blank.
    """
    person = item.get("person") or {}
    campaign = item.get("campaign") or {}
    return {
        **item,
        "person_name": person.get("name") or item.get("to"),
        "campaign_name": campaign.get("name"),
        "campaign_status": campaign.get("status"),
    }


def _print_action(item: dict) -> None:
    """Print one proposed action, the reply it answers, and its draft."""
    print_detail(_flat(item), _ACTION_FIELDS)
    reply = item.get("replying_to")
    if reply:
        rprint("[bold]Replying to:[/bold]")
        rprint(as_text(reply.get("text") or ""))
    draft = item.get("draft_payload") or {}
    for key, label in (("subject", "Subject"), ("note", "Note"), ("body", "Body")):
        if draft.get(key) is not None:
            rprint(styled("[bold]{}:[/bold]", label))
            rprint(as_text(draft[key]))


@drafts_app.command("list")
def drafts_list(
    status: str | None = typer.Option(
        None, "--status", help="Only this status. The API default is pending_approval"
    ),
    campaign_id: str | None = typer.Option(None, "--campaign-id", help="Only this campaign"),
    action_type: str | None = typer.Option(
        None, "--type", help="Only this type: email, linkedin_connection or linkedin_message"
    ),
    limit: int = typer.Option(_PAGE_DEFAULT, "--limit", help="How many actions, 1 to 100"),
    offset: int = typer.Option(0, "--offset", help="How many actions to skip first"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the proposed actions that wait for review, oldest first, with the queue total."""
    set_json_mode(json_output)
    if status is not None and status not in _ACTION_STATUSES:
        refuse_local(f"--status must be one of: {', '.join(_ACTION_STATUSES)}", status)
    if action_type is not None and action_type not in _ACTION_TYPES:
        refuse_local(f"--type must be one of: {', '.join(_ACTION_TYPES)}", action_type)
    if not _PAGE_MIN <= limit <= _PAGE_MAX:
        refuse_local(f"--limit is not between {_PAGE_MIN} and {_PAGE_MAX}", limit)
    if offset < 0:
        refuse_local("--offset may not be negative", offset)
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if status is not None:
        params["status"] = status
    if campaign_id is not None:
        params["campaign_id"] = campaign_id
    if action_type is not None:
        params["type"] = action_type
    data = _api_request("get", f"{_ENVOY}/actions", params=params).json()
    if json_output:
        print_json(data)
        return
    rows = [_flat(item) for item in data.get("data", [])]
    total = data.get("total", len(rows))
    shown = f"{offset + 1}-{offset + len(rows)} of {total}" if rows else f"0 of {total}"
    print_table(rows, _LIST_FIELDS, title=f"Envoy actions {shown}")
    if data.get("has_more"):
        rprint(styled("[dim]More actions wait: --offset {}[/dim]", offset + len(rows)))


@drafts_app.command("get")
def drafts_get(
    action_id: str = typer.Argument(..., help="Action ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Read one proposed action: the person, the address, the reply and the draft."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_ENVOY}/actions/{action_id}").json()
    if json_output:
        print_json(data)
        return
    _print_action(data)


@drafts_app.command("approve")
def drafts_approve(
    action_id: str = typer.Argument(..., help="Action ID"),
    subject: str | None = typer.Option(None, "--subject", help="New email subject"),
    body: str | None = typer.Option(None, "--body", help="New plain text email body"),
    body_file: Path | None = typer.Option(
        None,
        "--body-file",
        help="Read the new email body from this file",
        exists=True,
        dir_okay=False,
    ),
    note: str | None = typer.Option(None, "--note", help="New LinkedIn connection note"),
    message: str | None = typer.Option(None, "--message", help="New LinkedIn message"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Approve one proposed action. The text, the address and their hash freeze.

    With no edit flag, the draft is approved as it is. An edit flag replaces
    that field of the draft, and the API checks the result.
    """
    set_json_mode(json_output)
    if sum(one is not None for one in (body, body_file, message)) > 1:
        refuse_local("give one of --body, --body-file and --message")
    if body_file is not None:
        body = body_file.read_text(encoding="utf-8")
    given = {
        flag: (key, value)
        for flag, key, value in (
            ("--subject", "subject", subject),
            ("--body", "body", body),
            ("--note", "note", note),
            ("--message", "body", message),
        )
        if value is not None
    }
    request: dict[str, object] = {}
    if given:
        action = _api_request("get", f"{_ENVOY}/actions/{action_id}").json()
        kind = action.get("type")
        if kind == "email" and action.get("replying_to"):
            kind = "email_reply"
        allowed = _EDIT_FLAGS.get(str(kind), ())
        refused = [flag for flag in given if flag not in allowed]
        if refused:
            refuse_local(
                f"this action ({kind}) takes {', '.join(allowed) or 'no edit flag'}",
                ", ".join(refused),
            )
        edits = dict(given.values())
        request["payload"] = {**(action.get("draft_payload") or {}), **edits}
    data = _api_request("post", f"{_ENVOY}/actions/{action_id}/approve", json=request).json()
    if json_output:
        print_json(data)
        return
    rprint(styled("[green]Action {} is approved.[/green]", action_id))
    _print_action(data)


@drafts_app.command("reject")
def drafts_reject(
    action_id: str = typer.Argument(..., help="Action ID"),
    then: str = typer.Option(
        ...,
        "--then",
        help="regenerate: ask for one new draft. stop: end the enrollment.",
    ),
    reason: str | None = typer.Option(
        None,
        "--reason",
        help="What the next draft must change (1 to 1000 chars). Required for regenerate.",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation for --then stop"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Reject one proposed action, then ask for a new draft or stop."""
    set_json_mode(json_output)
    if then not in _THENS:
        refuse_local(f"--then must be one of: {', '.join(_THENS)}", then)
    if then == "regenerate" and reason is None:
        refuse_local("--then regenerate needs --reason")
    if then == "stop" and not should_skip_confirm(yes):
        typer.confirm("End this person's enrollment in the campaign?", abort=True)
    body: dict[str, str] = {"then": then}
    if reason is not None:
        body["reason"] = reason
    data = _api_request("post", f"{_ENVOY}/actions/{action_id}/reject", json=body).json()
    if json_output:
        print_json(data)
        return
    rprint(styled("[yellow]Action {} is rejected ({}).[/yellow]", action_id, then))
    _print_action(data)


# Campaigns.

_STATUSES = ("active", "paused", "archived")
_ENROLLMENT_STATUSES = ("active", "needs_contact_data", "ended")
_PERSON_KINDS = ("crm.person", "prospect.person")
_ENROLLMENT_PAGE_DEFAULT = 100
_ENROLLMENT_PAGE_MAX = 200
_SEARCH_MAX = 100
_DESCRIPTION_MAX = 2000
_GOAL_MAX = 2000
_CHANNELS = ("email", "linkedin")
_MAX_TOUCHES_MAX = 10
_FOLLOWUP_DAYS_MAX = 30

_CAMPAIGN_LIST_FIELDS = [
    ("id", "Campaign ID"),
    ("name", "Name"),
    ("status", "Status"),
    ("channels", "Channels"),
    ("people", "People"),
    ("needs_email", "Needs email"),
    ("ended", "Ended"),
    ("created_at", "Created"),
]
_CAMPAIGN_FIELDS = [
    ("id", "Campaign ID"),
    ("name", "Name"),
    ("status", "Status"),
    ("description", "Description"),
    ("goal", "Goal"),
    ("channels", "Channels"),
    ("max_touches", "Max touches"),
    ("followup", "Follow-up"),
    ("sender_user_id", "Sender"),
    ("created_by", "Owner"),
    ("updated_at", "Updated"),
]
# A write answers no counts, so only the read prints these lines.
_CAMPAIGN_READ_FIELDS = [
    *_CAMPAIGN_FIELDS,
    ("people", "People"),
    ("active", "Active"),
    ("needs_email", "Needs email"),
    ("ended", "Ended"),
]
_ENROLLMENT_LIST_FIELDS = [
    ("id", "Enrollment ID"),
    ("person_name", "Name"),
    ("email", "Email"),
    ("status", "Status"),
    ("last_action", "Last decision"),
    ("next_check_at", "Next check"),
]
_ENROLLMENT_FIELDS = [
    ("id", "Enrollment ID"),
    ("campaign_id", "Campaign"),
    ("person_kind", "Kind"),
    ("person_id", "Person"),
    ("status", "Status"),
    ("ended_reason", "Ended reason"),
    ("next_check_at", "Next check"),
    ("touch_count", "Touches"),
    ("context_version", "Context version"),
    ("enrolled_at", "Enrolled"),
    ("ended_at", "Ended at"),
]
_STOP_FIELDS = [("stopped", "Stopped"), ("stopped_at", "Since")]
# The most people one enroll-batch run names: the live cap of a campaign.
_BATCH_MAX = 200
# The most people one batch request names. The API refuses more with a 422,
# so a run sends its people in chunks of this size, one after another.
_BATCH_CHUNK = 50
_BATCH_FIELDS = [
    ("person", "Person"),
    ("outcome", "Outcome"),
    ("detail", "Detail"),
]
_OUTCOME_DETAILS = {
    "campaign_full": "The campaign holds its 200 live enrollments",
    "opted_out": "The address is on the do-not-contact list",
    "not_found": "The organization holds no such person",
    "not_sent": "Not sent: an earlier request of this run failed",
}


def _with_settings(campaign: dict) -> dict:
    """Adds the channel and follow-up window cells to one campaign row."""
    cells: dict[str, object] = {}
    channels = campaign.get("allowed_channels")
    if isinstance(channels, list):
        cells["channels"] = ", ".join(str(one) for one in channels)
    low, high = campaign.get("followup_min_days"), campaign.get("followup_max_days")
    if low is not None and high is not None:
        cells["followup"] = f"{low} to {high} days"
    return {**campaign, **cells}


def _with_counts(campaign: dict) -> dict:
    """Adds the enrollment count and setting cells to one campaign row."""
    campaign = _with_settings(campaign)
    counts = campaign.get("enrollment_counts")
    if not isinstance(counts, dict):
        return campaign
    return {
        **campaign,
        "people": f"{counts.get('live', 0)}/{counts.get('cap', 0)}",
        "active": counts.get("active"),
        "needs_email": counts.get("needs_contact_data"),
        "ended": counts.get("ended"),
    }


def _with_last_action(row: dict) -> dict:
    """Adds one cell that names the last decision of an enrollment row."""
    last = row.get("last_decision")
    if not isinstance(last, dict):
        return row
    parts = [last.get("type"), last.get("status")]
    return {**row, "last_action": " · ".join(str(part) for part in parts if part)}


def _check_range(option: str, value: int | None, low: int, high: int) -> None:
    if value is not None and not low <= value <= high:
        refuse_local(f"{option} is not between {low} and {high}", value)


def _campaign_body(
    *,
    name: str | None,
    description: str | None,
    goal: str | None = None,
    channels: list[str] | None = None,
    max_touches: int | None = None,
    min_days: int | None = None,
    max_days: int | None = None,
) -> dict[str, object]:
    """Build a campaign body from the given options. An empty description clears it.

    The checks mirror the API, so a bad value is refused before any call.
    """
    if description is not None and len(description) > _DESCRIPTION_MAX:
        refuse_local(
            f"--description is longer than {_DESCRIPTION_MAX} characters", len(description)
        )
    if goal is not None and not goal.strip():
        refuse_local("--goal may not be blank")
    if goal is not None and len(goal) > _GOAL_MAX:
        refuse_local(f"--goal is longer than {_GOAL_MAX} characters", len(goal))
    for channel in channels or []:
        if channel not in _CHANNELS:
            refuse_local(f"--channel must be one of: {', '.join(_CHANNELS)}", channel)
    _check_range("--max-touches", max_touches, 1, _MAX_TOUCHES_MAX)
    _check_range("--min-days", min_days, 1, _FOLLOWUP_DAYS_MAX)
    _check_range("--max-days", max_days, 1, _FOLLOWUP_DAYS_MAX)
    if min_days is not None and max_days is not None and min_days > max_days:
        refuse_local("--min-days may not be above --max-days")
    return {
        key: value
        for key, value in (
            ("name", name),
            ("goal", goal),
            ("description", description),
            ("allowed_channels", channels or None),
            ("max_touches", max_touches),
            ("followup_min_days", min_days),
            ("followup_max_days", max_days),
        )
        if value is not None
    }


_NAME_OPTION = typer.Option(None, "--name", help="Campaign name")
_GOAL_HELP = (
    f'What the campaign wants, such as "Book a 20 min intro call", at most {_GOAL_MAX} characters'
)
_CHANNEL_OPTION = typer.Option(
    None, "--channel", help="A channel the campaign can use: email or linkedin. Repeat for both"
)
_MAX_TOUCHES_OPTION = typer.Option(
    None, "--max-touches", help="The most outbound touches per person, 1 to 10"
)
_MIN_DAYS_OPTION = typer.Option(
    None, "--min-days", help="The fewest days between two touches, 1 to 30"
)
_MAX_DAYS_OPTION = typer.Option(
    None, "--max-days", help="The most days between two touches, 1 to 30"
)
_DESCRIPTION_OPTION = typer.Option(
    None,
    "--description",
    help=f"Who the campaign is for and what you want from it, at most {_DESCRIPTION_MAX} characters",
)


@campaigns_app.command("list")
def campaigns_list(
    status: str | None = typer.Option(None, "--status", help="active, paused or archived"),
    limit: int = typer.Option(_PAGE_DEFAULT, "--limit", help="How many campaigns, 1 to 100"),
    offset: int = typer.Option(0, "--offset", help="How many campaigns to skip first"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the campaigns, newest first, one page at a time."""
    set_json_mode(json_output)
    if status is not None and status not in _STATUSES:
        refuse_local(f"--status must be one of: {', '.join(_STATUSES)}", status)
    if not _PAGE_MIN <= limit <= _PAGE_MAX:
        refuse_local(f"--limit is not between {_PAGE_MIN} and {_PAGE_MAX}", limit)
    if offset < 0:
        refuse_local("--offset may not be negative", offset)
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if status is not None:
        params["status"] = status
    data = _api_request("get", f"{_ENVOY}/campaigns", params=params).json()
    if json_output:
        print_json(data)
        return
    rows = [_with_counts(item) for item in data.get("items", [])]
    total = data.get("total", len(rows))
    shown = f"{offset + 1}-{offset + len(rows)} of {total}" if rows else f"0 of {total}"
    print_table(rows, _CAMPAIGN_LIST_FIELDS, title=f"Envoy campaigns {shown}")
    if data.get("has_more"):
        rprint(styled("[dim]More campaigns wait: --offset {}[/dim]", offset + len(rows)))


@campaigns_app.command("get")
def campaigns_get(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Read one campaign and the count of its enrollments per status."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_ENVOY}/campaigns/{campaign_id}").json()
    if json_output:
        print_json(data)
        return
    print_detail(_with_counts(data), _CAMPAIGN_READ_FIELDS)


@campaigns_app.command("create")
def campaigns_create(
    name: str = typer.Option(..., "--name", help="Campaign name"),
    # Optional for Click, so a missing --goal answers the JSON refusal.
    goal: str | None = typer.Option(None, "--goal", help=f"Required. {_GOAL_HELP}"),
    description: str | None = _DESCRIPTION_OPTION,
    channels: list[str] | None = _CHANNEL_OPTION,
    max_touches: int | None = _MAX_TOUCHES_OPTION,
    min_days: int | None = _MIN_DAYS_OPTION,
    max_days: int | None = _MAX_DAYS_OPTION,
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a paused campaign. You own it, and your mailbox sends its emails.

    A limit left out takes the default: email only, 5 touches, 3 to 7 days.
    """
    set_json_mode(json_output)
    if goal is None:
        refuse_local("--goal is required")
    body = _campaign_body(
        name=name,
        description=description,
        goal=goal,
        channels=channels,
        max_touches=max_touches,
        min_days=min_days,
        max_days=max_days,
    )
    data = _api_request("post", f"{_ENVOY}/campaigns", json=body).json()
    if json_output:
        print_json(data)
        return
    rprint(styled("[green]Campaign {} is created paused.[/green]", data["id"]))
    print_detail(_with_settings(data), _CAMPAIGN_FIELDS)


@campaigns_app.command("update")
def campaigns_update(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    name: str | None = _NAME_OPTION,
    goal: str | None = typer.Option(None, "--goal", help=_GOAL_HELP),
    description: str | None = _DESCRIPTION_OPTION,
    channels: list[str] | None = _CHANNEL_OPTION,
    max_touches: int | None = _MAX_TOUCHES_OPTION,
    min_days: int | None = _MIN_DAYS_OPTION,
    max_days: int | None = _MAX_DAYS_OPTION,
    json_output: bool = JSON_OPTION,
) -> None:
    """Edit a campaign. Pass an empty `--description` to clear the description.

    `--channel` replaces the channel list. The sender stays the creator.
    """
    set_json_mode(json_output)
    body = _campaign_body(
        name=name,
        description=description,
        goal=goal,
        channels=channels,
        max_touches=max_touches,
        min_days=min_days,
        max_days=max_days,
    )
    if not body:
        refuse_local("nothing to update: give at least one option")
    data = _api_request("patch", f"{_ENVOY}/campaigns/{campaign_id}", json=body).json()
    if json_output:
        print_json(data)
        return
    print_detail(_with_settings(data), _CAMPAIGN_FIELDS)


def _set_status(campaign_id: str, status: str, json_output: bool) -> bool:
    """Post the status. Answer True when the caller prints the text line."""
    data = _api_request(
        "post", f"{_ENVOY}/campaigns/{campaign_id}/status", json={"status": status}
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
    """Start a new campaign. Its enrollments get their first Run."""
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
        f"{_ENVOY}/campaigns/{campaign_id}/enrollments",
        json={"person_kind": person_kind, "person_id": person_id},
    ).json()
    if json_output:
        print_json(data)
        return
    rprint(styled("[green]Enrollment {} is created.[/green]", data["id"]))
    print_detail(data, _ENROLLMENT_FIELDS)


def _batch_person(raw: str, source: str) -> dict[str, str]:
    """Reads one `kind:id`, or refuses it before any HTTP call."""
    kind, _, person_id = raw.strip().partition(":")
    if kind not in _PERSON_KINDS:
        refuse_local(f"{source} must start with one of: {', '.join(_PERSON_KINDS)}", raw.strip())
    try:
        normalized = str(uuid.UUID(person_id))
    except ValueError:
        refuse_local(f"{source} must end with a person ID (a UUID)", raw.strip())
    return {"person_kind": kind, "person_id": normalized}


def _batch_people(people: list[str], file: Path | None) -> list[dict[str, str]]:
    """Reads the people of the flags, then the lines of the file, in order.

    A person named twice is sent once, at the first place it is named.
    """
    found = [_batch_person(one, "--person") for one in people]
    if file is not None:
        try:
            # utf-8-sig drops the byte order mark that some editors write.
            lines = file.read_text(encoding="utf-8-sig").splitlines()
        except OSError as error:
            refuse_local("--file cannot be read", f"{file} ({error.strerror})")
        except UnicodeDecodeError:
            refuse_local("--file is not UTF-8 text", str(file))
        for number, line in enumerate(lines, start=1):
            text = line.strip()
            if text and not text.startswith("#"):
                found.append(_batch_person(text, f"--file line {number}"))
    unique: dict[tuple[str, str], dict[str, str]] = {}
    for one in found:
        unique.setdefault((one["person_kind"], one["person_id"]), one)
    found = list(unique.values())
    if not found:
        refuse_local("name at least one person with --person or --file")
    if len(found) > _BATCH_MAX:
        refuse_local(f"one batch takes at most {_BATCH_MAX} people", len(found))
    return found


def _batch_row(result: dict) -> dict:
    """Builds the table row of one batch result."""
    outcome = result.get("outcome")
    if outcome == "added":
        detail = f"Enrollment {result.get('enrollment_id')}"
    elif outcome == "already_enrolled":
        name = result.get("campaign_name")
        status = result.get("campaign_status")
        if not name:
            detail = "In another campaign"
        else:
            detail = f'In "{name}" ({status})' if status else f'In "{name}"'

    else:
        detail = _OUTCOME_DETAILS.get(str(outcome), "")
    return {
        "person": f"{result.get('person_kind')}:{result.get('person_id')}",
        "outcome": outcome,
        "detail": detail,
    }


@campaigns_app.command("enroll-batch")
def campaigns_enroll_batch(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    people: list[str] = typer.Option(
        [], "--person", help="kind:id, such as crm.person:<id>. Repeat for each person."
    ),
    file: Path | None = typer.Option(
        None,
        "--file",
        help="A file with one kind:id per line. Blank lines and # comments are skipped.",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Enroll up to 200 people, and print one result per person, in order.

    The people go in requests of 50, one after another. One refused person
    never blocks the others. Each result is added, already_enrolled (in
    another campaign), campaign_full, opted_out or not_found. A person
    already in this campaign answers added. When a request fails, the run
    stops: the table shows the people already sent and marks the rest
    not_sent. A repeat of the run is safe.
    """
    set_json_mode(json_output)
    found = _batch_people(people, file)
    results: list[dict] = []
    try:
        for start in range(0, len(found), _BATCH_CHUNK):
            chunk = found[start : start + _BATCH_CHUNK]
            data = _api_request(
                "post",
                f"{_ENVOY}/campaigns/{campaign_id}/enrollments/batch",
                json={"people": chunk},
            ).json()
            results.extend(data.get("results", []))
    except typer.Exit:
        # The error is printed. In JSON mode it is the whole output.
        if not json_output and results:
            unsent = [{**one, "outcome": "not_sent"} for one in found[len(results) :]]
            _print_batch(results + unsent)
        raise
    if json_output:
        print_json({"results": results})
        return
    _print_batch(results)


def _print_batch(results: list[dict]) -> None:
    """Prints one row per batch result, under the count of the people added."""
    added = sum(1 for one in results if one.get("outcome") == "added")
    print_table(
        [_batch_row(one) for one in results],
        _BATCH_FIELDS,
        title=f"{added} of {len(results)} added",
    )


# Enrollments.


@enrollments_app.command("list")
def enrollments_list(
    campaign_id: str = typer.Option(..., "--campaign-id", help="Campaign ID"),
    status: str | None = typer.Option(None, "--status", help="active, needs_contact_data or ended"),
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
    if status is not None and status not in _ENROLLMENT_STATUSES:
        refuse_local(f"--status must be one of: {', '.join(_ENROLLMENT_STATUSES)}", status)
    if not _PAGE_MIN <= limit <= _ENROLLMENT_PAGE_MAX:
        refuse_local(f"--limit is not between {_PAGE_MIN} and {_ENROLLMENT_PAGE_MAX}", limit)
    if offset < 0:
        refuse_local("--offset may not be negative", offset)
    if search is not None and len(search) > _SEARCH_MAX:
        refuse_local(f"--search is longer than {_SEARCH_MAX} characters", len(search))
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if status is not None:
        params["status"] = status
    if search is not None:
        params["search"] = search
    data = _api_request(
        "get", f"{_ENVOY}/campaigns/{campaign_id}/enrollments", params=params
    ).json()
    if json_output:
        print_json(data)
        return
    rows = [_with_last_action(row) for row in data.get("data", [])]
    total = data.get("total", len(rows))
    shown = f"{offset + 1}-{offset + len(rows)} of {total}" if rows else f"0 of {total}"
    print_table(rows, _ENROLLMENT_LIST_FIELDS, title=f"Envoy enrollments {shown}")
    if data.get("has_more"):
        rprint(styled("[dim]More rows wait: --offset {}[/dim]", offset + len(rows)))


@enrollments_app.command("get")
def enrollments_get(
    enrollment_id: str = typer.Argument(..., help="Enrollment ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Read one enrollment."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_ENVOY}/enrollments/{enrollment_id}").json()
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
        parts = [item.get("type"), item.get("status"), item.get("rationale")]
    elif kind == "action":
        parts = [item.get("type"), item.get("status"), item.get("reject_reason")]
    elif kind == "email":
        parts = [item.get("direction"), item.get("status"), item.get("subject")]
    elif kind == "linkedin_message":
        parts = [item.get("direction"), item.get("text")]
    elif kind == "ended":
        parts = [item.get("ended_reason")]
    else:
        parts = []
    return " · ".join(str(part) for part in parts if part)


@enrollments_app.command("timeline")
def enrollments_timeline(
    enrollment_id: str = typer.Argument(..., help="Enrollment ID"),
    limit: int = typer.Option(
        _PAGE_DEFAULT, "--limit", help="Most rows of each kind, 1 to 100. The newest are kept"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Read the Envoy items of one enrollment, newest first.

    The items are the start, each decision, each proposed action, the thread
    emails, the LinkedIn messages and the end. No CRM activity is in it.
    """
    set_json_mode(json_output)
    if not _PAGE_MIN <= limit <= _PAGE_MAX:
        refuse_local(f"--limit is not between {_PAGE_MIN} and {_PAGE_MAX}", limit)
    data = _api_request(
        "get",
        f"{_ENVOY}/enrollments/{enrollment_id}/timeline",
        params={"limit": limit},
    ).json()
    if json_output:
        print_json(data)
        return
    rows = [{**item, "what": _timeline_text(item)} for item in data.get("items", [])]
    print_table(
        rows,
        _TIMELINE_FIELDS,
        title=f"Envoy timeline: {data.get('campaign_name') or ''} (newest first)",
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
    data = _api_request("post", f"{_ENVOY}/enrollments/{enrollment_id}/evaluate", json=body).json()
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
    """End the enrollment. A draft that waits for review is not sent."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm("End this person's enrollment in the campaign?", abort=True)
    data = _api_request("post", f"{_ENVOY}/enrollments/{enrollment_id}/exit").json()
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
    """Read whether the organization stopped Envoy."""
    set_json_mode(json_output)
    _print_stop(_api_request("get", f"{_ENVOY}/organization").json(), json_output)


@organization_app.command("stop")
def organization_stop(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Stop every Envoy campaign of the organization from planning or sending."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm("Stop Envoy for the whole organization?", abort=True)
    _print_stop(_api_request("post", f"{_ENVOY}/organization/stop").json(), json_output)


@organization_app.command("resume")
def organization_resume(json_output: bool = JSON_OPTION) -> None:
    """Resume Envoy for the organization. Due Runs restart."""
    set_json_mode(json_output)
    _print_stop(_api_request("post", f"{_ENVOY}/organization/resume").json(), json_output)


app.add_typer(drafts_app, name="drafts")
app.add_typer(campaigns_app, name="campaigns")
app.add_typer(enrollments_app, name="enrollments")
app.add_typer(organization_app, name="organization")
