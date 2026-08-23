"""Agentic platform commands.

`ac agentic runs` drives the run surface of the new agentic platform, and
`ac agentic definitions` drives the definition lifecycle. Both sit beside the
live `ac agents runs` and replace none of it: the two stacks are branch
isolated until the cutover, so the alias and the deletion of the old commands
belong to Phase 7.

Every platform route sits under `/api/v1/agentic/`, so one path constant serves
both groups and the parity audit resolves each call.

The endpoints are ac-docs, the file
engineering/system-design/agentic-platform/interfaces/surfaces.md, Run Explorer
and Agent Builder.
"""

from __future__ import annotations

import json
import uuid

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.formatting import print_detail, print_json, print_table

app = typer.Typer(help="Agentic platform")

_AGENTIC = "/api/v1/agentic"

runs_app = typer.Typer(help="Agentic run operations")


@app.callback()
def agentic_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


def _parse_input(input_json: str | None) -> dict:
    """Reads the --input flag, or answers an empty body.

    Args:
        input_json: The JSON string the caller passed, or None.

    Returns:
        The parsed input.

    Raises:
        typer.Exit: The string is not JSON.
    """
    if not input_json:
        return {}
    try:
        parsed = json.loads(input_json)
    except json.JSONDecodeError:
        rprint("[red]Invalid JSON for --input[/red]")
        raise typer.Exit(code=1) from None
    if not isinstance(parsed, dict):
        rprint("[red]--input must be a JSON object[/red]")
        raise typer.Exit(code=1)
    return parsed


_RUN_FIELDS = [
    ("id", "Run ID"),
    ("kind", "Kind"),
    ("definition_name", "Definition"),
    ("status", "Status"),
    ("waiting_on", "Waiting on"),
    ("source", "Source"),
    ("child_count", "Children"),
    ("created_at", "Created"),
    ("started_at", "Started"),
    ("ended_at", "Ended"),
]

_LIST_FIELDS = [
    ("id", "Run ID"),
    ("definition_name", "Definition"),
    ("status", "Status"),
    ("kind", "Kind"),
    ("created_at", "Created"),
]

_SPAN_FIELDS = [
    ("span_id", "Span ID"),
    ("kind", "Kind"),
    ("name", "Name"),
    ("status", "Status"),
    ("duration_ms", "Duration (ms)"),
    ("started_at", "Started"),
]


