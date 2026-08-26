"""Agentic platform commands.

`ac agentic runs` drives the run surface of the new agentic platform,
`ac agentic definitions` drives the definition lifecycle,
`ac agentic tools` reads the catalogue a definition names its tools from,
`ac agentic approvals` answers a run that stopped for a person,
`ac agentic policies` writes the rules an organization governs its agents with,
and `ac agentic limits` reads and writes what it may spend in a day. All six
sit beside the live `ac agents runs` and replace none of it: the two stacks are
branch isolated until the cutover, so the alias and the deletion of the old
commands belong to Phase 7.

Every platform route sits under `/api/v1/agentic/`, so one path constant serves
every group and the parity audit resolves each call.

The endpoints are ac-docs, the file
engineering/system-design/agentic-platform/interfaces/surfaces.md, Run Explorer,
Agent Builder, Approval Inbox and The three admin surfaces.
"""

from __future__ import annotations

import json
import uuid

import typer
from rich import print as rprint
from rich.text import Text

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.formatting import (
    as_text,
    console,
    print_detail,
    print_json,
    print_table,
)

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

# ⚠️ **`No call` is what makes the `Status` column readable.** A `tool` span
# that reads `ok` is not always a call: a call that stopped for a person and a
# call answered from the journal both close `ok` and both carry the tool name.
# The column names which, so a person counting what a run did counts the rows
# that leave it empty.
_SPAN_FIELDS = [
    ("span_id", "Span ID"),
    ("kind", "Kind"),
    ("name", "Name"),
    ("status", "Status"),
    ("no_call_reason", "No call"),
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
            "[yellow]Duplicate:[/yellow] this key already started",
            as_text(f"{data['id']} (status: {data['status']})"),
        )
        return
    rprint(
        "[green]Run started:[/green]",
        as_text(f"{data['id']} ({data['definition_name']}, status: {data['status']})"),
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
    # The key is required and it is nullable, so a read of the key is honest
    # and a `.get` default would hide a shape change. A null usage means the
    # meter did not answer. Zero is a run that spent nothing, so the two must
    # not print the same line.
    usage = data["usage"]
    if usage is None:
        rprint("[dim]Tree usage:[/dim] unknown (the meter did not answer)")
    else:
        rprint(
            "[dim]Tree usage:[/dim]",
            as_text(f"{usage['total_tokens']} tokens, {usage['cost_cents']} cents"),
        )
    if data.get("child_count"):
        rprint("[dim]Read the children:[/dim] ac agentic runs list --parent", as_text(run_id))


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
        console.print(
            "[dim]Next page:[/dim] --cursor", as_text(data["next_cursor"]), soft_wrap=True
        )


def _print_spans_hint(items: list[dict], next_cursor: str | None, since: str | None) -> None:
    """Prints the command that reads the next spans, or reconnects.

    ⚠️ **A cursor names the order it was written for.** A `--since` page is
    tagged `updated_at` and a plain page is tagged `started_at`, so the hint
    repeats `--since`. Pasted without it, the same cursor answers `400`.

    ⚠️ **The hint prints with `soft_wrap`, so the cursor stays one token.** A
    cursor is about 108 characters, and the console hard wraps a longer line at
    the terminal width. A person copying a folded line pastes a cursor cut in
    three, which answers `400`.

    ⚠️ **The reconnect value is a line and never a column.** A person builds
    the next `--since` from the newest `updated_at` of the drain. `updated_at`
    would be the eighth column of the table, and eight columns truncate every
    timestamp at 80 columns beside a span id. The line prints the one value the
    loop reads, at any width.

    The reader drains the cursor before it moves `--since`. The filter is
    `>=` and one `UPDATE` stamps every span of a batch alike, so a reader that
    moved `--since` early would re-read that group and never pass it. So the
    reconnect line prints at the end of the drain alone.

    The page is ordered on `updated_at` ascending, so the last row carries the
    newest value.

    ⚠️ **A `--since` drain always ends with the line.** An idle poll is the
    steady state of the loop, and it answers an empty page. A read against an
    API that predates `updated_at` answers no value either. In both cases the
    boundary stays where it is, so the line names the value the read carried.
    A missing line leaves a script with an empty `--since`, which answers 422
    and stops the loop the option exists for.

    Args:
        items: The page, ordered on the column the read selected.
        next_cursor: The token of the next page, or None at the end of it.
        since: The value this read carried, or None for a plain read.
    """
    if next_cursor:
        if since is not None:
            console.print(
                "[dim]Next page:[/dim] --since",
                as_text(since),
                "--cursor",
                as_text(next_cursor),
                soft_wrap=True,
            )
        else:
            console.print("[dim]Next page:[/dim] --cursor", as_text(next_cursor), soft_wrap=True)
        return
    if since is None:
        return
    # get, and not a subscript. The CLI ships to PyPI on its own cadence, so it
    # meets an API older than this field. A KeyError would print a traceback
    # under a table it already rendered.
    # A truth test, and not `is None`. `_blank_if_null` asks whether a field
    # holds a value to print, where `0` is one. This asks whether a stamp can
    # move the boundary, and neither a null nor `""` can. Both take the same
    # fallback, so both take the same warning.
    #
    # It reads the page backwards, and not the last row alone. The rows are
    # ordered, so the first usable stamp from the end is the newest one. A page
    # whose last row carries no stamp still moves the boundary as far as its
    # rows allow, where reading that row alone would send the caller back to
    # where it started and drop the progress the page held.
    newest = next((row.get("updated_at") for row in reversed(items) if row.get("updated_at")), None)
    if items and not newest:
        # An empty page that repeats the boundary is an idle poll, and it is
        # correct. A full page that repeats it is not: the API answered rows
        # this reader cannot advance past, so the poll re-reads them for ever.
        # The two read alike on the line below, so say which this is.
        rprint(
            "[yellow]Warning:[/yellow] these spans carry no updated_at, so"
            " --since cannot advance and this poll repeats. The API is older"
            " than the reconnect read."
        )
    console.print(
        "[dim]Reconnect with:[/dim] --since",
        as_text(newest or since),
        soft_wrap=True,
    )


@runs_app.command("spans")
def runs_spans(
    ctx: typer.Context,
    run_id: str = typer.Argument(..., help="Run ID"),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Read the spans that moved at or after this instant, as ISO 8601 with a time zone",
    ),
    cursor: str | None = typer.Option(None, "--cursor", help="Page to continue"),
    limit: int = typer.Option(50, help="Page size"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the spans of one run.

    It reads the spans of that run alone. A child run holds its own spans, so
    open the child to read them.

    `--since` is what a client reads after a dropped stream. The run stream
    keeps no backlog, so a reconnecting reader asks for the spans that moved
    while it was away. It filters `updated_at`, so it answers a span that
    opened before the gap and closed inside it.

    ⚠️ **A cursor names the order it was written for.** `--since` orders the
    page on `updated_at` and a plain read orders it on `started_at`, so a
    cursor from one replayed against the other answers `400`. Carry both
    options together, or neither, which is why the next-page hint repeats
    `--since`.

    Drain the cursor, then read the `Reconnect with:` line the last page
    prints. It names the `--since` of the next poll, and it prints on every
    `--since` read that ends a drain, including one that moved nothing.
    """
    set_json_mode(json_output)
    params: dict = {"limit": limit}
    # `is not None`, and not a truth test. A reconnect loop builds this value
    # from the last page, and an empty one means the extraction failed. Sent
    # on, it answers 422; dropped, it reads the whole run unfiltered and the
    # loop re-reads it on every poll with nothing to say so.
    if since is not None:
        params["since"] = since
    if cursor:
        params["cursor"] = cursor

    resp = _api_request("get", f"{_AGENTIC}/runs/{run_id}/spans", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("items", [])
    print_table(items, _SPAN_FIELDS, title=f"Spans ({len(items)})")
    _print_spans_hint(items, data.get("next_cursor"), since)


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
    rprint("[green]Cancel requested:[/green]", as_text(f"{data['id']} (status: {data['status']})"))


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
        # The path names a JSON key the author typed, so build the line as a
        # Text. Every part then prints as it is, and the code keeps its dim.
        line = Text("  ")
        line.append(str(one["code"]), style="dim")
        if one.get("path"):
            line.append(" at ")
            line.append_text(as_text(one["path"]))
        line.append(": ")
        line.append_text(as_text(one["message"]))
        rprint(line)


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
        console.print(
            "[dim]Next page:[/dim] --cursor", as_text(data["next_cursor"]), soft_wrap=True
        )


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
    rprint(
        "[green]Draft created:[/green]", as_text(f"{data['id']} ({data['name']}, {data['kind']})")
    )


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
    rprint("[green]Draft saved:[/green]", as_text(data["id"]))
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
    rprint("[green]Published:[/green]", as_text(f"{data['id']} (state: {data['state']})"))


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
    rprint("[green]Disabled:[/green]", as_text(f"{data['id']} (state: {data['state']})"))


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
    rprint("[green]Enabled:[/green]", as_text(f"{data['id']} (state: {data['state']})"))


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
    rprint("[green]Forked:[/green]", as_text(f"{data['id']} ({data['name']}, {data['state']})"))


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
    rprint("[green]Draft deleted:[/green]", as_text(definition_id))


app.add_typer(definitions_app, name="definitions")


tools_app = typer.Typer(help="Agentic tool catalogue")

_TOOL_LIST_FIELDS = [
    ("name", "Tool ID"),
    ("side_effects", "Effect"),
    ("description", "Description"),
]


@tools_app.command("list")
def tools_list(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """List every tool a definition may name in `tool_ids`.

    The catalogue belongs to the platform, so every caller reads the same rows.
    The table shows the tool id, the effect and the description. Use `--json`
    for the two JSON Schemas, which no table renders.
    """
    set_json_mode(json_output)

    resp = _api_request("get", f"{_AGENTIC}/tools")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("items", [])
    print_table(items, _TOOL_LIST_FIELDS, title=f"Tools ({len(items)})")


app.add_typer(tools_app, name="tools")


approvals_app = typer.Typer(help="Agentic approval inbox")

_APPROVAL_FIELDS = [
    ("id", "Approval ID"),
    ("action", "Action"),
    ("target_summary", "Target"),
    ("preview", "Proposal"),
    ("reason", "Why a person"),
    ("raised_by", "Raised by"),
    ("status", "Status"),
    ("run_id", "Run"),
    ("created_at", "Requested"),
    ("expires_at", "Expires"),
    ("resolved_by", "Decided by"),
    ("resolved_at", "Decided"),
]

_APPROVAL_LIST_FIELDS = [
    ("id", "Approval ID"),
    ("action", "Action"),
    ("target_summary", "Target"),
    ("preview", "Proposal"),
    ("status", "Status"),
    ("expires_at", "Expires"),
]


@approvals_app.command("list")
def approvals_list(
    ctx: typer.Context,
    status: str | None = typer.Option(
        None,
        "--status",
        help="pending, approved, rejected, expired or cancelled. The default is pending.",
    ),
    cursor: str | None = typer.Option(None, "--cursor", help="Page to continue"),
    limit: int = typer.Option(50, help="Page size"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the approvals of your organization, soonest expiry first.

    It reads the work that waits by default. A row past its expiry is expired,
    so the pending page never offers one that nobody can answer.
    """
    set_json_mode(json_output)
    params: dict = {"limit": limit}
    # The endpoint reads pending when no status is named, so sending the
    # default would name a filter the caller did not choose.
    if status:
        params["status"] = status
    if cursor:
        params["cursor"] = cursor

    resp = _api_request("get", f"{_AGENTIC}/approvals", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("items", [])
    print_table(items, _APPROVAL_LIST_FIELDS, title=f"Approvals ({len(items)})")
    if data.get("next_cursor"):
        console.print(
            "[dim]Next page:[/dim] --cursor", as_text(data["next_cursor"]), soft_wrap=True
        )


@approvals_app.command("get")
def approvals_get(
    ctx: typer.Context,
    approval_id: str = typer.Argument(..., help="Approval ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Read one approval, and the exact proposal it authorizes.

    The proposal is redacted on the way out, so a credential prints as
    `[redacted]`. The stored row keeps every value, because the run executes
    the approved call from it.
    """
    set_json_mode(json_output)
    resp = _api_request("get", f"{_AGENTIC}/approvals/{approval_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, _APPROVAL_FIELDS)
    rprint("[dim]Proposal:[/dim]", as_text(json.dumps(data["proposed_arguments"])))


def _report_decision(data: dict, asked: str) -> None:
    """Prints the state the row now reads, and never the state a caller asked for.

    A repeated resolve answers 200 with the current state. So does a decision
    another surface made first, and so does a row that expired. The status is
    the whole answer, and a line that echoed the request would be wrong in all
    three cases.

    Args:
        data: The approval the endpoint answered.
        asked: The resolution this command asked for.
    """
    status = data["status"]
    if status == asked:
        rprint(f"[green]Approval {status}:[/green]", as_text(data["id"]))
        return
    rprint(
        "[yellow]Not written:[/yellow] this approval already reads",
        as_text(f"{status} ({data['id']})"),
    )


@approvals_app.command("approve")
def approvals_approve(
    ctx: typer.Context,
    approval_id: str = typer.Argument(..., help="Approval ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Authorize one exact proposal.

    Read it first. Approve authorizes the arguments the row holds, and the run
    executes those and nothing else.
    """
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Approve {approval_id}?", abort=True)

    resp = _api_request("post", f"{_AGENTIC}/approvals/{approval_id}/approve")

    data = resp.json()
    if json_output:
        print_json(data)
        return
    _report_decision(data, "approved")


@approvals_app.command("reject")
def approvals_reject(
    ctx: typer.Context,
    approval_id: str = typer.Argument(..., help="Approval ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Refuse one exact proposal.

    The run stops the work this approval was gating. To change the proposal,
    reject it and start the work again, so the new proposal gets its own
    decision.
    """
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Reject {approval_id}?", abort=True)

    resp = _api_request("post", f"{_AGENTIC}/approvals/{approval_id}/reject")

    data = resp.json()
    if json_output:
        print_json(data)
        return
    _report_decision(data, "rejected")


app.add_typer(approvals_app, name="approvals")


limits_app = typer.Typer(help="Agentic organization spend ceilings")

# The one ceiling this deploy enforces. A new kind is a database migration, so a
# typo here cannot create a ceiling that nothing enforces.
_DAILY_COST = "daily_cost"

_LIMIT_FIELDS = [
    ("kind", "Kind"),
    ("value_cents", "Value (cents)"),
    ("updated_at", "Updated"),
]


def _report_limit(data: dict) -> None:
    """Prints one ceiling, or says the organization has none.

    A null value is the no-cap state, and it is not an error. The accrual check
    reads an absent row as no cap.

    Args:
        data: The limit the endpoint answered.
    """
    if data.get("value_cents") is None:
        rprint("[green]No cap:[/green]", as_text(data["kind"]))
        return
    print_detail(data, _LIMIT_FIELDS)


@limits_app.command("get")
def limits_get(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Read what this organization may spend.

    An organization that set no ceiling has no cap, and the list is empty.
    """
    set_json_mode(json_output)
    resp = _api_request("get", f"{_AGENTIC}/limits")

    data = resp.json()
    if json_output:
        print_json(data)
        return
    items = data.get("items", [])
    if not items:
        rprint("[yellow]No cap:[/yellow] this organization set no ceiling")
        return
    print_table(items, _LIMIT_FIELDS, title="Limits")


@limits_app.command("set")
def limits_set(
    ctx: typer.Context,
    value_cents: int = typer.Option(
        ..., "--value-cents", min=0, help="What the organization may spend, in cents"
    ),
    kind: str = typer.Option(_DAILY_COST, "--kind", help="Which ceiling to write"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Set one spend ceiling.

    Zero is a ceiling somebody set, and it stops every run: the check compares
    the day's spend against the cap with `>=`. Use `limits clear` for no cap.
    """
    set_json_mode(json_output)
    resp = _api_request(
        "put", f"{_AGENTIC}/limits", json={"kind": kind, "value_cents": value_cents}
    )

    data = resp.json()
    if json_output:
        print_json(data)
        return
    _report_limit(data)


@limits_app.command("clear")
def limits_clear(
    ctx: typer.Context,
    kind: str = typer.Option(_DAILY_COST, "--kind", help="Which ceiling to remove"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Remove one spend ceiling, so the organization returns to no cap.

    It is the one path back. The value takes zero, and zero stops every run, so
    a lower number never undoes a ceiling.
    """
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Remove the {kind} ceiling?", abort=True)

    resp = _api_request("put", f"{_AGENTIC}/limits", json={"kind": kind, "value_cents": None})

    data = resp.json()
    if json_output:
        print_json(data)
        return
    _report_limit(data)


app.add_typer(limits_app, name="limits")


policies_app = typer.Typer(help="Agentic policy rules")

_POLICY_FIELDS = [
    ("id", "Policy ID"),
    ("name", "Name"),
    ("action", "Action"),
    ("decision", "Decision"),
    ("enabled", "Enabled"),
    ("definition_id", "Narrowed to"),
    ("approval_ttl_seconds", "Approval TTL (s)"),
    ("created_at", "Created"),
    ("updated_at", "Token"),
]

# The table holds no `updated_at`. The token is 32 characters, and a sixth
# column of that width truncates every other one to nothing. `--json` carries
# it, which is where `patch` reads it from.
_POLICY_LIST_FIELDS = [
    ("id", "Policy ID"),
    ("name", "Name"),
    ("action", "Action"),
    ("decision", "Decision"),
    ("enabled", "Enabled"),
]


def _parse_conditions(raw: str | None) -> dict | None:
    """Reads the --conditions flag, or answers None.

    A rule with no tree matches on the action alone.

    Args:
        raw: The JSON string the caller passed, or None.

    Returns:
        The parsed tree, or None.

    Raises:
        typer.Exit: The string is not a JSON object.
    """
    if raw is None:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        rprint("[red]Invalid JSON for --conditions[/red]")
        raise typer.Exit(code=1) from None
    if not isinstance(parsed, dict):
        rprint("[red]--conditions must be a JSON object[/red]")
        raise typer.Exit(code=1)
    return parsed


@policies_app.command("list")
def policies_list(
    ctx: typer.Context,
    action: str | None = typer.Option(
        None, "--action", help="Read the rules bound to exactly this action"
    ),
    cursor: str | None = typer.Option(None, "--cursor", help="Page cursor"),
    limit: int = typer.Option(50, "--limit", min=1, max=100, help="Page size"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the rules of this organization.

    The page holds the disabled rules too, because `enabled` is how a rule is
    turned off rather than deleted.

    `--action` matches the column exactly. It does not answer which rules
    govern one action: a `crm.*` rule governs `crm.send` and this filter reads
    the two apart.
    """
    set_json_mode(json_output)
    params: dict = {"limit": limit}
    if action:
        params["action"] = action
    if cursor:
        params["cursor"] = cursor

    resp = _api_request("get", f"{_AGENTIC}/policies", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return
    print_table(data.get("items", []), _POLICY_LIST_FIELDS, title="Policies")
    if data.get("next_cursor"):
        console.print("[dim]Next cursor:[/dim]", as_text(data["next_cursor"]), soft_wrap=True)


@policies_app.command("create")
def policies_create(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", help="What to call the rule"),
    action: str = typer.Option(..., "--action", help="An exact action, a domain wildcard, or *"),
    decision: str = typer.Option(..., "--decision", help="allow, deny, or require_approval"),
    definition_id: str | None = typer.Option(
        None, "--definition", help="Narrow the rule to one agent or workflow"
    ),
    conditions: str | None = typer.Option(
        None, "--conditions", help="The condition tree, as a JSON object"
    ),
    ttl: int | None = typer.Option(
        None, "--ttl", min=1, help="How long a person has to answer, in seconds"
    ),
    disabled: bool = typer.Option(False, "--disabled", help="Save the rule turned off"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Write one rule.

    A rule binds to an action first. Narrowing it to one definition is the
    exception.

    `--action '*'` is the organization kill switch. One rule of that shape,
    deciding `deny`, stops every new agentic action.
    """
    set_json_mode(json_output)
    body: dict = {
        "name": name,
        "action": action,
        "decision": decision,
        "enabled": not disabled,
    }
    if definition_id:
        body["definition_id"] = definition_id
    tree = _parse_conditions(conditions)
    if tree is not None:
        body["conditions"] = tree
    if ttl is not None:
        body["approval_ttl_seconds"] = ttl

    resp = _api_request("post", f"{_AGENTIC}/policies", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
        return
    rprint("[green]Policy created:[/green]", as_text(data["id"]))
    print_detail(data, _POLICY_FIELDS)


@policies_app.command("patch")
def policies_patch(
    ctx: typer.Context,
    policy_id: str = typer.Argument(..., help="Policy ID"),
    expected_updated_at: str = typer.Option(
        ...,
        "--expected-updated-at",
        help="The token the last read returned. Send it back unchanged.",
    ),
    patch: str = typer.Option(..., "--patch", help="The fields to replace, as a JSON object"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Replace the named fields of one rule.

    The patch replaces each named field whole, and an explicit null clears one.
    Set `enabled` to false to turn a rule off without deleting it.

    The token is opaque. Echo back the `updated_at` that
    `ac agentic policies list --json` returned, and never a value a date type
    has parsed: a millisecond round trip answers stale.
    """
    set_json_mode(json_output)
    body = {
        "expected_updated_at": expected_updated_at,
        **_parse_object(patch, "--patch"),
    }

    resp = _api_request("patch", f"{_AGENTIC}/policies/{policy_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
        return
    rprint("[green]Policy saved:[/green]", as_text(data["id"]))
    print_detail(data, _POLICY_FIELDS)


@policies_app.command("delete")
def policies_delete(
    ctx: typer.Context,
    policy_id: str = typer.Argument(..., help="Policy to remove"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Remove one rule.

    A rule restricts, so removing one widens what agents may do. Turn the rule
    off with `patch` when you want to keep the row.
    """
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete policy {policy_id}?", abort=True)

    _api_request("delete", f"{_AGENTIC}/policies/{policy_id}")

    if json_output:
        print_json({"id": policy_id, "deleted": True})
        return
    rprint("[green]Policy deleted:[/green]", as_text(policy_id))


app.add_typer(policies_app, name="policies")
