"""Authentication commands: login, logout, whoami."""

import httpx
import typer
from rich import print as rprint
from supabase import create_client

from ac_cli.client import get_api_client
from ac_cli.config import (
    ENV_NAMES,
    ENVIRONMENTS,
    clear_config,
    clear_env_config,
    get_active_env,
    load_full_config,
    save_full_config,
    set_active_env,
)

app = typer.Typer(help="Authentication commands")


@app.command()
def login(
    email: str = typer.Option(None, help="Supabase account email"),
    password: str = typer.Option(None, help="Account password"),
    supabase_url: str = typer.Option(None, help="Supabase project URL"),
    supabase_anon_key: str = typer.Option(None, help="Supabase anonymous/public key"),
    api_url: str = typer.Option(None, help="AgencyCore API base URL"),
    env: str = typer.Option(
        None,
        "--env",
        help="Environment to log in to (local, staging, production). Default: active env.",
    ),
    dev: bool = typer.Option(
        False,
        "--dev",
        help="[deprecated] Use --env local instead",
        hidden=True,
    ),
) -> None:
    """Sign in with email and password via Supabase.

    By default, logs in to the currently active environment. Use --env to target
    a specific environment (local, staging, production).
    """
    # Resolve environment name
    if dev and not env:
        env = "local"
    env = env or get_active_env()

    if env not in ENV_NAMES:
        rprint(f"[red]Unknown environment:[/red] {env}")
        rprint(f"Available: {', '.join(ENV_NAMES)}")
        raise typer.Exit(code=1)

    defaults = ENVIRONMENTS[env]
    api_url = api_url or defaults["api_url"]
    supabase_url = supabase_url or defaults["supabase_url"]
    supabase_anon_key = supabase_anon_key or defaults["supabase_anon_key"]

    rprint(f"[dim]Logging in to {env} environment[/dim]")

    if not email:
        email = typer.prompt("Email")
    if not password:
        password = typer.prompt("Password", hide_input=True)

    try:
        client = create_client(supabase_url, supabase_anon_key)
        response = client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception as exc:
        rprint(f"[red]Login failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    session = response.session
    if not session:
        rprint("[red]Login failed: no session returned.[/red]")
        raise typer.Exit(code=1)

    # Save credentials under the target environment
    full = load_full_config()
    envs = full.get("environments", {})
    envs[env] = {
        "api_url": api_url,
        "supabase_url": supabase_url,
        "supabase_anon_key": supabase_anon_key,
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
    }
    full["environments"] = envs
    full["active"] = env
    save_full_config(full)

    rprint(f"[green]Logged in as {email} ({env})[/green]")


@app.command()
def logout(
    env: str = typer.Option(
        None,
        "--env",
        help="Logout from a specific environment (default: all)",
    ),
) -> None:
    """Clear stored credentials.

    By default, logs out of all environments. Use --env to log out of a
    specific environment only.
    """
    if env:
        if env not in ENV_NAMES:
            rprint(f"[red]Unknown environment:[/red] {env}")
            rprint(f"Available: {', '.join(ENV_NAMES)}")
            raise typer.Exit(code=1)
        clear_env_config(env)
        rprint(f"[green]Logged out of {env}.[/green]")
    else:
        clear_config()
        rprint("[green]Logged out of all environments.[/green]")


@app.command()
def whoami(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Show the currently authenticated user."""
    from ac_cli.commands._helpers import _EXIT_CODES, set_json_mode, JSON_OPTION
    from ac_cli.formatting import print_json

    set_json_mode(json_output)
    active = get_active_env()
    with get_api_client() as client:
        try:
            resp = client.get("/whoami")
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                body = exc.response.json()
                detail = body.get("detail") or body.get("message") or exc.response.text
            except (ValueError, KeyError):
                detail = exc.response.text
            exit_code = _EXIT_CODES.get(exc.response.status_code, 1)
            if json_output:
                print_json({"error": True, "status_code": exc.response.status_code, "detail": detail})
            else:
                rprint(f"[red]Error {exc.response.status_code}:[/red] {detail}")
            raise typer.Exit(code=exit_code)
        except httpx.HTTPError as exc:
            if json_output:
                print_json({"error": True, "status_code": None, "detail": str(exc)})
            else:
                rprint(f"[red]Connection error:[/red] {exc}")
            raise typer.Exit(code=1)
    data = resp.json()
    data["environment"] = active
    if json_output:
        print_json(data)
    else:
        rprint(data)
