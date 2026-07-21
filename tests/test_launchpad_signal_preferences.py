"""Tests for the launchpad signal-preferences commands."""

import json

_PATH = "/api/v1/launchpad/signal-preferences"

CURRENT = {
    "sort_mode": "hottest",
    "group_by_saved_search": False,
    "score_threshold": None,
    "score_direction": "above",
}


def test_get(invoke, mock_api):
    mock_api.get(_PATH).respond(200, json=CURRENT)
    result = invoke(["launchpad", "signal-preferences", "get"])
    assert result.exit_code == 0
    assert "hottest" in result.output


def test_get_json(invoke, mock_api):
    mock_api.get(_PATH).respond(200, json=CURRENT)
    result = invoke(["launchpad", "signal-preferences", "get", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["sort_mode"] == "hottest"
    assert parsed["score_threshold"] is None


def test_set_merges_over_current(invoke, mock_api):
    # `set` is partial-friendly: it GETs the current config first, overlays the
    # provided flags, then PUTs the full merged object.
    mock_api.get(_PATH).respond(200, json=CURRENT)
    route = mock_api.put(_PATH).respond(
        200, json={**CURRENT, "sort_mode": "recent", "score_threshold": 50}
    )
    result = invoke(
        [
            "launchpad",
            "signal-preferences",
            "set",
            "--sort-mode",
            "recent",
            "--score-threshold",
            "50",
        ]
    )
    assert result.exit_code == 0
    assert "Updated" in result.output
    body = json.loads(route.calls.last.request.content)
    # Provided flags applied.
    assert body["sort_mode"] == "recent"
    assert body["score_threshold"] == 50
    # Unset flags preserved from the current server values.
    assert body["group_by_saved_search"] is False
    assert body["score_direction"] == "above"


def test_set_group_flag(invoke, mock_api):
    mock_api.get(_PATH).respond(200, json=CURRENT)
    route = mock_api.put(_PATH).respond(200, json={**CURRENT, "group_by_saved_search": True})
    result = invoke(["launchpad", "signal-preferences", "set", "--group"])
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["group_by_saved_search"] is True


def test_set_score_direction(invoke, mock_api):
    mock_api.get(_PATH).respond(200, json=CURRENT)
    route = mock_api.put(_PATH).respond(200, json={**CURRENT, "score_direction": "below"})
    result = invoke(
        [
            "launchpad",
            "signal-preferences",
            "set",
            "--score-direction",
            "below",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["score_direction"] == "below"


def test_set_clear_threshold(invoke, mock_api):
    # --clear-threshold removes an existing threshold (score_threshold -> null),
    # the one path a bare --score-threshold cannot express.
    current = {**CURRENT, "score_threshold": 50}
    mock_api.get(_PATH).respond(200, json=current)
    route = mock_api.put(_PATH).respond(200, json={**current, "score_threshold": None})
    result = invoke(["launchpad", "signal-preferences", "set", "--clear-threshold"])
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["score_threshold"] is None


def test_set_json(invoke, mock_api):
    mock_api.get(_PATH).respond(200, json=CURRENT)
    mock_api.put(_PATH).respond(200, json={**CURRENT, "sort_mode": "recent"})
    result = invoke(
        [
            "launchpad",
            "signal-preferences",
            "set",
            "--sort-mode",
            "recent",
            "--json",
        ]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["sort_mode"] == "recent"


def test_set_invalid_value_exits_2(invoke, mock_api):
    # The API validates the enum and returns 422 -> semantic exit code 2.
    mock_api.get(_PATH).respond(200, json=CURRENT)
    mock_api.put(_PATH).respond(422, json={"detail": "bad sort_mode"})
    result = invoke(
        [
            "launchpad",
            "signal-preferences",
            "set",
            "--sort-mode",
            "bogus",
        ]
    )
    assert result.exit_code == 2
