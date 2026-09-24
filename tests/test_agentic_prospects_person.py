"""A person prospect prints its person, and no company."""

import json

from ac_cli.commands.prospects import _SUMMARY_FIELDS
from tests.test_agentic_prospects import BASE, PROSPECT_ID, SUMMARY

_COLUMNS = [key for key, _ in _SUMMARY_FIELDS]
SUBJECT_COLUMN = _COLUMNS.index("subject_type")
PERSON_COLUMN = _COLUMNS.index("person_name")

PERSON_SUBJECT = {
    "id": "77777777-7777-4777-8777-777777777777",
    "linkedin_url": None,
    "full_name": "Jane Doe",
    "avatar_url": None,
    "current_title": "Marketing creator",
    "current_company_text": None,
    "location": "Bristol",
    "country": "United Kingdom",
    "email": None,
    "personal_website": "https://janedoe.example",
    "social_profile_url": "https://x.com/janedoe",
    "last_enriched_at": "2026-09-25T09:00:00Z",
}
PERSON_SUMMARY = {
    **SUMMARY,
    "subject_type": "person",
    "person": PERSON_SUBJECT,
    "company_name": None,
    "company_domain": None,
    "company_logo_url": None,
    "company_industry": None,
    "company_location": None,
}
PERSON_DETAIL = {**PERSON_SUMMARY, "company": None}
COMPANY_SUMMARY = {**SUMMARY, "subject_type": "company", "person": None}


def test_list_names_the_person_of_a_person_prospect(invoke, mock_api, table_column):
    mock_api.get(BASE).respond(
        200, json={"items": [PERSON_SUMMARY, COMPANY_SUMMARY], "next_cursor": None}
    )

    result = invoke(["agentic", "prospects", "list"])

    assert result.exit_code == 0
    # The helper joins the cells of one column, top row first, and a wrapped
    # cell loses its inner space.
    assert table_column(result.output, SUBJECT_COLUMN) == "personcompany"
    assert table_column(result.output, PERSON_COLUMN).replace(" ", "") == "JaneDoe"


def test_get_prints_the_person_and_no_company_block(invoke, mock_api):
    mock_api.get(f"{BASE}/{PROSPECT_ID}").respond(200, json=PERSON_DETAIL)

    result = invoke(["agentic", "prospects", "get", PROSPECT_ID])

    assert result.exit_code == 0
    # A block header is a line of its own. A detail row ends its label with a
    # colon, so "Company:" is a row and "Company" is the block.
    lines = [line.strip() for line in result.output.splitlines()]
    assert "Person" in lines
    assert "Company" not in lines
    assert "Jane Doe" in result.output
    assert "janedoe.example" in result.output
    assert "Marketing creator" in result.output


def test_get_json_keeps_the_null_company(invoke, mock_api):
    mock_api.get(f"{BASE}/{PROSPECT_ID}").respond(200, json=PERSON_DETAIL)

    result = invoke(["agentic", "prospects", "get", PROSPECT_ID, "--json"])

    assert json.loads(result.output)["company"] is None
    assert json.loads(result.output)["person"]["full_name"] == "Jane Doe"
