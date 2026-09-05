"""The rule that no print gives the markup parser text the CLI did not write.

ENG-2134 closed the shared helpers. ENG-2147 closed the command modules. Three
checks hold the boundary:

1. The AST gate reads every print argument in `src/ac_cli`.
2. Every `styled` template in the source renders a bracketed value literally.
   The parameter is the file, so a failure names the file that broke.
3. The two reported commands print a bracketed value and exit 0.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

from ac_cli.formatting import styled
from tests.conftest import WHOAMI_RESPONSE

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_markup  # noqa: E402

SRC = Path(__file__).resolve().parent.parent / "src" / "ac_cli"

# A value that raised MarkupError, and one that rendered without its brackets.
CLOSE_TAG = "Acme [/beta] Ltd"
OPEN_TAG = "see the [urgent] note"


# -- the gate -------------------------------------------------------------------


def test_no_print_argument_reaches_the_markup_parser():
    """A grep does not find these, so the gate walks the tree.

    Adding an f-string to an rprint call fails here. Wrap the value in
    as_text(), or write the line with styled().
    """
    messages = [
        message for file in sorted(SRC.rglob("*.py")) for message in check_markup.check(file)
    ]
    assert messages == []


def test_the_gate_fails_on_an_unwrapped_value(tmp_path):
    """A gate nobody has seen fail proves nothing, so make it fail."""
    module = tmp_path / "sample.py"
    module.write_text('rprint(f"[green]Created:[/green] {name}")\n')
    assert check_markup.check(module) != []


def test_the_gate_passes_a_wrapped_value(tmp_path):
    module = tmp_path / "sample.py"
    module.write_text('rprint(styled("[green]Created:[/green] {}", name))\n')
    assert check_markup.check(module) == []


def test_the_gate_fails_a_template_that_is_not_a_literal(tmp_path):
    """A template from somewhere else is the fault the gate exists for."""
    module = tmp_path / "sample.py"
    module.write_text('rprint(styled(row["template"], name))\n')
    assert check_markup.check(module) != []


# -- every styled template in the source ----------------------------------------


def _templates(path: Path) -> list[str]:
    """Answers the template of each styled call in one file."""
    found = []
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Name) and func.id == "styled"):
            continue
        if node.args and isinstance(node.args[0], ast.Constant):
            found.append(node.args[0].value)
    return found


_FILES_WITH_TEMPLATES = sorted(path for path in SRC.rglob("*.py") if _templates(path))


@pytest.mark.parametrize("path", _FILES_WITH_TEMPLATES, ids=lambda p: str(p.relative_to(SRC)))
def test_every_styled_template_renders_a_bracketed_value(path):
    """One converted file, and every line it prints.

    A close tag raised MarkupError, so the command exited 1 with no output. An
    open tag rendered without the bracketed word, so the reader read a value
    the record does not hold. Both survive now.
    """
    for template in _templates(path):
        places = template.count("{}")
        for value in (CLOSE_TAG, OPEN_TAG):
            rendered = styled(template, *[value] * places).plain
            assert rendered.count(value) == places, (template, rendered)


def test_the_source_holds_a_template_to_check():
    """A wrong extraction would make the parametrized test vacuous."""
    assert len(_FILES_WITH_TEMPLATES) > 40


# -- the two reported commands --------------------------------------------------


SAMPLE_COMPANY = {
    "id": "comp_1",
    "name": CLOSE_TAG,
    "industry": "SaaS",
    "website": "https://acme.com",
}


def test_companies_create_prints_a_bracketed_name(invoke, mock_api):
    """The reported fault: `create` exited 1 and printed nothing at all."""
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/crm/companies").respond(201, json=SAMPLE_COMPANY)

    result = invoke(["crm", "companies", "create", "--name", CLOSE_TAG])

    assert result.exit_code == 0
    assert CLOSE_TAG in result.output


def _thread(body: str) -> dict:
    return {
        "data": [
            {
                "id": "comm_1",
                "direction": "inbound",
                "from_name": "Jane Doe",
                "to_emails": ["sales@acme.com"],
                "subject": "Pricing",
                "content": body,
                "communication_date": "2026-01-01T09:00:00Z",
                "sentiment": "positive",
            }
        ],
        "total": 1,
        "limit": 200,
        "offset": 0,
        "has_more": False,
    }


def test_thread_renders_a_close_tag_in_a_message_body(invoke, mock_api):
    """A customer writes `see the [/pricing] page`, and the command exited 1."""
    body = "see the [/pricing] page"
    mock_api.get("/api/v1/crm/communications/thread/thread_1").respond(200, json=_thread(body))

    result = invoke(["crm", "comms", "thread", "thread_1"])

    assert result.exit_code == 0
    assert body in result.output


def test_thread_keeps_a_bracketed_word_in_a_message_body(invoke, mock_api):
    """This one exited 0 and dropped the word, which is the quieter fault."""
    body = "this is [urgent] please read"
    mock_api.get("/api/v1/crm/communications/thread/thread_1").respond(200, json=_thread(body))

    result = invoke(["crm", "comms", "thread", "thread_1"])

    assert result.exit_code == 0
    assert "[urgent]" in result.output


def test_thread_shows_a_control_byte_in_a_message_body(invoke, mock_api):
    """An API value must not repaint the terminal. See formatting._visible."""
    mock_api.get("/api/v1/crm/communications/thread/thread_1").respond(
        200, json=_thread("red \x1b[41m now")
    )

    result = invoke(["crm", "comms", "thread", "thread_1"])

    assert result.exit_code == 0
    assert "\x1b[41m" not in result.output
    assert "\\x1b" in result.output


def test_thread_json_is_unchanged(invoke, mock_api):
    """`--json` never rendered markup, so the escape must not reach it."""
    body = "see the [/pricing] page"
    mock_api.get("/api/v1/crm/communications/thread/thread_1").respond(200, json=_thread(body))

    result = invoke(["crm", "comms", "thread", "thread_1", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output)["data"][0]["content"] == body


# -- the connection-error branch the commands copied ----------------------------
#
# A command that uploads a file builds its own request, so it does not take
# _api_request. Each one copied the branch, and each copy printed the error
# text as markup. They now take one function. See _handle_connection_error.


def test_csv_parse_renders_a_close_tag_in_a_connection_error(invoke, mock_api, tmp_path):
    """A non-HTTP responder puts its own bytes in the transport error text."""
    import httpx

    mock_api.post("/api/v1/workflows/csv/parse-companies").mock(
        side_effect=httpx.ConnectError("failed to reach [/urgent] host")
    )
    csv_file = tmp_path / "companies.csv"
    csv_file.write_text("name,website\nAcme Corp,https://acme.com\n")

    result = invoke(["workflows", "csv-parse", str(csv_file)])

    assert result.exit_code == 1
    assert "[/urgent]" in result.output


def test_csv_parse_answers_json_for_a_connection_error(invoke, mock_api, tmp_path):
    """The shared branch reads the JSON mode, where the copy printed text."""
    import httpx

    mock_api.post("/api/v1/workflows/csv/parse-companies").mock(
        side_effect=httpx.ConnectError("failed to reach host")
    )
    csv_file = tmp_path / "companies.csv"
    csv_file.write_text("name,website\nAcme Corp,https://acme.com\n")

    result = invoke(["workflows", "csv-parse", str(csv_file), "--json"])

    assert result.exit_code == 1
    assert json.loads(result.output)["error"] is True
