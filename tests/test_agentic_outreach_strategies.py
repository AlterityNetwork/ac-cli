"""Tests for the Outreach strategy commands and `--strategy` on campaigns."""

import json

BASE = "/api/v1/agentic/outreach"
STRATEGY_ID = "66666666-6666-4666-8666-666666666666"
OFFER_ID = "12121212-1212-4212-8212-121212121212"
CAMPAIGN_ID = "33333333-3333-4333-8333-333333333333"

STRATEGY = {
    "id": STRATEGY_ID,
    "name": "Website teardown",
    "goal": "Book a 20 min intro call",
    "offer_id": OFFER_ID,
    "offer_name": "Free mobile checkout audit",
    "angle": "Open with one checkout bug.",
    "research_tools": ["research.fetch_page", "research.detect_technologies"],
    "example_messages": ["Hi Ana"],
    "max_research_cents": 40,
    "version": 2,
    "archived_at": None,
    "created_by": "99999999-9999-4999-8999-999999999999",
    "created_at": "2026-11-18T10:00:00Z",
    "updated_at": "2026-11-18T10:00:00Z",
    "used_by_campaigns": 2,
}
CAMPAIGN = {
    "id": CAMPAIGN_ID,
    "name": "Q4 intro",
    "status": "paused",
    "description": "",
    "goal": "Book a 20 min intro call",
    "allowed_channels": ["email"],
    "max_touches": 5,
    "followup_min_days": 3,
    "followup_max_days": 7,
    "sender_user_id": None,
    "created_by": None,
    "created_at": "2026-11-18T10:00:00Z",
    "updated_at": "2026-11-18T10:00:00Z",
    "strategy_id": STRATEGY_ID,
    "strategy_name": "Website teardown",
}


def _body(route) -> dict:
    return json.loads(route.calls[0].request.content)


def _cmd(*args: str) -> list[str]:
    return ["agentic", "outreach", "strategies", *args]


