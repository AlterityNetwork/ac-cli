"""Tests for the agentic people commands.

`ac agentic people profile` reads what the global people cache holds for one
LinkedIn profile: the work history and the affiliations outside the main job.
"""

import json

_PROFILE = "/api/v1/agentic/people/profile"

LINKEDIN_URL = "https://www.linkedin.com/in/rorysutherland"

SAMPLE_PROFILE = {
    "linkedin_url": LINKEDIN_URL,
    "experience_history": [
        {
            "title": "Vice Chairman",
            "company": "Ogilvy",
            "start_date": "2005-01-01",
            "kind": "employment",
        }
    ],
    "affiliations": [
        {
            "kind": "advisory",
            "name": "Daivid",
            "role": "Strategic Advisor",
            "current": True,
            "source_url": "https://example.com/daivid",
        }
    ],
    "affiliations_checked_at": "2026-11-03T12:00:00Z",
}


def test_profile_sends_the_linkedin_url_as_a_query_param(invoke, mock_api):
    route = mock_api.get(_PROFILE).respond(200, json=SAMPLE_PROFILE)

    result = invoke(["agentic", "people", "profile", "--linkedin-url", LINKEDIN_URL])

    assert result.exit_code == 0
    assert route.calls[0].request.url.params.multi_items() == [("linkedin_url", LINKEDIN_URL)]


def test_profile_prints_the_history_and_the_affiliations(invoke, mock_api):
    mock_api.get(_PROFILE).respond(200, json=SAMPLE_PROFILE)

    result = invoke(["agentic", "people", "profile", "--linkedin-url", LINKEDIN_URL])

    assert result.exit_code == 0
    assert "2026-11-03T12:00:00Z" in result.output
    assert "Experience" in result.output
    assert "Ogilvy" in result.output
    assert "employment" in result.output
    assert "Affiliations" in result.output
    assert "Daivid" in result.output
    assert "advisory" in result.output
    assert "yes" in result.output


def test_profile_says_when_the_deep_dive_found_nothing(invoke, mock_api):
    """An empty list with a check time is an answer: the deep dive found nothing."""
    mock_api.get(_PROFILE).respond(
        200,
        json={
            "linkedin_url": LINKEDIN_URL,
            "experience_history": [],
            "affiliations": [],
            "affiliations_checked_at": "2026-11-03T16:00:00Z",
        },
    )

    result = invoke(["agentic", "people", "profile", "--linkedin-url", LINKEDIN_URL])

    assert result.exit_code == 0
    assert "No experience history" in result.output
    assert "No affiliations found" in result.output
    assert "not checked" not in result.output


def test_profile_says_when_no_deep_dive_ran(invoke, mock_api):
    """No check time means no deep dive ran, which is not an empty answer."""
    mock_api.get(_PROFILE).respond(
        200,
        json={
            "linkedin_url": LINKEDIN_URL,
            "experience_history": [],
            "affiliations": [],
        },
    )

    result = invoke(["agentic", "people", "profile", "--linkedin-url", LINKEDIN_URL])

    assert result.exit_code == 0
    assert "Affiliations not checked yet" in result.output
    assert "No affiliations found" not in result.output


def test_profile_json_returns_the_body(invoke, mock_api):
    mock_api.get(_PROFILE).respond(200, json=SAMPLE_PROFILE)

    result = invoke(["agentic", "people", "profile", "--linkedin-url", LINKEDIN_URL, "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == SAMPLE_PROFILE


def test_profile_reports_a_cache_miss_as_not_found(invoke, mock_api):
    mock_api.get(_PROFILE).respond(404, json={"detail": "person not found"})

    result = invoke(["agentic", "people", "profile", "--linkedin-url", LINKEDIN_URL, "--json"])

    # 3 is what _EXIT_CODES maps a 404 to, and a script reads that code.
    assert result.exit_code == 3
    assert json.loads(result.output)["status_code"] == 404


def test_profile_reports_a_plan_without_the_people_apps(invoke, mock_api):
    mock_api.get(_PROFILE).respond(402, json={"detail": "People Search is not in your plan"})

    result = invoke(["agentic", "people", "profile", "--linkedin-url", LINKEDIN_URL, "--json"])

    # 6 is what _EXIT_CODES maps a plan refusal to.
    assert result.exit_code == 6
    assert json.loads(result.output)["status_code"] == 402


def test_profile_reports_a_url_that_is_not_a_profile(invoke, mock_api):
    mock_api.get(_PROFILE).respond(422, json={"detail": "not a LinkedIn profile URL"})

    result = invoke(
        ["agentic", "people", "profile", "--linkedin-url", "https://example.com", "--json"]
    )

    assert result.exit_code == 2
    assert json.loads(result.output)["status_code"] == 422


def test_profile_needs_the_linkedin_url(invoke, mock_api):
    route = mock_api.get(_PROFILE).respond(200, json=SAMPLE_PROFILE)

    result = invoke(["agentic", "people", "profile"])

    assert result.exit_code == 2
    assert not route.called
