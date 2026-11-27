"""The hidden `ac agentic capabilities estimate` alias calls the startable route."""

import json

PATH = "/api/v1/agentic/definitions/startable/signals.search/estimate"


def test_the_alias_posts_to_the_startable_route(invoke, mock_api):
    route = mock_api.post(PATH).respond(200, json={"priced": False, "credits_per_run": 200})

    result = invoke(
        ["agentic", "capabilities", "estimate", "signals.search", "--units", "3", "--json"]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {"units": 3}


def test_the_alias_is_hidden_from_help(invoke):
    result = invoke(["agentic", "capabilities", "--help"])

    assert "estimate" not in result.output