class TestStrategies:
    def test_list_prints_the_live_strategies(self, invoke, mock_api, table_column):
        route = mock_api.get(f"{BASE}/strategies").respond(
            200,
            json={"items": [STRATEGY], "total": 1, "limit": 50, "offset": 0, "has_more": False},
        )

        result = invoke(_cmd("list"))

        assert result.exit_code == 0, result.output
        assert table_column(result.output, 1).replace(" ", "") == "Websiteteardown"
        assert dict(route.calls[0].request.url.params) == {"limit": "50", "offset": "0"}

    def test_list_passes_include_archived(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/strategies").respond(
            200, json={"items": [], "total": 0, "has_more": False}
        )

        result = invoke(_cmd("list", "--include-archived", "--json"))

        assert result.exit_code == 0, result.output
        assert route.calls[0].request.url.params["include_archived"] == "true"
        assert json.loads(result.output)["items"] == []

    def test_get_prints_the_strategy(self, invoke, mock_api):
        mock_api.get(f"{BASE}/strategies/{STRATEGY_ID}").respond(200, json=STRATEGY)

        result = invoke(_cmd("get", STRATEGY_ID))

        assert result.exit_code == 0, result.output
        for text in ("Free mobile checkout audit", "research.fetch_page", "Hi Ana"):
            assert text in result.output

    def test_get_json(self, invoke, mock_api):
        mock_api.get(f"{BASE}/strategies/{STRATEGY_ID}").respond(200, json=STRATEGY)

        result = invoke(_cmd("get", STRATEGY_ID, "--json"))

        assert json.loads(result.output) == STRATEGY

    def test_get_of_a_missing_strategy_exits_3(self, invoke, mock_api):
        mock_api.get(f"{BASE}/strategies/{STRATEGY_ID}").respond(404, json={"detail": "not found"})

        assert invoke(_cmd("get", STRATEGY_ID)).exit_code == 3

    def test_create_sends_every_given_field(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/strategies").respond(201, json=STRATEGY)

        result = invoke(
            _cmd(
                "create",
                "--name",
                "Website teardown",
                "--goal",
                "Book a call",
                "--offer-id",
                OFFER_ID,
                "--angle",
                "Open with one bug.",
                "--tool",
                "research.fetch_page",
                "--tool",
                "research.detect_technologies",
                "--example",
                "Hi Ana",
                "--max-research-cents",
                "40",
            )
        )

        assert result.exit_code == 0, result.output
        assert _body(route) == {
            "name": "Website teardown",
            "goal": "Book a call",
            "offer_id": OFFER_ID,
            "angle": "Open with one bug.",
            "research_tools": ["research.fetch_page", "research.detect_technologies"],
            "example_messages": ["Hi Ana"],
            "max_research_cents": 40,
        }
        assert "is created" in result.output

    def test_create_sends_only_the_name(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/strategies").respond(201, json=STRATEGY)

        result = invoke(_cmd("create", "--name", "Signals only", "--json"))

        assert result.exit_code == 0, result.output
        assert _body(route) == {"name": "Signals only"}
        assert json.loads(result.output)["id"] == STRATEGY_ID

    def test_create_refuses_an_unknown_tool_without_a_call(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/strategies").respond(201, json=STRATEGY)

        result = invoke(_cmd("create", "--name", "A", "--tool", "research.read_mind"))

        assert result.exit_code == 2
        assert not route.called

    def test_a_taken_name_exits_5(self, invoke, mock_api):
        mock_api.post(f"{BASE}/strategies").respond(
            409, json={"detail": "taken", "code": "strategy_name_taken"}
        )

        assert invoke(_cmd("create", "--name", "A")).exit_code == 5

    def test_an_offer_of_another_organization_exits_2(self, invoke, mock_api):
        mock_api.post(f"{BASE}/strategies").respond(
            422, json={"detail": {"code": "offer_not_found", "field": "offer_id"}}
        )

        assert invoke(_cmd("create", "--name", "A", "--offer-id", OFFER_ID)).exit_code == 2

    def test_update_sends_only_the_given_fields(self, invoke, mock_api):
        route = mock_api.patch(f"{BASE}/strategies/{STRATEGY_ID}").respond(200, json=STRATEGY)

        result = invoke(_cmd("update", STRATEGY_ID, "--angle", "Open with the stack."))

        assert result.exit_code == 0, result.output
        assert _body(route) == {"angle": "Open with the stack."}
        assert "Version" in result.output

    def test_update_clears_the_offer_the_cap_the_tools_and_the_examples(self, invoke, mock_api):
        route = mock_api.patch(f"{BASE}/strategies/{STRATEGY_ID}").respond(200, json=STRATEGY)

        result = invoke(
            _cmd(
                "update",
                STRATEGY_ID,
                "--no-offer",
                "--default-cap",
                "--no-tools",
                "--no-examples",
            )
        )

        assert result.exit_code == 0, result.output
        assert _body(route) == {
            "offer_id": None,
            "max_research_cents": None,
            "research_tools": [],
            "example_messages": [],
        }

    def test_update_refuses_an_offer_and_no_offer_without_a_call(self, invoke, mock_api):
        route = mock_api.patch(f"{BASE}/strategies/{STRATEGY_ID}").respond(200, json=STRATEGY)

        result = invoke(_cmd("update", STRATEGY_ID, "--offer-id", OFFER_ID, "--no-offer"))

        assert result.exit_code == 2
        assert not route.called

    def test_update_with_nothing_refuses_without_a_call(self, invoke, mock_api):
        route = mock_api.patch(f"{BASE}/strategies/{STRATEGY_ID}").respond(200, json=STRATEGY)

        result = invoke(_cmd("update", STRATEGY_ID))

        assert result.exit_code == 2
        assert not route.called

    def test_archive_asks_first(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/strategies/{STRATEGY_ID}/archive").respond(
            200, json=STRATEGY
        )

        result = invoke(_cmd("archive", STRATEGY_ID), input="n\n")

        assert result.exit_code == 1
        assert not route.called

    def test_archive_with_yes_posts(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/strategies/{STRATEGY_ID}/archive").respond(
            200, json={**STRATEGY, "archived_at": "2026-11-18T11:00:00Z"}
        )

        result = invoke(_cmd("archive", STRATEGY_ID, "--yes"))

        assert result.exit_code == 0, result.output
        assert route.called
        assert "is archived" in result.output

    def test_archive_of_a_used_strategy_exits_5(self, invoke, mock_api):
        mock_api.post(f"{BASE}/strategies/{STRATEGY_ID}/archive").respond(
            409, json={"detail": "in use", "code": "strategy_in_use"}
        )

        result = invoke(_cmd("archive", STRATEGY_ID, "--yes", "--json"))

        assert result.exit_code == 5
        assert json.loads(result.output)["status_code"] == 409


class TestCampaignStrategy:
    def test_create_sends_the_strategy(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/campaigns").respond(201, json=CAMPAIGN)

        result = invoke(
            [
                "agentic",
                "outreach",
                "campaigns",
                "create",
                "--name",
                "Q4 intro",
                "--strategy",
                STRATEGY_ID,
            ]
        )

        assert result.exit_code == 0, result.output
        assert _body(route) == {"name": "Q4 intro", "strategy_id": STRATEGY_ID}
        assert "Website teardown" in result.output

    def test_create_refuses_a_goal_with_a_strategy_without_a_call(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/campaigns").respond(201, json=CAMPAIGN)

        result = invoke(
            [
                "agentic",
                "outreach",
                "campaigns",
                "create",
                "--name",
                "Q4",
                "--goal",
                "G",
                "--strategy",
                STRATEGY_ID,
            ]
        )

        assert result.exit_code == 2
        assert not route.called

    def test_update_switches_the_strategy(self, invoke, mock_api):
        route = mock_api.patch(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)

        result = invoke(
            ["agentic", "outreach", "campaigns", "update", CAMPAIGN_ID, "--strategy", STRATEGY_ID]
        )

        assert result.exit_code == 0, result.output
        assert _body(route) == {"strategy_id": STRATEGY_ID}

    def test_get_prints_the_strategy(self, invoke, mock_api):
        mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)

        result = invoke(["agentic", "outreach", "campaigns", "get", CAMPAIGN_ID])

        assert result.exit_code == 0, result.output
        assert "Website teardown" in result.output
