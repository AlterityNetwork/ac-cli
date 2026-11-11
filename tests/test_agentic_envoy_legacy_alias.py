"""ENG-2904: `ac agentic outreach` stays a hidden alias of `ac agentic envoy`."""

from typer.testing import CliRunner

from ac_cli.main import app


def test_ac_agentic_outreach_runs_the_envoy_command(invoke, mock_api):
    route = mock_api.get("/api/v1/agentic/envoy/campaigns").respond(200, json={"items": []})
    result = invoke(["agentic", "outreach", "campaigns", "list"])
    assert result.exit_code == 0, result.output
    assert route.called


def test_agentic_help_lists_envoy_and_hides_outreach():
    result = CliRunner().invoke(app, ["agentic", "--help"])
    assert result.exit_code == 0
    assert "envoy" in result.output
    assert "outreach" not in result.output
