"""Shared helpers for CLI commands."""

import contextvars
import os
from typing import NoReturn

import httpx
import typer
from rich import print as rprint
from rich.text import Text

from ac_cli.client import get_api_client
from ac_cli.formatting import as_text, print_json

_json_output: contextvars.ContextVar[bool] = contextvars.ContextVar("json_output", default=False)

JSON_OPTION = typer.Option(False, "--json", help="Output raw JSON")

_EXIT_CODES = {401: 4, 403: 4, 404: 3, 409: 5, 422: 2}

_KEY_FLAG = "--idempotency-key"


def set_json_mode(enabled: bool) -> None:
    """Set the JSON output mode for the current context."""
    _json_output.set(enabled)


def should_skip_confirm(yes_flag: bool) -> bool:
    """Check if confirmation should be skipped via flag or AC_YES env var."""
    return yes_flag or os.environ.get("AC_YES", "").lower() in ("1", "true", "yes")


def _handle_error(exc: httpx.HTTPStatusError) -> None:
    """Print API error detail and exit.

    The server writes the detail, and rprint reads rich markup. A detail that
    holds `[/urgent]` raises MarkupError, and the command then exits 1 with no
    reason. Print the detail through as_text, which never reaches the markup
    parser. See as_text in formatting.py.
    """
    try:
        body = exc.response.json()
        detail = body.get("detail") or body.get("message") or exc.response.text
    except (ValueError, KeyError):
        detail = exc.response.text
    exit_code = _EXIT_CODES.get(exc.response.status_code, 1)
    if _json_output.get():
        print_json({"error": True, "status_code": exc.response.status_code, "detail": detail})
    else:
        rprint(f"[red]Error {exc.response.status_code}:[/red]", as_text(detail))
    raise typer.Exit(code=exit_code)


def _api_request(method: str, path: str, **kwargs: object) -> httpx.Response:
    """Make an authenticated API request with standard error handling."""
    with get_api_client() as client:
        try:
            resp = getattr(client, method)(path, **kwargs)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)
        except httpx.HTTPError as exc:
            if _json_output.get():
                print_json({"error": True, "status_code": None, "detail": str(exc)})
            else:
                rprint("[red]Connection error:[/red]", as_text(exc))
            raise typer.Exit(code=1)
    return resp


def _resolve_entity(
    *,
    entity_id: str | None,
    entity_name: str | None,
    search_path: str,
    name_field: str = "name",
    label: str = "entity",
) -> str | None:
    """Resolve an entity ID from an explicit ID or a name-based search.

    Returns the entity ID, or ``None`` if neither *entity_id* nor
    *entity_name* was provided.  Exits with an error when a name search
    finds zero or multiple matches.
    """
    if entity_id:
        return entity_id
    if not entity_name:
        return None

    resp = _api_request("get", search_path, params={"search": entity_name, "limit": 5})
    data = resp.json()
    items = data if isinstance(data, list) else data.get("data", [])

    if not items:
        if _json_output.get():
            print_json({"error": True, "detail": f"No {label} found matching '{entity_name}'"})
        else:
            rprint(Text(f"No {label} found matching '{entity_name}'", style="red"))
        raise typer.Exit(code=3)

    if len(items) > 1:
        # Check for an exact match first
        exact = [i for i in items if (i.get(name_field) or "").lower() == entity_name.lower()]
        if len(exact) == 1:
            return exact[0]["id"]
        if _json_output.get():
            matches = [{"id": i["id"], name_field: i.get(name_field)} for i in items]
            print_json(
                {
                    "error": True,
                    "detail": f"Multiple {label}s match '{entity_name}'",
                    "matches": matches,
                }
            )
        else:
            rprint(Text(f"Multiple {label}s match '{entity_name}':", style="yellow"))
            for item in items:
                rprint(as_text(f"  - {item.get(name_field) or '?'} ({item['id']})"))
        raise typer.Exit(code=2)

    return items[0]["id"]


def _require_id(
    resolved_id: str | None,
    *,
    id_label: str = "ID",
    name_flag: str = "--name",
) -> str:
    """Ensure an entity ID was resolved — exit with error if not."""
    if resolved_id:
        return resolved_id
    if _json_output.get():
        print_json({"error": True, "detail": f"Provide a {id_label} or use {name_flag}"})
    else:
        rprint(f"[red]Provide a {id_label} or use {name_flag}[/red]")
    raise typer.Exit(code=2)


