"""Tests for the research of one Outreach enrollment and its part in a draft (ENG-3021)."""

import json

from tests.test_agentic_outreach import ACTION, ACTION_ID, ACTIONS

BASE = "/api/v1/agentic/outreach"
ENROLLMENT_ID = "22222222-2222-4222-8222-222222222222"
RESEARCH_ID = "44444444-4444-4444-8444-444444444444"
COMMAND = ["agentic", "outreach", "enrollments", "research", ENROLLMENT_ID]

RESEARCH = {
    "id": RESEARCH_ID,
    "enrollment_id": ENROLLMENT_ID,
    "strategy_id": "55555555-5555-4555-8555-555555555555",
    "strategy_version": 2,
    "run_id": None,
    "status": "ready",
    "hook": "They launched a [TikTok] ad.",
    "findings": [
        {
            "key": "r1",
            "text": "Launched a TikTok ad.",
            "source_url": "https://acme.example/news",
            "observed_at": "2026-10-01",
            "tool": "research.fetch_page",
        },
        {
            "key": "r2",
            "text": "Hires 2 analysts.",
            "source_url": "https://acme.example/jobs",
            "observed_at": None,
            "tool": "research.search_web",
        },
    ],
    "cost_cents": 12.5,
    "created_at": "2026-11-18T09:00:00Z",
}


class TestEnrollmentResearch:
    def test_research_prints_the_status_the_hook_and_each_finding(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}/research").respond(
            200, json=RESEARCH
        )

        result = invoke(COMMAND)

        assert result.exit_code == 0, result.output
        assert route.called
        for text in (
            "ready",
            "They launched a [TikTok] ad.",
            "2026-10-01",
            "Launched a TikTok ad.",
            "https://acme.example/news",
            "undated",
            "Hires 2 analysts.",
        ):
            assert text in result.output

    def test_a_thin_research_says_it_has_no_finding(self, invoke, mock_api):
        mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}/research").respond(
            200, json={**RESEARCH, "status": "thin", "hook": None, "findings": []}
        )

        result = invoke(COMMAND)

        assert result.exit_code == 0, result.output
        assert "thin" in result.output
        assert "No finding" in result.output
        assert "None" not in result.output

    def test_research_prints_json(self, invoke, mock_api):
        mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}/research").respond(200, json=RESEARCH)

        result = invoke([*COMMAND, "--json"])

        assert result.exit_code == 0, result.output
        assert json.loads(result.output) == RESEARCH

    def test_no_research_gets_the_404_exit_code(self, invoke, mock_api):
        mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}/research").respond(
            404, json={"detail": "Outreach research not found"}
        )

        result = invoke(COMMAND)

        assert result.exit_code == 3


class TestDraftResearch:
    def test_get_prints_the_research_and_the_url_of_a_research_fact(self, invoke, mock_api):
        item = {
            **ACTION,
            "facts_used": [
                {
                    "source": "research",
                    "label": "2026-10-01: Launched a TikTok ad.",
                    "ref_kind": "outreach.research",
                    "ref_id": RESEARCH_ID,
                    "url": "https://acme.example/news",
                },
                {"source": "crm", "label": "title: CMO", "ref_kind": "crm.person", "ref_id": "p"},
            ],
            "research": {
                "id": RESEARCH_ID,
                "status": "ready",
                "hook": "They launched a TikTok ad.",
                "findings": [],
            },
        }
        mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=item)

        result = invoke(["agentic", "outreach", "drafts", "get", ACTION_ID])

        assert result.exit_code == 0, result.output
        assert (
            "research · 2026-10-01: Launched a TikTok ad. · https://acme.example/news"
            in result.output
        )
        assert "crm · title: CMO" in result.output
        assert "Research: ready · They launched a TikTok ad." in result.output

    def test_get_prints_a_failed_research(self, invoke, mock_api):
        item = {
            **ACTION,
            "research": {"id": RESEARCH_ID, "status": "failed", "hook": None, "findings": []},
        }
        mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json=item)

        result = invoke(["agentic", "outreach", "drafts", "get", ACTION_ID])

        assert result.exit_code == 0, result.output
        assert "Research: failed" in result.output
        assert "None" not in result.output

    def test_get_with_no_research_prints_no_research_line(self, invoke, mock_api):
        mock_api.get(f"{ACTIONS}/{ACTION_ID}").respond(200, json={**ACTION, "research": None})

        result = invoke(["agentic", "outreach", "drafts", "get", ACTION_ID])

        assert result.exit_code == 0, result.output
        assert "Research:" not in result.output