@runs_app.command("start")
def runs_start(
    ctx: typer.Context,
    definition_id: str = typer.Option(
        ..., "--definition", help="Definition to run (agent or workflow)"
    ),
    input_json: str | None = typer.Option(None, "--input", help="Input JSON string"),
    idempotency_key: str | None = typer.Option(
        None,
        "--idempotency-key",
        help="Delivery identity of this start. A fresh one is minted when it is not given.",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Start a run of one definition."""
    set_json_mode(json_output)
    body = {"definition_id": definition_id, "input": _parse_input(input_json)}
    # A fresh key per invocation, and never a stable one. The key names the
    # delivery, so a value derived from the command would make tomorrow's run a
    # duplicate of today's and it would never execute.
    key = idempotency_key or str(uuid.uuid4())

    resp = _api_request("post", f"{_AGENTIC}/runs", json=body, headers={"Idempotency-Key": key})

    data = resp.json()
    if json_output:
        print_json(data)
        return
    outcome = data.get("outcome")
    if outcome == "duplicate":
        rprint(
            f"[yellow]Duplicate:[/yellow] this key already started "
            f"{data['id']} (status: {data['status']})"
        )
        return
    rprint(
        f"[green]Run started:[/green] {data['id']} "
        f"({data['definition_name']}, status: {data['status']})"
    )


@runs_app.command("get")
def runs_get(
    ctx: typer.Context,
    run_id: str = typer.Argument(..., help="Run ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get one agentic run by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_AGENTIC}/runs/{run_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, _RUN_FIELDS)
    usage = data.get("usage") or {}
    rprint(
        f"[dim]Tree usage:[/dim] {usage.get('total_tokens', 0)} tokens, "
        f"{usage.get('cost_cents', 0)} cents"
    )
    if data.get("child_count"):
        rprint(f"[dim]Read the children:[/dim] ac agentic runs list --parent {run_id}")


@runs_app.command("list")
def runs_list(
    ctx: typer.Context,
    parent: str | None = typer.Option(None, "--parent", help="Children of one run"),
    definition_id: str | None = typer.Option(None, "--definition", help="Runs of one definition"),
    status: str | None = typer.Option(None, "--status", help="Runs in one status"),
    every: bool = typer.Option(
        False, "--all", help="Include child runs. The default returns roots only."
    ),
    cursor: str | None = typer.Option(None, "--cursor", help="Page to continue"),
    limit: int = typer.Option(50, help="Page size"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List agentic runs. It returns the top of each tree by default."""
    set_json_mode(json_output)
    params: dict = {"limit": limit}
    # root_only is unset unless --all names it. The endpoint reads roots by
    # default and children when a parent is named, so sending it would refuse
    # the --parent case with a 400.
    if every:
        params["root_only"] = "false"
    if parent:
        params["parent_run_id"] = parent
    if definition_id:
        params["definition_id"] = definition_id
    if status:
        params["status"] = status
    if cursor:
        params["cursor"] = cursor

    resp = _api_request("get", f"{_AGENTIC}/runs", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("items", [])
    print_table(items, _LIST_FIELDS, title=f"Runs ({len(items)})")
    if data.get("next_cursor"):
        rprint(f"[dim]Next page:[/dim] --cursor {data['next_cursor']}")


@runs_app.command("spans")
def runs_spans(
    ctx: typer.Context,
    run_id: str = typer.Argument(..., help="Run ID"),
    cursor: str | None = typer.Option(None, "--cursor", help="Page to continue"),
    limit: int = typer.Option(50, help="Page size"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the spans of one run.

    It reads the spans of that run alone. A child run holds its own spans, so
    open the child to read them.
    """
    set_json_mode(json_output)
    params: dict = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    resp = _api_request("get", f"{_AGENTIC}/runs/{run_id}/spans", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("items", [])
    print_table(items, _SPAN_FIELDS, title=f"Spans ({len(items)})")
    if data.get("next_cursor"):
        rprint(f"[dim]Next page:[/dim] --cursor {data['next_cursor']}")


@runs_app.command("cancel")
def runs_cancel(
    ctx: typer.Context,
    run_id: str = typer.Argument(..., help="Run ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Cancel one run and its descendants.

    Cancel is idempotent. Cancelling a finished run is still a success, and the
    answer carries the status the run produced.
    """
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Cancel agentic run {run_id} and its children?", abort=True)

    resp = _api_request("post", f"{_AGENTIC}/runs/{run_id}/cancel")

    data = resp.json()
    if json_output:
        print_json(data)
        return
    rprint(f"[green]Cancel requested:[/green] {data['id']} (status: {data['status']})")


app.add_typer(runs_app, name="runs")


definitions_app = typer.Typer(help="Agentic definition lifecycle")

_DEFINITION_FIELDS = [
    ("id", "Definition ID"),
    ("kind", "Kind"),
    ("name", "Name"),
    ("origin", "Origin"),
    ("state", "State"),
    ("has_unpublished_changes", "Unpublished edits"),
    ("source_definition_id", "Forked from"),
    ("created_at", "Created"),
    ("published_at", "Published"),
    ("updated_at", "Token"),
]

_DEFINITION_LIST_FIELDS = [
    ("id", "Definition ID"),
    ("name", "Name"),
    ("kind", "Kind"),
    ("origin", "Origin"),
    ("state", "State"),
    ("has_unpublished_changes", "Unpublished edits"),
]


def _parse_object(raw: str | None, flag: str) -> dict:
    """Reads one JSON object flag, or answers an empty object.

    Args:
        raw: The JSON string the caller passed, or None.
        flag: The flag name, for the message.

    Returns:
        The parsed object.

    Raises:
        typer.Exit: The string is not a JSON object.
    """
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        rprint(f"[red]Invalid JSON for {flag}[/red]")
        raise typer.Exit(code=1) from None
    if not isinstance(parsed, dict):
        rprint(f"[red]{flag} must be a JSON object[/red]")
        raise typer.Exit(code=1)
    return parsed


def _report_validation(data: dict) -> None:
    """Prints what validation found, when the route ran one.

    The answer of a draft save is advisory: the draft saved whatever it says.
    The errors are what tell the author what is still missing.

    Args:
        data: The definition the endpoint answered.
    """
    validation = data.get("validation")
    if validation is None:
        return
    if validation.get("ok"):
        rprint("[green]Validation:[/green] the configuration is valid")
        return
    rprint("[yellow]Validation:[/yellow] the configuration cannot publish yet")
    for one in validation.get("issues", []):
        where = f" at {one['path']}" if one.get("path") else ""
        rprint(f"  [dim]{one['code']}[/dim]{where}: {one['message']}")


@definitions_app.command("list")
def definitions_list(
    ctx: typer.Context,
    kind: str | None = typer.Option(None, "--kind", help="agent, workflow or skill"),
    origin: str | None = typer.Option(None, "--origin", help="platform or custom"),
    state: str | None = typer.Option(None, "--state", help="draft, active or disabled"),
    cursor: str | None = typer.Option(None, "--cursor", help="Page to continue"),
    limit: int = typer.Option(50, help="Page size"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the definitions this organization may see.

    The page carries your own definitions in every state, plus the platform
    templates that are active. A fork starts from a template.
    """
    set_json_mode(json_output)
    params: dict = {"limit": limit}
    if kind:
        params["kind"] = kind
    if origin:
        params["origin"] = origin
    if state:
        params["state"] = state
    if cursor:
        params["cursor"] = cursor

    resp = _api_request("get", f"{_AGENTIC}/definitions", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("items", [])
    print_table(items, _DEFINITION_LIST_FIELDS, title=f"Definitions ({len(items)})")
    if data.get("next_cursor"):
        rprint(f"[dim]Next page:[/dim] --cursor {data['next_cursor']}")


@definitions_app.command("create")
def definitions_create(
    ctx: typer.Context,
    kind: str = typer.Option(..., "--kind", help="agent, workflow or skill"),
    name: str = typer.Option(..., "--name", help="What an admin calls it"),
    config: str | None = typer.Option(
        None, "--config", help="Starting configuration, as a JSON object"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create one draft.

    A new draft may be incomplete. `patch` reports what is still missing on
    every save, and `publish` runs the full validation.
    """
    set_json_mode(json_output)
    body = {"kind": kind, "name": name, "config": _parse_object(config, "--config")}

    resp = _api_request("post", f"{_AGENTIC}/definitions", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
        return
    rprint(f"[green]Draft created:[/green] {data['id']} ({data['name']}, {data['kind']})")


@definitions_app.command("get")
def definitions_get(
    ctx: typer.Context,
    definition_id: str = typer.Argument(..., help="Definition ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get one definition of this organization.

    A platform template answers 404 here. It is visible through `list` and
    through `fork`.
    """
    set_json_mode(json_output)
    resp = _api_request("get", f"{_AGENTIC}/definitions/{definition_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, _DEFINITION_FIELDS)
    if data.get("has_unpublished_changes"):
        rprint("[dim]The draft differs from what is published.[/dim]")


@definitions_app.command("patch")
def definitions_patch(
    ctx: typer.Context,
    definition_id: str = typer.Argument(..., help="Definition ID"),
    expected_updated_at: str = typer.Option(
        ...,
        "--expected-updated-at",
        help="The token the last read returned. Send it back unchanged.",
    ),
    patch: str = typer.Option(..., "--patch", help="The fields to replace, as a JSON object"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Replace the named fields of one draft.

    The patch replaces each named field whole, and an explicit null clears one.
    A merge cannot remove a tool, so send the whole list when you shorten it.

    The token is opaque. Echo back the `updated_at` a read returned, and never
    a value a date type has parsed: a millisecond round trip answers stale.
    """
    set_json_mode(json_output)
    body = {
        "expected_updated_at": expected_updated_at,
        "patch": _parse_object(patch, "--patch"),
    }

    resp = _api_request("patch", f"{_AGENTIC}/definitions/{definition_id}/draft", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
        return
    rprint(f"[green]Draft saved:[/green] {data['id']}")
    _report_validation(data)


@definitions_app.command("validate")
def definitions_validate(
    ctx: typer.Context,
    definition_id: str = typer.Argument(..., help="Definition ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Validate one draft, and write nothing."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_AGENTIC}/definitions/{definition_id}/validate")

    data = resp.json()
    if json_output:
        print_json(data)
        return
    _report_validation(data)


@definitions_app.command("publish")
def definitions_publish(
    ctx: typer.Context,
    definition_id: str = typer.Argument(..., help="Definition ID"),
    expected_updated_at: str = typer.Option(
        ...,
        "--expected-updated-at",
        help="The token the last read returned. Send it back unchanged.",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Make the stored draft the runnable configuration.

    New runs use it. A run already in flight keeps its frozen snapshot.
    """
    set_json_mode(json_output)
    body = {"expected_updated_at": expected_updated_at}

    resp = _api_request("post", f"{_AGENTIC}/definitions/{definition_id}/publish", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
        return
    rprint(f"[green]Published:[/green] {data['id']} (state: {data['state']})")


@definitions_app.command("disable")
def definitions_disable(
    ctx: typer.Context,
    definition_id: str = typer.Argument(..., help="Definition ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Refuse new run trees of one definition.

    It is not a stop button. A workflow already running still starts its child
    runs. Cancel a run with `ac agentic runs cancel`.
    """
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Refuse new runs of definition {definition_id}?", abort=True)

    resp = _api_request("post", f"{_AGENTIC}/definitions/{definition_id}/disable")

    data = resp.json()
    if json_output:
        print_json(data)
        return
    rprint(f"[green]Disabled:[/green] {data['id']} (state: {data['state']})")


@definitions_app.command("enable")
def definitions_enable(
    ctx: typer.Context,
    definition_id: str = typer.Argument(..., help="Definition ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Return one disabled definition to service.

    It revalidates first. A definition this one references may have been
    disabled while this one was off.
    """
    set_json_mode(json_output)
    resp = _api_request("post", f"{_AGENTIC}/definitions/{definition_id}/enable")

    data = resp.json()
    if json_output:
        print_json(data)
        return
    rprint(f"[green]Enabled:[/green] {data['id']} (state: {data['state']})")


@definitions_app.command("fork")
def definitions_fork(
    ctx: typer.Context,
    definition_id: str = typer.Argument(..., help="Template to copy"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Copy one template into this organization as a draft.

    A fork of a platform template copies everything it references, and rewrites
    every id. Two calls mint two independent copies.
    """
    set_json_mode(json_output)
    resp = _api_request("post", f"{_AGENTIC}/definitions/{definition_id}/fork")

    data = resp.json()
    if json_output:
        print_json(data)
        return
    rprint(f"[green]Forked:[/green] {data['id']} ({data['name']}, {data['state']})")


@definitions_app.command("delete")
def definitions_delete(
    ctx: typer.Context,
    definition_id: str = typer.Argument(..., help="Draft to remove"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Remove one draft.

    A draft is the only row that deletes. A published definition is disabled,
    because a run's audit trail must not be deletable from under it.
    """
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete draft {definition_id}?", abort=True)

    _api_request("delete", f"{_AGENTIC}/definitions/{definition_id}")

    if json_output:
        print_json({"id": definition_id, "deleted": True})
        return
    rprint(f"[green]Draft deleted:[/green] {definition_id}")


app.add_typer(definitions_app, name="definitions")
