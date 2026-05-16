"""Environment management commands: list, show, use."""

import typer
from rich import print as rprint
from rich.table import Table

from ac_cli.commands._helpers import JSON_OPTION, set_json_mode
from ac_cli.config import (
    ENV_NAMES,
    ENVIRONMENTS,
    load_full_config,
    set_active_env,
)

app = typer.Typer(help="Manage CLI environments (local, staging, production)")


@app.callback()
def callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@app.command("list")
def list_envs(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """List all environments and their login status."""
    set_json_mode(json_output)
    import json as json_mod

    full = load_full_config()
    active = full.get("active")
    envs = full.get("environments", {})

    if json_output:
        rows = []
        for name in ENV_NAMES:
            env_data = envs.get(name, {})
            rows.append(
                {
                    "name": name,
                    "active": name == active,
                    "logged_in": bool(env_data.get("access_token")),
                    "api_url": env_data.get("api_url", ENVIRONMENTS[name]["api_url"]),
                }
            )
        rprint(json_mod.dumps(rows, indent=2))
        return

    table = Table(title="Environments")
    table.add_column("", width=2)
    table.add_column("Name")
    table.add_column("API URL")
    table.add_column("Status")

    for name in ENV_NAMES:
        env_data = envs.get(name, {})
        marker = "*" if name == active else ""
        api_url = env_data.get("api_url", ENVIRONMENTS[name]["api_url"])
        logged_in = bool(env_data.get("access_token"))
        status = "[green]logged in[/green]" if logged_in else "[dim]not logged in[/dim]"
        table.add_row(marker, name, api_url, status)

    rprint(table)


@app.command()
def show(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Show the active environment details."""
    set_json_mode(json_output)
    import json as json_mod

    full = load_full_config()
    active = full.get("active")
    env_data = full.get("environments", {}).get(active, {})
    defaults = ENVIRONMENTS.get(active, {})

    info = {
        "environment": active,
        "api_url": env_data.get("api_url", defaults.get("api_url", "")),
        "supabase_url": env_data.get("supabase_url", defaults.get("supabase_url", "")),
        "logged_in": bool(env_data.get("access_token")),
    }

    if json_output:
        rprint(json_mod.dumps(info, indent=2))
        return

    rprint(f"[bold]Environment:[/bold] {info['environment']}")
    rprint(f"[bold]API URL:[/bold]     {info['api_url']}")
    rprint(f"[bold]Supabase:[/bold]    {info['supabase_url']}")
    status = "[green]logged in[/green]" if info["logged_in"] else "[dim]not logged in[/dim]"
    rprint(f"[bold]Status:[/bold]      {status}")


@app.command()
def use(
    name: str = typer.Argument(..., help="Environment name (local, staging, production)"),
) -> None:
    """Switch the active environment."""
    if name not in ENV_NAMES:
        rprint(f"[red]Unknown environment:[/red] {name}")
        rprint(f"Available: {', '.join(ENV_NAMES)}")
        raise typer.Exit(code=1)

    full = load_full_config()
    env_data = full.get("environments", {}).get(name, {})
    set_active_env(name)

    if not env_data.get("access_token"):
        rprint(f"[yellow]Switched to {name} (not logged in — run `ac login --env {name}`)[/yellow]")
    else:
        rprint(f"[green]Switched to {name}[/green]")