def _resolve_company_id(
    company_id: str | None,
    company_name: str | None,
    crm_prefix: str,
) -> str | None:
    """Resolve a company ID from ``--company-id`` or ``--company-name``."""
    return _resolve_entity(
        entity_id=company_id,
        entity_name=company_name,
        search_path=f"{crm_prefix}/companies",
        name_field="name",
        label="company",
    )


def _resolve_contact_id(
    contact_id: str | None,
    contact_name: str | None,
    crm_prefix: str,
) -> str | None:
    """Resolve a contact ID from ``--contact-id`` or ``--contact-name``."""
    return _resolve_entity(
        entity_id=contact_id,
        entity_name=contact_name,
        search_path=f"{crm_prefix}/people",
        name_field="full_name",
        label="contact",
    )


def _resolve_deal_id(
    deal_id: str | None,
    deal_name: str | None,
    crm_prefix: str,
) -> str | None:
    """Resolve a deal ID from ``--deal-id`` or ``--deal-name``."""
    return _resolve_entity(
        entity_id=deal_id,
        entity_name=deal_name,
        search_path=f"{crm_prefix}/deals",
        name_field="name",
        label="deal",
    )


def _get_org_id() -> str:
    """Fetch the current user's organization ID from /whoami."""
    resp = _api_request("get", "/whoami")
    return resp.json()["organization_id"]


def _build_body(**fields: object) -> dict:
    """Build API request body from non-None fields."""
    body: dict = {}
    for key, value in fields.items():
        if value is not None:
            if key == "tags" and isinstance(value, str):
                body[key] = [t.strip() for t in value.split(",")]
            else:
                body[key] = value
    return body


def header_safe_key(key: str) -> bool:
    """Reports whether one idempotency key can travel in a request header.

    h11 raises LocalProtocolError for a newline, a carriage return, a null
    byte or outer whitespace. httpx raises UnicodeEncodeError for a non-ASCII
    value. Both raise deep in the transport, so read the key here and name the
    flag that is wrong.

    A tab and DEL travel with no error. This function refuses them too. An
    invisible character makes two keys that look equal name two deliveries.

    The bound is 200 characters. The agentic run and conversation routes cap
    the header at 255, so this bound is the stricter of the two.

    Args:
        key: The key the caller supplied.

    Returns:
        True when the key holds 1 to 200 printable ASCII characters and no
        outer whitespace.
    """
    return (
        bool(key)
        and key == key.strip()
        and len(key) <= 200
        and all(32 <= ord(char) < 127 for char in key)
    )


def refuse_local(detail: str, value: object | None = None) -> NoReturn:
    """Reports one local input error, and exits before any HTTP call.

    A poll drives these commands with `--json`, so the refusal answers the
    shape that caller parses. See _handle_error, which answers the same shape
    for a refusal the API wrote.

    ⚠️ **Click renders its own refusal as a usage box, never as JSON.** A range
    or a choice on a typer.Option therefore breaks the `--json` contract, so a
    command checks the bounds of a flag itself and calls this function.

    Args:
        detail: What the caller must change.
        value: What the caller typed, when the message must echo it. The
          message appends it after a colon. Leave it None to name no value.

    Raises:
        typer.Exit: Always, with the validation code.
    """
    message = detail if value is None else f"{detail}: {value}"
    if _json_output.get():
        print_json({"error": True, "status_code": None, "detail": message})
    else:
        rprint("[red]Invalid option:[/red]", as_text(message))
    raise typer.Exit(code=2)


def checked_header_key(key: str) -> str:
    """Returns one idempotency key, or refuses it before any HTTP call.

    Every command that starts work sends the key in a request header. A key
    the header refuses fails deep in the transport. LocalProtocolError is an
    httpx.HTTPError. _api_request catches it, and the caller then reads a
    connection error for a typing error. Refuse the key here, so all five
    senders answer one message and one exit code.

    See header_safe_key for the rule and for what each layer refuses.

    The refusal never echoes the value. A refused key holds control
    characters, and those characters move the cursor of the terminal that
    prints them.

    Args:
        key: The key the caller supplied.

    Returns:
        The key, when the header accepts it.

    Raises:
        typer.Exit: Code 2, when the header refuses the key.
    """
    if header_safe_key(key):
        return key
    refuse_local(f"{_KEY_FLAG} must contain 1–200 header-safe ASCII characters")
