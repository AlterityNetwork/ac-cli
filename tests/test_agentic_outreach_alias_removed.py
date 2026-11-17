"""ENG-2989: the hidden `ac agentic outreach` alias of ENG-2904 is gone."""

from typer.testing import CliRunner

from ac_cli.main import app


def test_ac_agentic_outreach_is_an_unknown_command():
    result = CliRunner().invoke(app, ["agentic", "outreach", "campaigns", "list"])
    assert result.exit_code == 2
    assert "No such command 'outreach'" in result.output


def test_ac_agentic_envoy_still_runs(invoke, mock_api):
    route = mock_api.get("/api/v1/agentic/envoy/campaigns").respond(200, json={"items": []})
    result = invoke(["agentic", "envoy", "campaigns", "list"])
    assert result.exit_code == 0, result.output
    assert route.called
