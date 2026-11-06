"""Inbox commands: one row per person, every channel, reply and AI draft.

Every THREAD_ID is an inbox thread id. A command on a person takes any thread
of the person.
"""

from __future__ import annotations

import time

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    refuse_local,
    set_json_mode,
)
from ac_cli.formatting import print_detail, print_json, print_table, styled

_INBOX = "/api/v1/inbox"

app = typer.Typer(help="Inbox: one row per person, reply and AI draft on email and LinkedIn")

_CHANNELS = ("email", "linkedin")
_VIEWS = ("inbox", "done")
_MESSAGE_VIEWS = ("sent", "drafts", "scheduled")
_INTENTS = ("interested", "not_interested", "out_of_office", "none")
_KINDS = ("message", "connection", "engagement")
_STATUSES = ("open", "done", "snoozed")
_BULK_ACTIONS = ("done", "read", "unread")
_PAGE_MAX = 100
# The longest LinkedIn message the API takes.
_LINKEDIN_LIMIT = 1000
# How long `ai-draft --wait` polls, and how often.
_WAIT_SECONDS = 180
_POLL_SECONDS = 2.0


@app.callback()
def callback(ctx: typer.Context) -> None:
    """Inbox commands."""
    ctx.ensure_object(dict)


def _one_of(name: str, value: str | None, allowed: tuple[str, ...]) -> None:
    if value is not None and value not in allowed:
        refuse_local(f"{name} must be one of {', '.join(allowed)}", value)


def _page(limit: int, offset: int) -> None:
    if not 1 <= limit <= _PAGE_MAX:
        refuse_local(f"--limit must be between 1 and {_PAGE_MAX}", limit)
    if offset < 0:
        refuse_local("--offset must be 0 or more", offset)


def _check_body(channel: str, body: str) -> None:
    _one_of("--channel", channel, _CHANNELS)
    if not body.strip():
        refuse_local("--body is empty")
    if channel == "linkedin" and len(body) > _LINKEDIN_LIMIT:
        refuse_local(f"A LinkedIn message holds at most {_LINKEDIN_LIMIT} characters", len(body))


def _print_sent(data: dict) -> None:
    if data.get("status") == "scheduled":
        rprint(
            styled(
                "[yellow]Scheduled[/yellow] {}: sends at {}",
                data.get("communication_id"),
                data.get("sends_at"),
            )
        )
        return
    rprint(styled("[green]Sent[/green] {}", data.get("communication_id")))


