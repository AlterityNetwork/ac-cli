"""AgencyCore CLI entry point."""

import typer

from ac_cli import __version__
from ac_cli.commands import admin, agent, apps, auth, chat, crm, env, files, health
from ac_cli.commands import envoy
from ac_cli.commands import hooks
from ac_cli.commands import legal_documents
from ac_cli.commands import managed_onboarding
from ac_cli.commands import marketplace
from ac_cli.commands import messaging
from ac_cli.commands import network
from ac_cli.commands import nylas
from ac_cli.commands import profiles
from ac_cli.commands import resources
from ac_cli.commands import tos
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
app.add_typer(agent.app, name="agent")
app.add_typer(admin.app, name="admin")
app.add_typer(apps.app, name="apps")
app.add_typer(auth.app, name="auth")
app.add_typer(chat.app, name="chat")
app.add_typer(crm.app, name="crm")
app.add_typer(env.app, name="env")
app.add_typer(health.app, name="health")
app.add_typer(envoy.app, name="envoy")
app.add_typer(files.app, name="files")
app.add_typer(hooks.app, name="hooks")
app.add_typer(legal_documents.app, name="legal-docs")
app.add_typer(managed_onboarding.app, name="onboarding")
app.add_typer(marketplace.app, name="marketplace")
app.add_typer(messaging.app, name="messaging")
app.add_typer(network.app, name="network")
app.add_typer(nylas.app, name="nylas")
app.add_typer(profiles.app, name="profiles")
app.add_typer(resources.app, name="resources")
app.add_typer(tos.app, name="tos")
app.add_typer(workflows.app, name="workflows")
app.add_typer(writing_styles.app, name="styles")

# Promote common auth commands to top level for convenience
app.command("login")(auth.login)
app.command("logout")(auth.logout)
app.command("whoami")(auth.whoami)

if __name__ == "__main__":
    app()
