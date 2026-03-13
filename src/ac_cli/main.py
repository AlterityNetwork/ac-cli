"""AgencyCore CLI entry point."""

import typer

from ac_cli import __version__
from ac_cli.commands import admin, apps, auth, crm, health
from ac_cli.commands import envoy
from ac_cli.commands import hooks
from ac_cli.commands import nylas
from ac_cli.commands import workflows
from ac_cli.commands import writing_styles

def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"ac {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="ac",
    help="AgencyCore CLI — authenticate and interact with the AgencyCore API.",
    no_args_is_help=True,
)


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version and exit", callback=_version_callback, is_eager=True,
    ),
) -> None:
    pass

# Register sub-command groups
app.add_typer(admin.app, name="admin")
app.add_typer(apps.app, name="apps")
app.add_typer(auth.app, name="auth")
app.add_typer(crm.app, name="crm")
app.add_typer(health.app, name="health")
app.add_typer(envoy.app, name="envoy")
app.add_typer(hooks.app, name="hooks")
app.add_typer(nylas.app, name="nylas")
app.add_typer(workflows.app, name="workflows")
app.add_typer(writing_styles.app, name="styles")

# Promote common auth commands to top level for convenience
app.command("login")(auth.login)
app.command("logout")(auth.logout)
app.command("whoami")(auth.whoami)

if __name__ == "__main__":
    app()