@app.command("list")
def inbox_list(
    view: str = typer.Option("inbox", help="inbox or done"),
    owner: str = typer.Option("me", help="me (the default), all, or a user id"),
    channel: list[str] = typer.Option(None, help="email or linkedin (repeat for more)"),
    needs_reply: bool = typer.Option(
        False, "--needs-reply", help="Only people who wait for a reply"
    ),
    unread: bool = typer.Option(False, "--unread", help="Only people with an unread item"),
    intent: list[str] = typer.Option(
        None, help="interested, not_interested, out_of_office or none (repeat for more)"
    ),
    kind: list[str] = typer.Option(
        None, help="message, connection or engagement (repeat for more)"
    ),
    sequence: str | None = typer.Option(None, help="any, none, or a sequence id"),
    since: str | None = typer.Option(None, help="Only activity on or after this date (ISO)"),
    q: str | None = typer.Option(
        None, "--q", help="Search the subject, the sender and the preview"
    ),
    limit: int = typer.Option(50, help="People per page (1 to 100)"),
    offset: int = typer.Option(0, help="People to skip"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List people with inbox conversations, newest activity first."""
    set_json_mode(json_output)
    _one_of("--view", view, _VIEWS)
    for value in channel or []:
        _one_of("--channel", value, _CHANNELS)
    for value in intent or []:
        _one_of("--intent", value, _INTENTS)
    for value in kind or []:
        _one_of("--kind", value, _KINDS)
    _page(limit, offset)
    params: dict = {"view": view, "owner": owner, "limit": limit, "offset": offset}
    if channel:
        params["channel"] = list(channel)
    if intent:
        params["intent"] = list(intent)
    if kind:
        params["kind"] = list(kind)
    if needs_reply:
        params["needs_reply"] = "true"
    if unread:
        params["unread"] = "true"
    for key, value in (("sequence", sequence), ("since", since), ("q", q)):
        if value:
            params[key] = value

    data = _api_request("get", f"{_INBOX}/threads", params=params).json()
    if json_output:
        print_json(data)
        return
    rows = [
        {
            "id": row.get("id"),
            "person": (row.get("person") or {}).get("name"),
            "company": (row.get("person") or {}).get("company_name"),
            "channels": ", ".join(c.get("channel", "") for c in row.get("conversations") or []),
            "needs_reply": "yes" if row.get("needs_reply") else "",
            "unread": "yes" if row.get("unread") else "",
            "intent": row.get("intent"),
            "owner": (row.get("owner") or {}).get("name"),
            "last_activity_at": row.get("last_activity_at"),
        }
        for row in data.get("data", [])
    ]
    print_table(
        rows,
        [
            ("person", "Person"),
            ("company", "Company"),
            ("channels", "Channels"),
            ("needs_reply", "Needs reply"),
            ("unread", "Unread"),
            ("intent", "Intent"),
            ("owner", "Owner"),
            ("last_activity_at", "Last activity"),
            ("id", "ID"),
        ],
        title=f"Inbox ({data.get('total', '?')} people)",
    )


@app.command("messages")
def inbox_messages(
    view: str = typer.Option(..., help="sent, drafts or scheduled"),
    owner: str = typer.Option("me", help="me (the default), all, or a user id"),
    channel: str | None = typer.Option(None, help="email or linkedin"),
    limit: int = typer.Option(50, help="Messages per page (1 to 100)"),
    offset: int = typer.Option(0, help="Messages to skip"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List sent, draft or scheduled messages on every channel."""
    set_json_mode(json_output)
    _one_of("--view", view, _MESSAGE_VIEWS)
    _one_of("--channel", channel, _CHANNELS)
    _page(limit, offset)
    params: dict = {"view": view, "owner": owner, "limit": limit, "offset": offset}
    if channel:
        params["channel"] = channel
    data = _api_request("get", f"{_INBOX}/messages", params=params).json()
    if json_output:
        print_json(data)
        return
    rows = [
        {**row, "person": (row.get("person") or {}).get("name")} for row in data.get("data", [])
    ]
    print_table(
        rows,
        [
            ("channel", "Channel"),
            ("person", "Person"),
            ("subject", "Subject"),
            ("preview", "Preview"),
            ("status", "Status"),
            ("send_scheduled_at", "Sends at"),
            ("communication_date", "Date"),
            ("id", "ID"),
        ],
        title=f"Inbox {view} ({data.get('total', '?')} total)",
    )


@app.command("resolve")
def inbox_resolve(
    message_id: str | None = typer.Option(None, "--message-id", help="An old Messages link id"),
    comm_id: str | None = typer.Option(None, "--comm-id", help="A communication id"),
    contact_id: str | None = typer.Option(None, "--contact-id", help="A CRM person id"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Find the inbox thread of an old link, a message or a CRM person."""
    set_json_mode(json_output)
    params = {
        k: v
        for k, v in (("message_id", message_id), ("comm_id", comm_id), ("contact_id", contact_id))
        if v
    }
    if not params:
        refuse_local("Name one of --message-id, --comm-id or --contact-id")
    data = _api_request("get", f"{_INBOX}/threads/resolve", params=params).json()
    if json_output:
        print_json(data)
        return
    print_detail(data, [("thread_id", "Thread"), ("contact_id", "Person")])


@app.command("show")
def inbox_show(
    thread_id: str = typer.Argument(..., help="Any inbox thread id of the person"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show a person: every conversation in one timeline, and who can reply."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_INBOX}/threads/{thread_id}").json()
    if json_output:
        print_json(data)
        return
    person = data.get("person") or {}
    rprint(
        styled(
            "[bold]{}[/bold]  {}", person.get("name") or "Unknown", person.get("company_name") or ""
        )
    )
    print_table(
        data.get("timeline", []),
        [
            ("sent_at", "Time"),
            ("channel", "Channel"),
            ("kind", "Kind"),
            ("direction", "Direction"),
            ("subject", "Subject"),
            ("text", "Text"),
        ],
        title="Timeline",
    )
    reply = data.get("reply") or {}
    channels = [
        {
            **c,
            "can_reply": "yes" if c.get("can_reply") else "no",
            "owner": (c.get("owner") or {}).get("name"),
        }
        for c in reply.get("channels", [])
    ]
    print_table(
        channels,
        [
            ("channel", "Channel"),
            ("can_reply", "Can reply"),
            ("reason", "Reason"),
            ("owner", "Owner"),
            ("account_label", "Account"),
        ],
        title=f"Reply (starts on {reply.get('default_channel') or '?'})",
    )


def _print_changed(data: dict, json_output: bool, message: str) -> None:
    if json_output:
        print_json(data)
        return
    rprint(styled("[green]{}[/green] ({} conversations)", message, len(data.get("thread_ids", []))))


@app.command("read")
def inbox_read(
    thread_id: str = typer.Argument(..., help="Any inbox thread id of the person"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Mark every message of the person read, for you only."""
    set_json_mode(json_output)
    data = _api_request("post", f"{_INBOX}/threads/{thread_id}/read").json()
    _print_changed(data, json_output, "Marked read")


@app.command("unread")
def inbox_unread(
    thread_id: str = typer.Argument(..., help="Any inbox thread id of the person"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Mark the newest message of each conversation unread, for you only."""
    set_json_mode(json_output)
    data = _api_request("post", f"{_INBOX}/threads/{thread_id}/unread").json()
    _print_changed(data, json_output, "Marked unread")


@app.command("status")
def inbox_status(
    thread_id: str = typer.Argument(..., help="Any inbox thread id of the person"),
    status: str = typer.Option(..., help="open, done or snoozed"),
    until: str | None = typer.Option(None, help="The end of a snooze (ISO time)"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Set done, open or snoozed on every conversation of the person, for everyone."""
    set_json_mode(json_output)
    _one_of("--status", status, _STATUSES)
    if status == "snoozed" and not until:
        refuse_local("--until is required to snooze")
    body = _build_body(status=status, snoozed_until=until if status == "snoozed" else None)
    data = _api_request("post", f"{_INBOX}/threads/{thread_id}/status", json=body).json()
    _print_changed(data, json_output, f"Status {status}")


@app.command("intent")
def inbox_intent(
    thread_id: str = typer.Argument(..., help="Any inbox thread id of the person"),
    intent: str = typer.Option(..., help="interested, not_interested, out_of_office or none"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Set the intent of the person. `none` clears it."""
    set_json_mode(json_output)
    _one_of("--intent", intent, _INTENTS)
    body = {"intent": None if intent == "none" else intent}
    data = _api_request("post", f"{_INBOX}/threads/{thread_id}/intent", json=body).json()
    _print_changed(data, json_output, f"Intent {intent}")


@app.command("bulk")
def inbox_bulk(
    ids: str = typer.Option(..., "--ids", help="Comma-separated inbox thread ids"),
    action: str = typer.Option(..., help="done, read or unread"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Mark several people done, read or unread."""
    set_json_mode(json_output)
    _one_of("--action", action, _BULK_ACTIONS)
    thread_ids = [i.strip() for i in ids.split(",") if i.strip()]
    if not thread_ids:
        refuse_local("--ids names no thread")
    body = {"thread_ids": thread_ids, "action": action}
    data = _api_request("post", f"{_INBOX}/threads/bulk", json=body).json()
    _print_changed(data, json_output, f"Bulk {action}")


@app.command("reply")
def inbox_reply(
    thread_id: str = typer.Argument(..., help="Any inbox thread id of the person"),
    channel: str = typer.Option(..., help="email or linkedin"),
    body: str = typer.Option(..., help="The message text"),
    subject: str | None = typer.Option(
        None, help="Email only. Default: Re: and the thread subject"
    ),
    cc: str | None = typer.Option(None, help="Email only. Comma-separated addresses"),
    bcc: str | None = typer.Option(None, help="Email only. Comma-separated addresses"),
    send_at: str | None = typer.Option(None, "--send-at", help="Email only. Schedule (ISO time)"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Reply to the person from the owner's account.

    Only the owner of the connected account replies. A LinkedIn reply counts
    against the daily message budget and waits for the send window.
    """
    set_json_mode(json_output)
    _check_body(channel, body)
    payload = _build_body(
        channel=channel,
        body_text=body,
        subject=subject,
        cc_emails=[a.strip() for a in cc.split(",")] if cc else None,
        bcc_emails=[a.strip() for a in bcc.split(",")] if bcc else None,
        send_at=send_at,
    )
    data = _api_request("post", f"{_INBOX}/threads/{thread_id}/reply", json=payload).json()
    if json_output:
        print_json(data)
        return
    _print_sent(data)


@app.command("send")
def inbox_send(
    contact_id: str = typer.Option(..., "--contact-id", help="The CRM person id"),
    channel: str = typer.Option(..., help="email or linkedin"),
    body: str = typer.Option(..., help="The message text"),
    subject: str | None = typer.Option(None, help="Email only. Required for email"),
    cc: str | None = typer.Option(None, help="Email only. Comma-separated addresses"),
    bcc: str | None = typer.Option(None, help="Email only. Comma-separated addresses"),
    send_at: str | None = typer.Option(None, "--send-at", help="Email only. Schedule (ISO time)"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Send a first message to a CRM person from your own account."""
    set_json_mode(json_output)
    _check_body(channel, body)
    payload = _build_body(
        contact_id=contact_id,
        channel=channel,
        subject=subject,
        body_text=body,
        cc_emails=[a.strip() for a in cc.split(",")] if cc else None,
        bcc_emails=[a.strip() for a in bcc.split(",")] if bcc else None,
        send_at=send_at,
    )
    data = _api_request("post", f"{_INBOX}/messages", json=payload).json()
    if json_output:
        print_json(data)
        return
    _print_sent(data)


@app.command("ai-draft")
def inbox_ai_draft(
    thread_id: str = typer.Argument(..., help="Any inbox thread id of the person"),
    channel: str = typer.Option(..., help="email or linkedin"),
    regenerate: bool = typer.Option(False, "--regenerate", help="Write a new draft"),
    wait: bool = typer.Option(False, "--wait", help="Wait for the draft and print it"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Start an AI draft of a reply. The draft never sends."""
    set_json_mode(json_output)
    _one_of("--channel", channel, _CHANNELS)
    params = {"regenerate": "true"} if regenerate else None
    started = _api_request(
        "post",
        f"{_INBOX}/threads/{thread_id}/ai-draft",
        json={"channel": channel},
        params=params,
    ).json()
    draft_id = started.get("draft_id")
    if not wait:
        if json_output:
            print_json(started)
        else:
            rprint(styled("Draft started: {}", draft_id))
        return
    deadline = time.monotonic() + _WAIT_SECONDS
    data = started
    while True:
        data = _api_request("get", f"{_INBOX}/ai-drafts/{draft_id}").json()
        if data.get("status") != "pending" or time.monotonic() >= deadline:
            break
        time.sleep(_POLL_SECONDS)
    if json_output:
        print_json(data)
        return
    if data.get("status") == "ready":
        if data.get("subject"):
            rprint(styled("[bold]Subject:[/bold] {}", data.get("subject")))
        rprint(styled("{}", data.get("body") or ""))
        return
    rprint(styled("Draft {}: {} {}", draft_id, data.get("status"), data.get("reason") or ""))


@app.command("ask-to-reply")
def inbox_ask_to_reply(
    thread_id: str = typer.Argument(..., help="Any inbox thread id of the person"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Ask the owner of the conversation to reply."""
    set_json_mode(json_output)
    data = _api_request("post", f"{_INBOX}/threads/{thread_id}/ask-to-reply").json()
    if json_output:
        print_json(data)
        return
    rprint(styled("[green]Asked[/green] {} to reply", data.get("owner_user_id")))


@app.command("counts")
def inbox_counts(json_output: bool = JSON_OPTION) -> None:
    """Show the inbox badge figures for your own conversations."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_INBOX}/counts").json()
    if json_output:
        print_json(data)
        return
    print_detail(
        data,
        [("badge", "Badge"), ("needs_reply", "People waiting"), ("unread", "People unread")],
    )
