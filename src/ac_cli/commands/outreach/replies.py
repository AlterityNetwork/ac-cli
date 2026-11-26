"""Commands for Outreach replies: `ac agentic outreach replies`.

`list` prints the replies to Outreach messages, the newest first. A reply is
`reply_ready` when Outreach wrote a draft that answers it, and `needs_reply`
when it did not: the person answers it by hand in the Inbox, or marks it
done. `--state replied` and `--state done` read the replies a person dealt
with, and `--since` keeps the ones handled at or after a time. The list also
prints the counts of the Review tab and the people who come due next.

`done <enrollment-id>` marks one `needs_reply` reply done. The API refuses a
reply with a draft (exit 5, `reply_not_open`). With `--reply-message-id`, it
also refuses when a newer reply came (exit 5, `reply_superseded`).
"""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    checked_since,
    refuse_local,
    set_json_mode,
)
from ac_cli.formatting import print_json, print_table, styled

replies_app = typer.Typer(help="List the replies to Outreach messages and mark one done")

_OUTREACH = "/api/v1/agentic/outreach"
_PAGE_DEFAULT = 50
_PAGE_MIN = 1
_PAGE_MAX = 100
_STATES = ("reply_ready", "needs_reply", "replied", "done")

_LIST_FIELDS = [
    ("enrollment_id", "Enrollment ID"),
    ("person_name", "Person"),
    ("campaign_name", "Campaign"),
    ("channel", "Channel"),
    ("state", "State"),
    ("received_at", "Received"),
    ("text", "Reply"),
]


def _flat(item: dict) -> dict:
    """One reply with the person and the campaign names at the top level."""
    person = item.get("person") or {}
    campaign = item.get("campaign") or {}
    return {
        **item,
        "person_name": person.get("name") or item.get("to") or "",
        "campaign_name": campaign.get("name") or "",
    }


def _summary(data: dict) -> None:
    counts = data.get("counts") or {}
    rprint(
        styled(
            "[dim]{} reply ready, {} need your reply, {} drafts to approve[/dim]",
            counts.get("reply_ready", 0),
            counts.get("needs_reply", 0),
            counts.get("drafts", 0),
        )
    )
    for one in data.get("coming_up") or []:
        rprint(
            styled(
                "[dim]{}: {} people due, the first at {}[/dim]",
                one.get("campaign_name") or one.get("campaign_id"),
                one.get("people"),
                one.get("first_at"),
            )
        )


@replies_app.command("list")
def replies_list(
    state: list[str] | None = typer.Option(
        None,
        "--state",
        help="reply_ready, needs_reply, replied or done; repeat for more. "
        "The API default is reply_ready and needs_reply",
    ),
    campaign_id: str | None = typer.Option(None, "--campaign-id", help="Only this campaign"),
    since: str | None = typer.Option(
        None, "--since", help="replied and done only: handled at or after this ISO time"
    ),
    limit: int = typer.Option(_PAGE_DEFAULT, "--limit", help="How many replies, 1 to 100"),
    offset: int = typer.Option(0, "--offset", help="How many replies to skip first"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the replies to Outreach messages, the newest first, with the counts."""
    set_json_mode(json_output)
    for one in state or []:
        if one not in _STATES:
            refuse_local(f"--state must be one of: {', '.join(_STATES)}", one)
    since = checked_since(since)
    if not _PAGE_MIN <= limit <= _PAGE_MAX:
        refuse_local(f"--limit is not between {_PAGE_MIN} and {_PAGE_MAX}", limit)
    if offset < 0:
        refuse_local("--offset may not be negative", offset)
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if state:
        params["state"] = state
    if campaign_id is not None:
        params["campaign_id"] = campaign_id
    if since is not None:
        params["since"] = since
    data = _api_request("get", f"{_OUTREACH}/replies", params=params).json()
    if json_output:
        print_json(data)
        return
    rows = [_flat(item) for item in data.get("data", [])]
    total = data.get("total", len(rows))
    shown = f"{offset + 1}-{offset + len(rows)} of {total}" if rows else f"0 of {total}"
    print_table(rows, _LIST_FIELDS, title=f"Outreach replies {shown}")
    if data.get("has_more"):
        rprint(styled("[dim]More replies wait: --offset {}[/dim]", offset + len(rows)))
    _summary(data)


@replies_app.command("done")
def replies_done(
    enrollment_id: str = typer.Argument(..., help="Enrollment ID of the reply"),
    reply_message_id: str | None = typer.Option(
        None,
        "--reply-message-id",
        help="The message id you saw; a newer reply then refuses the call",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Mark one reply that needs your reply as done."""
    set_json_mode(json_output)
    body: dict[str, object] = {}
    if reply_message_id is not None:
        body["reply_message_id"] = reply_message_id
    data = _api_request("post", f"{_OUTREACH}/replies/{enrollment_id}/done", json=body).json()
    if json_output:
        print_json(data)
        return
    person = (data.get("person") or {}).get("name") or enrollment_id
    rprint(styled("[green]The reply of {} is done.[/green]", person))
