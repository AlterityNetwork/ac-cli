"""ENG-2903: `ac envoy` stays a hidden alias of `ac sequences` for one release."""

from typer.testing import CliRunner

from ac_cli.main import app


def test_ac_envoy_runs_the_sequences_command(invoke, mock_api):
    route = mock_api.get("/api/v1/sequences/dashboard/inbox-count").respond(200, json={"count": 7})
    result = invoke(["envoy", "inbox-count"])
    assert result.exit_code == 0, result.output
    assert route.called


def test_help_lists_sequences_and_hides_envoy():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "sequences" in result.output
    assert "envoy" not in result.output.lower()
