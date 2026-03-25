"""Organization apps commands."""

from __future__ import annotations

import json as json_lib

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, _build_body, set_json_mode, should_skip_confirm
from ac_cli.formatting import print_detail, print_json, print_table

app = typer.Typer(help="Organization app operations")

_APPS = "/api/v1/orgs"


@app.callback()
def apps_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


def _resolve_org_id(org_id: str | None) -> str:
    """Resolve org ID from argument or /whoami."""
    if org_id:
        return org_id
    me = _api_request("get", "/whoami")
    return me.json()["organization_id"]


@app.command("install")
def apps_install(
    ctx: typer.Context,
    app_slug: str = typer.Argument(..., help="App slug to install"),
    org_id: str | None = typer.Option(None, "--org-id", help="Organization ID (auto-resolved from /whoami)"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Install an app for the organization."""
    set_json_mode(json_output)
    oid = _resolve_org_id(org_id)
    resp = _api_request("post", f"{_APPS}/{oid}/apps/{app_slug}")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Installed {app_slug}[/green]")


@app.command("uninstall")
def apps_uninstall(
    app_slug: str = typer.Argument(..., help="App slug to uninstall"),
    org_id: str | None = typer.Option(None, "--org-id", help="Organization ID (auto-resolved from /whoami)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Uninstall an app from the organization."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Uninstall app {app_slug}?", abort=True)

    oid = _resolve_org_id(org_id)
    _api_request("delete", f"{_APPS}/{oid}/apps/{app_slug}")

    rprint(f"[green]Uninstalled {app_slug}[/green]")


@app.command("list")
def apps_list(
    ctx: typer.Context,
    org_id: str | None = typer.Option(None, "--org-id", help="Organization ID (auto-resolved from /whoami)"),
    include_inactive: bool = typer.Option(False, "--include-inactive", help="Include inactive apps"),
    limit: int = typer.Option(100, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List installed apps for the organization."""
    set_json_mode(json_output)
    oid = _resolve_org_id(org_id)
    params: dict = {"limit": limit, "offset": offset}
    if include_inactive:
        params["include_inactive"] = True

    resp = _api_request("get", f"{_APPS}/{oid}/apps", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data if isinstance(data, list) else data.get("data", []),
        [
            ("app_slug", "App Slug"),
            ("status", "Status"),
            ("installed_at", "Installed At"),
        ],
        title="Apps",
    )


@app.command("usage-event")
def apps_usage_event(
    ctx: typer.Context,
    app_slug: str = typer.Argument(..., help="App slug"),
    org_id: str | None = typer.Option(None, "--org-id", help="Organization ID (auto-resolved from /whoami)"),
    event_type: str = typer.Option(..., "--event-type", help="Event type"),
    metadata: str | None = typer.Option(None, "--metadata", help="JSON metadata string"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Record a usage event for an app."""
    set_json_mode(json_output)
    oid = _resolve_org_id(org_id)
    body: dict = {"event_type": event_type}
    if metadata is not None:
        try:
            body["metadata"] = json_lib.loads(metadata)
        except json_lib.JSONDecodeError:
            rprint("[red]Invalid JSON for --metadata[/red]")
            raise typer.Exit(code=1)

    resp = _api_request("post", f"{_APPS}/{oid}/apps/{app_slug}/events", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Recorded usage event for {app_slug}[/green]")


@app.command("usage")
def apps_usage(
    ctx: typer.Context,
    app_slug: str = typer.Argument(..., help="App slug"),
    org_id: str | None = typer.Option(None, "--org-id", help="Organization ID (auto-resolved from /whoami)"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get usage summary for an app."""
    set_json_mode(json_output)
    oid = _resolve_org_id(org_id)
    resp = _api_request("get", f"{_APPS}/{oid}/apps/{app_slug}/usage")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, [
        ("app_slug", "App Slug"),
        ("total_events", "Total Events"),
        ("last_event_at", "Last Event"),
    ])


@app.command("configs")
def apps_configs(
    ctx: typer.Context,
    app_slug: str = typer.Argument(..., help="App slug"),
    org_id: str | None = typer.Option(None, "--org-id", help="Organization ID (auto-resolved from /whoami)"),
    mask_secrets: bool = typer.Option(True, "--mask-secrets/--no-mask-secrets", help="Mask secret values"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List configuration for an app."""
    set_json_mode(json_output)
    oid = _resolve_org_id(org_id)
    params: dict = {"mask_secrets": mask_secrets}
    resp = _api_request("get", f"{_APPS}/{oid}/apps/{app_slug}/configs", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("config_key", "Config Key"),
            ("value", "Value"),
        ],
        title=f"Configs for {app_slug}",
    )


@app.command("update-config")
def apps_update_config(
    ctx: typer.Context,
    app_slug: str = typer.Argument(..., help="App slug"),
    config_key: str = typer.Argument(..., help="Configuration key"),
    value: str = typer.Option(..., "--value", help="Configuration value"),
    org_id: str | None = typer.Option(None, "--org-id", help="Organization ID (auto-resolved from /whoami)"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a configuration value for an app."""
    set_json_mode(json_output)
    oid = _resolve_org_id(org_id)
    resp = _api_request(
        "put",
        f"{_APPS}/{oid}/apps/{app_slug}/configs/{config_key}",
        json={"value": value},
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated config {config_key} for {app_slug}[/green]")


@app.command("delete-config")
def apps_delete_config(
    app_slug: str = typer.Argument(..., help="App slug"),
    config_key: str = typer.Argument(..., help="Configuration key"),
    org_id: str | None = typer.Option(None, "--org-id", help="Organization ID (auto-resolved from /whoami)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a configuration key for an app."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete config {config_key} for {app_slug}?", abort=True)

    oid = _resolve_org_id(org_id)
    _api_request("delete", f"{_APPS}/{oid}/apps/{app_slug}/configs/{config_key}")

    rprint(f"[green]Deleted config {config_key} for {app_slug}[/green]")
