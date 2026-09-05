"""Shared test fixtures for ac-cli tests."""

from unittest.mock import patch

import pytest
import respx
from typer.testing import CliRunner

from ac_cli.main import app

API_BASE = "http://test-api:8008"

MOCK_CONFIG = {
    "api_url": API_BASE,
    "access_token": "test-token",
    "refresh_token": "test-refresh-token",
    "supabase_url": "http://test-supabase",
    "supabase_anon_key": "test-anon-key",
}

# Every key one command must refuse before it builds a request header. The list
# covers each branch of header_safe_key: empty, outer whitespace, over the
# length bound, a control character and a non-ASCII character.
UNSENDABLE_KEYS = [
    "",
    " ",
    " delivery-42",
    "delivery-42 ",
    "x" * 256,
    "line\nbreak",
    "carriage\rreturn",
    "nul\x00byte",
    "tab\there",
    "del\x7f",
    "é",
]

WHOAMI_RESPONSE = {
    "user_id": "user-123",
    "organization_id": "org-456",
    "email": "test@example.com",
}


@pytest.fixture()
def mock_config():
    with patch("ac_cli.client.load_config", return_value=MOCK_CONFIG):
        yield MOCK_CONFIG


@pytest.fixture()
def mock_api():
    with respx.mock(base_url=API_BASE, assert_all_called=False) as router:
        yield router


@pytest.fixture()
def invoke(mock_config, mock_api):
    """Convenience fixture: returns a function that invokes the CLI app."""
    runner = CliRunner()

    def _invoke(args, input=None):
        return runner.invoke(app, args, input=input)

    return _invoke


@pytest.fixture()
def table_column():
    """Returns a reader that joins one column of a rendered table.

    A cell that folds spans two or more lines. The reader joins the parts, so
    a test asserts the whole value and not one of its parts.

    The reader takes the text `print_table` wrote and a zero based column
    index. It answers that column with the fold points removed.

    ⚠️ **The reader reads the default box only.** It finds a body row by the
    `│` that starts it, and it splits that row on the same character. A table
    with another `box` value gives a wrong answer, and so does a cell that
    holds a `│`. Neither raises.
    """

    def _read(output: str, index: int) -> str:
        parts = []
        for line in output.splitlines():
            if not line.startswith("│"):
                continue
            parts.append(line.split("│")[index + 1].strip())
        return "".join(parts)

    return _read
