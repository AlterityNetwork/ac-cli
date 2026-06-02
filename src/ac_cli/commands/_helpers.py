"""Shared helpers for CLI commands."""

import contextvars
import os

import httpx
import typer
from rich import print as rprint

from ac_cli.client import get_api_client
from ac_cli.formatting import OutputMode, get_output_mode, print_json, set_output_mode

_json_output: contextvars.ContextVar[bool] = contextvars.ContextVar("json_output", default=False)

JSON_OPTION = typer.Option(False, "--json", help="Output raw JSON")

_EXIT_CODES = {401: 4, 403: 4, 404: 3, 409: 5, 422: 2}


def set_json_mode(enabled: bool) -> None:
    """Set the JSON output mode for the current context."""
    if enabled:
        set_output_mode(OutputMode.json)
        _json_output.set(True)
        return
    _json_output.set(get_output_mode() == OutputMode.json)


def should_skip_confirm(yes_flag: bool) -> bool:
    """Check if confirmation should be skipped via flag or AC_YES env var."""
    return yes_flag or os.environ.get("AC_YES", "").lower() in ("1", "true", "yes")


def _handle_error(exc: httpx.HTTPStatusError) -> None:
    """Print API error detail and exit."""
    try:
        body = exc.response.json()
        detail = body.get("detail") or body.get("message") or exc.response.text
    except (ValueError, KeyError):
        detail = exc.response.text
    exit_code = _EXIT_CODES.get(exc.response.status_code, 1)
    if _json_output.get():
        print_json({"error": True, "status_code": exc.response.status_code, "detail": detail})
    else:
        rprint(f"[red]Error {exc.response.status_code}:[/red] {detail}")
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
                rprint(f"[red]Connection error:[/red] {exc}")
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
            rprint(f"[red]No {label} found matching '{entity_name}'[/red]")
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
            rprint(f"[yellow]Multiple {label}s match '{entity_name}':[/yellow]")
            for item in items:
                rprint(f"  - {item.get(name_field, '?')} ({item['id']})")
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
