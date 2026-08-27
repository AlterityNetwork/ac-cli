"""Tests for the agentic platform tool catalogue command.

`ac agentic tools list` reads `/api/v1/agentic/tools`, which answers the
catalogue an author picks `tool_ids` from. Staging serves no `/api/v1/agentic/`
path until the cutover, so the audit for this group runs against a branch API.
"""

import json

BASE = "/api/v1/agentic/tools"

SAMPLE = {
    "name": "crm.search_people",
    "description": (
        "Search the people of this organization. The free text matches a "
        "name, an email, a job title and a summary. Filter also by company "
        "id, by job title or by country. It answers at most 25 people, each "
        "with their name, title, company, email and country."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "additionalProperties": False,
    },
    "output_schema": {"type": "array", "items": {"type": "object"}},
    "side_effects": "read",
}


def test_tools_list(invoke, mock_api):
    mock_api.get(BASE).respond(200, json={"items": [SAMPLE]})

    result = invoke(["agentic", "tools", "list"])

    assert result.exit_code == 0
    assert "crm.search_people" in result.output


def test_tools_list_json_carries_both_schemas(invoke, mock_api):
    """The table drops the schemas, so `--json` is the only way to read them."""
    mock_api.get(BASE).respond(200, json={"items": [SAMPLE]})

    result = invoke(["agentic", "tools", "list", "--json"])

    assert result.exit_code == 0
    row = json.loads(result.output)["items"][0]
    assert row["input_schema"]["properties"] == {"query": {"type": "string"}}
    assert row["output_schema"]["type"] == "array"


def test_tools_list_sends_no_page_argument(invoke, mock_api):
    """The catalogue is not paginated. A cursor or a limit would 422."""
    route = mock_api.get(BASE).respond(200, json={"items": []})

    invoke(["agentic", "tools", "list"])

    assert route.called
    assert route.calls[0].request.url.params.multi_items() == []


def test_tools_list_renders_an_empty_catalogue(invoke, mock_api):
    """A deploy that declares no tool is not an error."""
    mock_api.get(BASE).respond(200, json={"items": []})

    result = invoke(["agentic", "tools", "list"])

    assert result.exit_code == 0
    assert "Tools (0)" in result.output


def test_tools_list_reports_a_server_refusal(invoke, mock_api):
    """Exit 1 and the reason on stdout.

    The stdout assertion is what separates a handled refusal from a crash. A
    `MarkupError` inside the renderer also exits 1, and it prints nothing, so
    the exit code alone answers the same for both.
    """
    mock_api.get(BASE).respond(500, json={"detail": "the registry did not build"})

    result = invoke(["agentic", "tools", "list"])

    assert result.exit_code == 1
    assert "the registry did not build" in result.output


def test_tools_list_json_reports_a_server_refusal(invoke, mock_api):
    """With --json a refusal is a JSON object, so a caller can parse it."""
    mock_api.get(BASE).respond(500, json={"detail": "the registry did not build"})

    result = invoke(["agentic", "tools", "list", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["error"] is True
    assert payload["status_code"] == 500
    assert payload["detail"] == "the registry did not build"


def test_tools_list_renders_a_write_tool(invoke, mock_api):
    """A picker warns on a write, so the effect column must carry the value."""
    write_tool = {
        **SAMPLE,
        "name": "crm.send_email",
        "description": "Send one email to one person.",
        "side_effects": "write",
    }
    mock_api.get(BASE).respond(200, json={"items": [write_tool]})

    result = invoke(["agentic", "tools", "list"])

    assert result.exit_code == 0
    # The row must carry both halves. The description is checked for the word
    # too, so a later fixture edit cannot answer this assertion by accident.
    assert "write" not in write_tool["description"]
    assert "crm.send_email" in result.output
    assert "write" in result.output


def test_tools_list_escapes_markup_in_a_description(invoke, mock_api):
    """A remote MCP server writes its own description, and rich reads markup.

    An unescaped `[id, name]` renders as nothing, so the reader reads a
    sentence the tool never declared. An unescaped `[/urgent]` raises
    MarkupError, and the command exits 1 with no output.
    """
    marked = {**SAMPLE, "description": "Answers [id, name] and [/urgent] rows."}
    mock_api.get(BASE).respond(200, json={"items": [marked]})

    result = invoke(["agentic", "tools", "list"])

    assert result.exit_code == 0
    assert "[id, name]" in result.output


# `mcp.<connection_slug>.<remote_name>`. The design doc records that this shape
# can pass 64 characters, so the table must not depend on a short id.
LONG_MCP_TOOL = {
    **SAMPLE,
    "name": "mcp.acme_zendesk_production.send_message_to_customer_with_attachment",
    "side_effects": "write",
}


def test_tools_list_renders_a_long_mcp_id_whole(monkeypatch, invoke, mock_api, table_column):
    """The id is the value a caller copies into `tool_ids`, so it never cuts.

    Pin the width. Rich reads the width of the real terminal, so an unpinned
    test stops proving anything on a wide screen or under `pytest -s`. Three
    columns at 80 leave the id about 32 characters, which is half of this name.
    """
    monkeypatch.setenv("COLUMNS", "80")
    mock_api.get(BASE).respond(200, json={"items": [LONG_MCP_TOOL]})

    result = invoke(["agentic", "tools", "list"])

    assert result.exit_code == 0
    assert "…" not in result.output
    assert table_column(result.output, 0) == LONG_MCP_TOOL["name"]


def test_tools_list_help_names_json_as_the_way_to_read_a_row(monkeypatch, invoke):
    """The help prose names `--json`, and not the options table alone.

    Typer lists every option, so a test for the flag name proves nothing. The
    table folds a long id over two or more lines. A reader who wants that row
    on one line needs the prose to say which flag answers it.

    Pin the width. Typer wraps the prose to the terminal, and a narrow screen
    would break the sentence across two lines.
    """
    monkeypatch.setenv("COLUMNS", "100")

    result = invoke(["agentic", "tools", "list", "--help"])

    assert result.exit_code == 0
    assert "Use `--json` to read a whole row." in result.output
