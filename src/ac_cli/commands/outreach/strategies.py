"""Commands for Outreach strategies: `ac agentic outreach strategies`.

A strategy is the reusable goal, offer, angle and research tools that a
campaign follows. `list` prints the live strategies by name, and
`--include-archived` adds the archived ones. Each strategy prints
`used_by_campaigns`: its live (active or paused) campaigns.

`templates` prints the ready-made strategies from Corbel. `create
--from-template <key>` copies one into the organization, with an optional
`--name` and `--offer-id`; the copy is a normal strategy.

`update` sends only the given options. A change of the goal, the offer, the
angle, the tools or the cap adds 1 to the version. The name and the examples
keep it. `--no-offer`, `--default-cap`, `--no-tools` and `--no-examples` clear
a field. `archive` frees the name. The API refuses it while a live campaign
follows the strategy (exit 5, `strategy_in_use`).
"""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    refuse_local,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.formatting import print_detail, print_json, print_table, styled

strategies_app = typer.Typer(help="Create, edit and archive Outreach strategies")

_OUTREACH = "/api/v1/agentic/outreach"
_PAGE_DEFAULT = 50
_PAGE_MIN = 1
_PAGE_MAX = 100
_NAME_MAX = 200
_GOAL_MAX = 2000
_ANGLE_MAX = 4000
_EXAMPLES_MAX = 5
_EXAMPLE_MAX = 4000
RESEARCH_TOOLS = (
    "research.fetch_page",
    "research.search_web",
    "research.detect_technologies",
    "research.search_company",
)

_LIST_FIELDS = [
    ("id", "Strategy ID"),
    ("name", "Name"),
    ("offer_name", "Offer"),
    ("used_by_campaigns", "Campaigns"),
    ("version", "Version"),
    ("archived_at", "Archived"),
]
_TEMPLATE_FIELDS = [
    ("key", "Key"),
    ("name", "Name"),
    ("goal", "Goal"),
    ("tools", "Research tools"),
    ("angle", "Opens with"),
]
_FIELDS = [
    ("id", "Strategy ID"),
    ("name", "Name"),
    ("goal", "Goal"),
    ("offer_name", "Offer"),
    ("offer_id", "Offer ID"),
    ("angle", "Angle"),
    ("tools", "Research tools"),
    ("max_research_cents", "Max research cents"),
    ("examples", "Example messages"),
    ("used_by_campaigns", "Used by campaigns"),
    ("version", "Version"),
    ("archived_at", "Archived"),
    ("updated_at", "Updated"),
]


def _cells(strategy: dict) -> dict:
    """Adds the tool and example cells to one strategy."""
    tools = strategy.get("research_tools")
    examples = strategy.get("example_messages")
    return {
        **strategy,
        "tools": ", ".join(str(one) for one in tools) if tools else "none",
        "examples": " | ".join(str(one) for one in examples) if examples else "",
    }


def _check_text(option: str, value: str | None, most: int) -> None:
    if value is not None and len(value) > most:
        refuse_local(f"{option} is longer than {most} characters", len(value))


def _strategy_body(
    *,
    name: str | None,
    goal: str | None,
    offer_id: str | None,
    angle: str | None,
    tools: list[str] | None,
    examples: list[str] | None,
    max_research_cents: int | None,
) -> dict[str, object]:
    """Build a strategy body from the given options.

    The checks mirror the API, so a bad value is refused before any call.
    """
    if name is not None and not name.strip():
        refuse_local("--name may not be blank")
    _check_text("--name", name, _NAME_MAX)
    if goal is not None and goal and not goal.strip():
        refuse_local("--goal may not be only spaces")
    _check_text("--goal", goal, _GOAL_MAX)
    _check_text("--angle", angle, _ANGLE_MAX)
    for tool in tools or []:
        if tool not in RESEARCH_TOOLS:
            refuse_local(f"--tool must be one of: {', '.join(RESEARCH_TOOLS)}", tool)
    if examples is not None and len(examples) > _EXAMPLES_MAX:
        refuse_local(f"--example takes at most {_EXAMPLES_MAX} messages", len(examples))
    for example in examples or []:
        if not example.strip():
            refuse_local("--example may not be blank")
        _check_text("--example", example, _EXAMPLE_MAX)
    if max_research_cents is not None and max_research_cents < 0:
        refuse_local("--max-research-cents may not be negative", max_research_cents)
    return {
        key: value
        for key, value in (
            ("name", name),
            ("goal", goal),
            ("offer_id", offer_id),
            ("angle", angle),
            ("research_tools", tools or None),
            ("example_messages", examples or None),
            ("max_research_cents", max_research_cents),
        )
        if value is not None
    }


