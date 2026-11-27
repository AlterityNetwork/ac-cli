"""Tests for the Outreach strategy commands and `--strategy` on campaigns."""

import json
from unittest.mock import patch

import httpx

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
    return json.loads(route.calls.last.request.content)


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

    def test_create_sends_message_templates_and_shows_them(self, invoke, mock_api):
        template = {
            "name": "Checkout audit",
            "channel": "email",
            "subject": "{{first name}}, your checkout",
            "body": "Hi {{first name}}, {{one checkout problem}}.",
        }
        route = mock_api.post(f"{BASE}/strategies").respond(
            201, json={**STRATEGY, "message_templates": [{"id": STRATEGY_ID, **template}]}
        )

        result = invoke(_cmd("create", "--name", "Templates", "--template", json.dumps(template)))

        assert result.exit_code == 0, result.output
        assert _body(route) == {"name": "Templates", "message_templates": [template]}
        assert "Checkout audit (email)" in result.output

    def test_create_refuses_a_template_that_is_not_a_json_object(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/strategies").respond(201, json=STRATEGY)

        for bad in ("not json", "[]", '{"name": "A", "channel": "fax", "body": "Hi"}'):
            result = invoke(_cmd("create", "--name", "A", "--template", bad))
            assert result.exit_code == 2, bad
        assert not route.called

    def test_update_replaces_or_clears_the_templates(self, invoke, mock_api):
        route = mock_api.patch(f"{BASE}/strategies/{STRATEGY_ID}").respond(200, json=STRATEGY)
        template = {"name": "Connect", "channel": "linkedin", "body": "Hi {{first name}}"}

        replaced = invoke(_cmd("update", STRATEGY_ID, "--template", json.dumps(template)))
        assert replaced.exit_code == 0, replaced.output
        assert _body(route) == {"message_templates": [template]}

        cleared = invoke(_cmd("update", STRATEGY_ID, "--no-templates"))
        assert cleared.exit_code == 0, cleared.output
        assert _body(route) == {"message_templates": []}

    def test_update_refuses_a_template_and_no_templates_without_a_call(self, invoke, mock_api):
        route = mock_api.patch(f"{BASE}/strategies/{STRATEGY_ID}").respond(200, json=STRATEGY)
        template = json.dumps({"name": "A", "channel": "email", "body": "Hi"})

        result = invoke(_cmd("update", STRATEGY_ID, "--template", template, "--no-templates"))

        assert result.exit_code == 2
        assert not route.called

    def test_create_with_no_offers_pitches_nothing(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/strategies").respond(201, json=STRATEGY)

        result = invoke(_cmd("create", "--name", "Goal only", "--no-offers"))

        assert result.exit_code == 0, result.output
        assert _body(route) == {"name": "Goal only", "use_offers": False}

    def test_no_offers_with_an_offer_refuses_without_a_call(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/strategies").respond(201, json=STRATEGY)

        result = invoke(_cmd("create", "--name", "A", "--no-offers", "--offer-id", OFFER_ID))

        assert result.exit_code == 2
        assert not route.called

    def test_update_turns_offers_on_and_off(self, invoke, mock_api):
        route = mock_api.patch(f"{BASE}/strategies/{STRATEGY_ID}").respond(200, json=STRATEGY)

        assert invoke(_cmd("update", STRATEGY_ID, "--no-offers")).exit_code == 0
        assert _body(route) == {"use_offers": False}
        assert invoke(_cmd("update", STRATEGY_ID, "--use-offers")).exit_code == 0
        assert _body(route) == {"use_offers": True}

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


TEMPLATE = {
    "key": "new-funding",
    "name": "New funding",
    "goal": "Book a 20 min intro call",
    "angle": "Their latest funding round.",
    "research_tools": ["research.search_web", "research.search_company"],
}


class TestStrategyTemplates:
    def test_templates_prints_the_ready_made_strategies(self, invoke, mock_api, table_column):
        route = mock_api.get(f"{BASE}/strategy-templates").respond(
            200, json={"items": [TEMPLATE], "total": 1}
        )

        result = invoke(_cmd("templates"))

        assert result.exit_code == 0, result.output
        assert route.called
        assert table_column(result.output, 0).replace(" ", "") == "new-funding"
        assert "New funding" in result.output

    def test_templates_json(self, invoke, mock_api):
        mock_api.get(f"{BASE}/strategy-templates").respond(
            200, json={"items": [TEMPLATE], "total": 1}
        )

        result = invoke(_cmd("templates", "--json"))

        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["items"][0]["key"] == "new-funding"

    def test_create_from_template_copies_it(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/strategy-templates/new-funding/copy").respond(
            201, json=STRATEGY
        )

        result = invoke(_cmd("create", "--from-template", "new-funding"))

        assert result.exit_code == 0, result.output
        assert _body(route) == {}
        assert STRATEGY_ID in result.output

    def test_create_from_template_sends_the_name_and_the_offer(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/strategy-templates/new-funding/copy").respond(
            201, json=STRATEGY
        )

        result = invoke(
            _cmd(
                "create",
                "--from-template",
                "new-funding",
                "--name",
                "Series A founders",
                "--offer-id",
                OFFER_ID,
                "--json",
            )
        )

        assert result.exit_code == 0, result.output
        assert _body(route) == {"name": "Series A founders", "offer_id": OFFER_ID}
        assert json.loads(result.output)["id"] == STRATEGY_ID

    def test_create_from_an_unknown_template_exits_3(self, invoke, mock_api):
        mock_api.post(f"{BASE}/strategy-templates/nope/copy").respond(
            404, json={"detail": "not found"}
        )

        assert invoke(_cmd("create", "--from-template", "nope")).exit_code == 3

    def test_create_from_template_with_a_taken_name_exits_5(self, invoke, mock_api):
        mock_api.post(f"{BASE}/strategy-templates/new-funding/copy").respond(
            409, json={"detail": "taken", "code": "strategy_name_taken"}
        )

        result = invoke(_cmd("create", "--from-template", "new-funding", "--name", "A"))

        assert result.exit_code == 5

    def test_create_from_template_refuses_a_strategy_field(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/strategy-templates/new-funding/copy").respond(
            201, json=STRATEGY
        )

        result = invoke(_cmd("create", "--from-template", "new-funding", "--goal", "G"))

        assert result.exit_code == 2
        assert not route.called

    def test_create_with_no_name_and_no_template_is_refused(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/strategies").respond(201, json=STRATEGY)

        result = invoke(_cmd("create", "--goal", "G"))

        assert result.exit_code == 2
        assert not route.called


DRAFT_ID = "77777777-7777-4777-8777-777777777777"
DRAFT_STRATEGY = {
    "name": "Shopify founders, checkout audit",
    "goal": "Book a 20 min intro call",
    "offer_id": OFFER_ID,
    "offer_name": "Free mobile checkout audit",
    "angle": "One problem on their mobile checkout.",
    "research_tools": ["research.fetch_page", "research.detect_technologies"],
}


class TestStrategyWrite:
    def test_write_starts_a_draft_and_prints_its_id(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/strategy-drafts").respond(202, json={"draft_id": DRAFT_ID})

        result = invoke(_cmd("write", "Book intro calls with Shopify founders."))

        assert result.exit_code == 0, result.output
        assert _body(route) == {"description": "Book intro calls with Shopify founders."}
        assert "regenerate" not in route.calls[0].request.url.params
        assert DRAFT_ID in result.output

    def test_write_regenerate_json(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/strategy-drafts").respond(202, json={"draft_id": DRAFT_ID})

        result = invoke(_cmd("write", "Book calls.", "--regenerate", "--json"))

        assert result.exit_code == 0, result.output
        assert route.calls[0].request.url.params["regenerate"] == "true"
        assert json.loads(result.output) == {"draft_id": DRAFT_ID}

    def test_write_wait_polls_until_ready_and_prints_the_strategy(self, invoke, mock_api):
        mock_api.post(f"{BASE}/strategy-drafts").respond(202, json={"draft_id": DRAFT_ID})
        poll = mock_api.get(f"{BASE}/strategy-drafts/{DRAFT_ID}").mock(
            side_effect=[
                httpx.Response(200, json={"draft_id": DRAFT_ID, "status": "pending"}),
                httpx.Response(
                    200,
                    json={"draft_id": DRAFT_ID, "status": "ready", "strategy": DRAFT_STRATEGY},
                ),
            ]
        )

        with patch("ac_cli.commands.outreach.strategies.time.sleep"):
            result = invoke(_cmd("write", "Book calls.", "--wait"))

        assert result.exit_code == 0, result.output
        assert poll.call_count == 2
        assert "Shopify founders, checkout audit" in result.output
        assert "Free mobile checkout audit" in result.output
        assert "research.fetch_page" in result.output

    def test_write_wait_json_prints_the_final_state(self, invoke, mock_api):
        mock_api.post(f"{BASE}/strategy-drafts").respond(202, json={"draft_id": DRAFT_ID})
        mock_api.get(f"{BASE}/strategy-drafts/{DRAFT_ID}").respond(
            200, json={"draft_id": DRAFT_ID, "status": "ready", "strategy": DRAFT_STRATEGY}
        )

        with patch("ac_cli.commands.outreach.strategies.time.sleep"):
            result = invoke(_cmd("write", "Book calls.", "--wait", "--json"))

        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["strategy"]["offer_id"] == OFFER_ID

    def test_write_wait_prints_a_failure(self, invoke, mock_api):
        mock_api.post(f"{BASE}/strategy-drafts").respond(202, json={"draft_id": DRAFT_ID})
        mock_api.get(f"{BASE}/strategy-drafts/{DRAFT_ID}").respond(
            200, json={"draft_id": DRAFT_ID, "status": "failed", "reason": "writer_empty"}
        )

        with patch("ac_cli.commands.outreach.strategies.time.sleep"):
            result = invoke(_cmd("write", "Book calls.", "--wait"))

        assert result.exit_code == 1
        assert "writer_empty" in result.output
        assert "--regenerate" in result.output

    def test_write_refused_exits_4(self, invoke, mock_api):
        mock_api.post(f"{BASE}/strategy-drafts").respond(
            403, json={"detail": "not available", "code": "strategy_draft_refused"}
        )

        assert invoke(_cmd("write", "Book calls.")).exit_code == 4

    def test_write_refuses_a_blank_or_long_description(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/strategy-drafts").respond(202, json={"draft_id": DRAFT_ID})

        assert invoke(_cmd("write", "   ")).exit_code == 2
        assert invoke(_cmd("write", "x" * 1001)).exit_code == 2
        assert not route.called

    def test_write_wait_timeout_keeps_waiting_without_regenerate(self, invoke, mock_api):
        mock_api.post(f"{BASE}/strategy-drafts").respond(202, json={"draft_id": DRAFT_ID})
        mock_api.get(f"{BASE}/strategy-drafts/{DRAFT_ID}").respond(
            200, json={"draft_id": DRAFT_ID, "status": "pending"}
        )

        with (
            patch("ac_cli.commands.outreach.strategies.time.sleep"),
            patch(
                "ac_cli.commands.outreach.strategies.time.monotonic",
                side_effect=[0.0, 0.0, 999.0],
            ),
        ):
            result = invoke(_cmd("write", "Book calls.", "--wait"))

        assert result.exit_code == 1
        assert "pending" in result.output
        assert "run the same command again" in result.output
        assert "--regenerate" not in result.output
