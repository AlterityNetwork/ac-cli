"""Tests for superadmin impersonation: --act-as flag and AC_ACT_AS env var."""

import os
from unittest.mock import patch

from tests.conftest import WHOAMI_RESPONSE


def test_act_as_flag_adds_header(invoke, mock_api):
    """--act-as injects X-Act-As-User on every API request."""
    route = mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    result = invoke(["--act-as", "target-user-uuid", "whoami"])
    assert result.exit_code == 0
    assert route.called
    sent = route.calls.last.request
    assert sent.headers.get("X-Act-As-User") == "target-user-uuid"
    assert sent.headers.get("Authorization", "").startswith("Bearer ")


def test_act_as_env_var_adds_header(invoke, mock_api):
    """AC_ACT_AS env var produces the same header without the flag."""
    route = mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    with patch.dict(os.environ, {"AC_ACT_AS": "env-target-uuid"}, clear=False):
        result = invoke(["whoami"])
    assert result.exit_code == 0
    assert route.calls.last.request.headers.get("X-Act-As-User") == "env-target-uuid"


def test_no_act_as_omits_header(invoke, mock_api):
    """Header is not sent when neither flag nor env var is set."""
    route = mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    # Defensive: clear env var if present in the developer's shell.
    env = {k: v for k, v in os.environ.items() if k != "AC_ACT_AS"}
    with patch.dict(os.environ, env, clear=True):
        result = invoke(["whoami"])
    assert result.exit_code == 0
    assert "X-Act-As-User" not in route.calls.last.request.headers


def test_act_as_flag_overrides_env_var(invoke, mock_api):
    """When both are set, the explicit --act-as wins."""
    route = mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    with patch.dict(os.environ, {"AC_ACT_AS": "from-env"}, clear=False):
        result = invoke(["--act-as", "from-flag", "whoami"])
    assert result.exit_code == 0
    assert route.calls.last.request.headers.get("X-Act-As-User") == "from-flag"


def test_act_as_whitespace_value_stripped(invoke, mock_api):
    """Whitespace-only AC_ACT_AS value does not add the header."""
    route = mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    with patch.dict(os.environ, {"AC_ACT_AS": "   "}, clear=False):
        result = invoke(["whoami"])
    assert result.exit_code == 0
    assert "X-Act-As-User" not in route.calls.last.request.headers