_GOAL_OPTION = typer.Option(
    None, "--goal", help='What counts as success, such as "Book a 20 min intro call"'
)
_OFFER_OPTION = typer.Option(
    None, "--offer-id", help="The playbook (Settings > Offers) that every message leads to"
)
_ANGLE_OPTION = typer.Option(
    None,
    "--angle",
    help="What Outreach researches, what it opens with, and what to do on no finding",
)
_TOOL_OPTION = typer.Option(
    None,
    "--tool",
    help=f"A research tool: {', '.join(RESEARCH_TOOLS)}. Repeat for more",
)
_EXAMPLE_OPTION = typer.Option(
    None, "--example", help="An example message that shows the tone. Repeat, up to 5"
)
_CAP_OPTION = typer.Option(
    None,
    "--max-research-cents",
    help="The most that the research of one person costs, in cents",
)


@strategies_app.command("list")
def strategies_list(
    include_archived: bool = typer.Option(
        False, "--include-archived", help="Also list the archived strategies"
    ),
    limit: int = typer.Option(_PAGE_DEFAULT, "--limit", help="How many strategies, 1 to 100"),
    offset: int = typer.Option(0, "--offset", help="How many strategies to skip first"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the strategies by name, one page at a time."""
    set_json_mode(json_output)
    if not _PAGE_MIN <= limit <= _PAGE_MAX:
        refuse_local(f"--limit is not between {_PAGE_MIN} and {_PAGE_MAX}", limit)
    if offset < 0:
        refuse_local("--offset may not be negative", offset)
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if include_archived:
        params["include_archived"] = "true"
    data = _api_request("get", f"{_OUTREACH}/strategies", params=params).json()
    if json_output:
        print_json(data)
        return
    rows = [_cells(item) for item in data.get("items", [])]
    total = data.get("total", len(rows))
    shown = f"{offset + 1}-{offset + len(rows)} of {total}" if rows else f"0 of {total}"
    print_table(rows, _LIST_FIELDS, title=f"Outreach strategies {shown}")
    if data.get("has_more"):
        rprint(styled("[dim]More strategies wait: --offset {}[/dim]", offset + len(rows)))


@strategies_app.command("get")
def strategies_get(
    strategy_id: str = typer.Argument(..., help="Strategy ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Read one strategy, live or archived."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_OUTREACH}/strategies/{strategy_id}").json()
    if json_output:
        print_json(data)
        return
    print_detail(_cells(data), _FIELDS)


@strategies_app.command("templates")
def strategies_templates(json_output: bool = JSON_OPTION) -> None:
    """List the ready-made strategies from Corbel. Copy one with `create --from-template`."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_OUTREACH}/strategy-templates").json()
    if json_output:
        print_json(data)
        return
    rows = [_cells(item) for item in data.get("items", [])]
    print_table(rows, _TEMPLATE_FIELDS, title=f"Outreach strategy templates ({len(rows)})")


def _create_from_template(
    key: str, *, name: str | None, offer_id: str | None, json_output: bool
) -> None:
    """Copy one template into the strategies of the organization."""
    if name is not None and not name.strip():
        refuse_local("--name may not be blank")
    _check_text("--name", name, _NAME_MAX)
    body = {field: value for field, value in (("name", name), ("offer_id", offer_id)) if value}
    data = _api_request("post", f"{_OUTREACH}/strategy-templates/{key}/copy", json=body).json()
    if json_output:
        print_json(data)
        return
    rprint(styled("[green]Strategy {} is created from {}.[/green]", data["id"], key))
    print_detail(_cells(data), _FIELDS)


@strategies_app.command("create")
def strategies_create(
    name: str | None = typer.Option(
        None,
        "--name",
        help="Strategy name, unique among the live ones. Required without --from-template",
    ),
    from_template: str | None = typer.Option(
        None,
        "--from-template",
        help="Copy a ready-made strategy (see `templates`), such as new-funding",
    ),
    goal: str | None = _GOAL_OPTION,
    offer_id: str | None = _OFFER_OPTION,
    angle: str | None = _ANGLE_OPTION,
    tools: list[str] | None = _TOOL_OPTION,
    examples: list[str] | None = _EXAMPLE_OPTION,
    max_research_cents: int | None = _CAP_OPTION,
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a strategy. Only `--name` is required.

    No `--tool` means no research: Outreach reads the CRM record and signals
    only. No cap takes the API default. With `--from-template`, only `--name`
    and `--offer-id` may change the copy.
    """
    set_json_mode(json_output)
    if from_template is not None:
        given = [
            flag
            for flag, value in (
                ("--goal", goal),
                ("--angle", angle),
                ("--tool", tools),
                ("--example", examples),
                ("--max-research-cents", max_research_cents),
            )
            if value is not None and value != []
        ]
        if given:
            refuse_local(f"--from-template takes only --name and --offer-id, not {given[0]}")
        _create_from_template(from_template, name=name, offer_id=offer_id, json_output=json_output)
        return
    if name is None:
        refuse_local("give --name, or --from-template")
    body = _strategy_body(
        name=name,
        goal=goal,
        offer_id=offer_id,
        angle=angle,
        tools=tools,
        examples=examples,
        max_research_cents=max_research_cents,
    )
    data = _api_request("post", f"{_OUTREACH}/strategies", json=body).json()
    if json_output:
        print_json(data)
        return
    rprint(styled("[green]Strategy {} is created.[/green]", data["id"]))
    print_detail(_cells(data), _FIELDS)


@strategies_app.command("update")
def strategies_update(
    strategy_id: str = typer.Argument(..., help="Strategy ID"),
    name: str | None = typer.Option(None, "--name", help="Strategy name"),
    goal: str | None = _GOAL_OPTION,
    offer_id: str | None = _OFFER_OPTION,
    no_offer: bool = typer.Option(False, "--no-offer", help="Clear the offer: every offer"),
    angle: str | None = _ANGLE_OPTION,
    tools: list[str] | None = _TOOL_OPTION,
    no_tools: bool = typer.Option(False, "--no-tools", help="Clear the tools: no research"),
    examples: list[str] | None = _EXAMPLE_OPTION,
    no_examples: bool = typer.Option(False, "--no-examples", help="Clear the examples"),
    max_research_cents: int | None = _CAP_OPTION,
    default_cap: bool = typer.Option(
        False, "--default-cap", help="Clear the cap: the API default applies"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Edit a strategy. `--tool` and `--example` replace the whole list.

    A change of the goal, the offer, the angle, the tools or the cap adds 1
    to the version. An empty `--goal` or `--angle` clears it.
    """
    set_json_mode(json_output)
    for flag, value, clear, clear_flag in (
        ("--offer-id", offer_id, no_offer, "--no-offer"),
        ("--tool", tools, no_tools, "--no-tools"),
        ("--example", examples, no_examples, "--no-examples"),
        ("--max-research-cents", max_research_cents, default_cap, "--default-cap"),
    ):
        if value is not None and value != [] and clear:
            refuse_local(f"give {flag} or {clear_flag}, not both")
    body = _strategy_body(
        name=name,
        goal=goal,
        offer_id=offer_id,
        angle=angle,
        tools=tools,
        examples=examples,
        max_research_cents=max_research_cents,
    )
    if no_offer:
        body["offer_id"] = None
    if default_cap:
        body["max_research_cents"] = None
    if no_tools:
        body["research_tools"] = []
    if no_examples:
        body["example_messages"] = []
    if not body:
        refuse_local("nothing to update: give at least one option")
    data = _api_request("patch", f"{_OUTREACH}/strategies/{strategy_id}", json=body).json()
    if json_output:
        print_json(data)
        return
    print_detail(_cells(data), _FIELDS)


@strategies_app.command("archive")
def strategies_archive(
    strategy_id: str = typer.Argument(..., help="Strategy ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Archive a strategy. No live campaign may follow it."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm("Archive the strategy? New campaigns can no longer pick it.", abort=True)
    data = _api_request("post", f"{_OUTREACH}/strategies/{strategy_id}/archive").json()
    if json_output:
        print_json(data)
        return
    rprint(styled("[yellow]Strategy {} is archived.[/yellow]", strategy_id))
