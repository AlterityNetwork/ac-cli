"""Tests for admin subscriptions and subscription-plans commands."""

import json

SAMPLE_PLAN = {
    "id": "plan-1",
    "slug": "pro",
    "name": "Pro",
    "description": "Pro tier",
    "monthly_price_cents": 4900,
    "annual_price_cents": 49000,
    "features": {"seats": 10},
    "is_active": True,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}

SAMPLE_SUB = {
    "id": "sub-1",
    "organization_id": "org-1",
    "plan_id": "plan-1",
    "billing_period": "monthly",
    "status": "active",
    "started_at": "2026-04-01T00:00:00Z",
    "ended_at": None,
    "trial_ends_at": None,
    "stripe_customer_id": "cus_x",
    "stripe_subscription_id": "sub_x",
}


# -- Subscription plans ------------------------------------------------------


def test_plans_list(invoke, mock_api):
    mock_api.get("/api/v1/admin/subscription-plans").respond(200, json=[SAMPLE_PLAN])
    result = invoke(["admin", "subscription-plans", "list"])
    assert result.exit_code == 0
    assert "Pro" in result.output


def test_plans_get(invoke, mock_api):
    mock_api.get("/api/v1/admin/subscription-plans/plan-1").respond(200, json=SAMPLE_PLAN)
    result = invoke(["admin", "subscription-plans", "get", "plan-1"])
    assert result.exit_code == 0
    assert "Pro" in result.output


def test_plans_create(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/subscription-plans").respond(201, json=SAMPLE_PLAN)
    result = invoke(
        [
            "admin",
            "subscription-plans",
            "create",
            "--slug",
            "pro",
            "--name",
            "Pro",
            "--monthly-price-cents",
            "4900",
            "--annual-price-cents",
            "49000",
            "--features",
            '{"seats": 10}',
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["features"] == {"seats": 10}
    assert "Created plan" in result.output


def test_plans_create_invalid_features(invoke, mock_api):
    result = invoke(
        [
            "admin",
            "subscription-plans",
            "create",
            "--slug",
            "pro",
            "--name",
            "Pro",
            "--monthly-price-cents",
            "4900",
            "--annual-price-cents",
            "49000",
            "--features",
            "{not json",
        ]
    )
    assert result.exit_code == 2


def test_plans_update(invoke, mock_api):
    mock_api.patch("/api/v1/admin/subscription-plans/plan-1").respond(
        200, json={**SAMPLE_PLAN, "name": "Pro Plus"}
    )
    result = invoke(["admin", "subscription-plans", "update", "plan-1", "--name", "Pro Plus"])
    assert result.exit_code == 0
    assert "Updated plan" in result.output


def test_plans_update_no_fields(invoke, mock_api):
    result = invoke(["admin", "subscription-plans", "update", "plan-1"])
    assert result.exit_code == 1


def test_plans_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/admin/subscription-plans/plan-1").respond(204)
    result = invoke(["admin", "subscription-plans", "delete", "plan-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted plan" in result.output


def test_plans_delete_aborted(invoke, mock_api):
    result = invoke(["admin", "subscription-plans", "delete", "plan-1"], input="n\n")
    assert result.exit_code == 1


# -- Subscriptions -----------------------------------------------------------


def test_subscriptions_list(invoke, mock_api):
    mock_api.get("/api/v1/admin/subscriptions").respond(
        200, json={"data": [SAMPLE_SUB], "total": 1}
    )
    result = invoke(["admin", "subscriptions", "list"])
    assert result.exit_code == 0
    assert "Subscriptions" in result.output


def test_subscriptions_list_org_filter(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/subscriptions").respond(200, json={"data": [], "total": 0})
    result = invoke(
        ["admin", "subscriptions", "list", "--org-id", "org-1", "--status", "active", "--json"]
    )
    assert result.exit_code == 0
    url = str(route.calls.last.request.url)
    assert "organization_id=org-1" in url
    assert "status=active" in url


def test_subscriptions_get(invoke, mock_api):
    mock_api.get("/api/v1/admin/subscriptions/sub-1").respond(200, json=SAMPLE_SUB)
    result = invoke(["admin", "subscriptions", "get", "sub-1"])
    assert result.exit_code == 0
    assert "sub-1" in result.output


def test_subscriptions_get_shows_dunning_detail(invoke, mock_api):
    # The display keys must match the API response exactly; a typo renders a
    # blank row rather than failing, so pin the real values.
    overdue = {
        **SAMPLE_SUB,
        "status": "past_due",
        "unit_amount_cents": 25000,
        "dunning_attempt_count": 2,
        "dunning_next_attempt_at": "2026-07-11T23:55:00Z",
        "last_payment_error": "Invalid account.",
        "last_payment_decline_code": "invalid_account",
        "last_payment_advice_code": "do_not_try_again",
    }
    mock_api.get("/api/v1/admin/subscriptions/sub-1").respond(200, json=overdue)
    result = invoke(["admin", "subscriptions", "get", "sub-1"])
    assert result.exit_code == 0
    output = result.output
    assert "invalid_account" in output
    assert "do_not_try_again" in output
    assert "2026-07-11" in output
    assert "25000" in output


def test_subscriptions_create(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions").respond(201, json=SAMPLE_SUB)
    result = invoke(
        [
            "admin",
            "subscriptions",
            "create",
            "--org-id",
            "org-1",
            "--plan-id",
            "plan-1",
            "--billing-period",
            "monthly",
            "--started-at",
            "2026-04-01",
        ]
    )
    assert result.exit_code == 0
    assert "Created subscription" in result.output


def test_subscriptions_update(invoke, mock_api):
    mock_api.patch("/api/v1/admin/subscriptions/sub-1").respond(
        200, json={**SAMPLE_SUB, "plan_id": "plan-2"}
    )
    result = invoke(["admin", "subscriptions", "update", "sub-1", "--plan-id", "plan-2"])
    assert result.exit_code == 0
    assert "Updated subscription" in result.output


def test_subscriptions_update_rejects_system_managed_flags(invoke):
    # status is webhook-authoritative; stripe ids are system-managed (ENG-577).
    for flag, value in (
        ("--status", "active"),
        ("--stripe-customer-id", "cus_x"),
        ("--stripe-subscription-id", "sub_x"),
    ):
        result = invoke(["admin", "subscriptions", "update", "sub-1", flag, value])
        assert result.exit_code != 0, f"{flag} should no longer be accepted on update"


def test_subscriptions_create_rejects_stripe_flags(invoke):
    for flag in ("--stripe-customer-id", "--stripe-subscription-id"):
        result = invoke(
            [
                "admin",
                "subscriptions",
                "create",
                "--org-id",
                "org-1",
                "--plan-id",
                "plan-1",
                "--billing-period",
                "monthly",
                "--started-at",
                "2026-04-01",
                flag,
                "x",
            ]
        )
        assert result.exit_code != 0, f"{flag} should no longer be accepted on create"


def test_subscriptions_update_no_fields(invoke, mock_api):
    result = invoke(["admin", "subscriptions", "update", "sub-1"])
    assert result.exit_code == 1


def test_subscriptions_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/admin/subscriptions/sub-1").respond(204)
    result = invoke(["admin", "subscriptions", "delete", "sub-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted subscription" in result.output


def test_subscriptions_delete_aborted(invoke, mock_api):
    result = invoke(["admin", "subscriptions", "delete", "sub-1"], input="n\n")
    assert result.exit_code == 1


def test_subscriptions_create_with_custom_pricing(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/subscriptions").respond(201, json=SAMPLE_SUB)
    result = invoke(
        [
            "admin",
            "subscriptions",
            "create",
            "--org-id",
            "org-1",
            "--plan-id",
            "plan-1",
            "--billing-period",
            "monthly",
            "--started-at",
            "2026-04-01",
            "--custom-price-cents",
            "25000",
            "--currency",
            "gbp",
            "--coupon",
            "FOUNDER50",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["custom_price_cents"] == 25000
    assert body["currency"] == "gbp"
    assert body["coupon"] == "FOUNDER50"


def test_subscriptions_update_with_custom_pricing(invoke, mock_api):
    route = mock_api.patch("/api/v1/admin/subscriptions/sub-1").respond(200, json=SAMPLE_SUB)
    result = invoke(["admin", "subscriptions", "update", "sub-1", "--custom-price-cents", "25000"])
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["custom_price_cents"] == 25000


def test_subscriptions_create_with_manual_billing_mode(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/subscriptions").respond(201, json=SAMPLE_SUB)
    result = invoke(
        [
            "admin",
            "subscriptions",
            "create",
            "--org-id",
            "org-1",
            "--plan-id",
            "plan-1",
            "--billing-period",
            "monthly",
            "--started-at",
            "2026-04-01",
            "--billing-mode",
            "manual",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["billing_mode"] == "manual"


def test_subscriptions_update_billing_mode(invoke, mock_api):
    route = mock_api.patch("/api/v1/admin/subscriptions/sub-1").respond(200, json=SAMPLE_SUB)
    result = invoke(["admin", "subscriptions", "update", "sub-1", "--billing-mode", "manual"])
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["billing_mode"] == "manual"


def test_subscriptions_activate_billing_with_yes(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions/sub-1/activate-billing").respond(
        200, json={**SAMPLE_SUB, "status": "active"}
    )
    result = invoke(["admin", "subscriptions", "activate-billing", "sub-1", "--yes"])
    assert result.exit_code == 0
    assert "Activated" in result.output


def test_subscriptions_activate_billing_aborted(invoke, mock_api):
    result = invoke(["admin", "subscriptions", "activate-billing", "sub-1"], input="n\n")
    assert result.exit_code == 1


def test_subscriptions_activate_billing_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions/sub-1/activate-billing").respond(
        200,
        json={**SAMPLE_SUB, "status": "incomplete", "latest_invoice_url": "https://pay/x"},
    )
    result = invoke(["admin", "subscriptions", "activate-billing", "sub-1", "--yes", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "incomplete"


def test_subscriptions_link_with_yes(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/subscriptions/sub-1/link").respond(
        200, json={**SAMPLE_SUB, "stripe_subscription_id": "sub_live_1"}
    )
    result = invoke(["admin", "subscriptions", "link", "sub-1", "--sid", "sub_live_1", "--yes"])
    assert result.exit_code == 0
    assert "Linked" in result.output
    body = json.loads(route.calls.last.request.content)
    assert body == {"stripe_subscription_id": "sub_live_1"}


def test_subscriptions_link_aborted(invoke, mock_api):
    result = invoke(
        ["admin", "subscriptions", "link", "sub-1", "--sid", "sub_live_1"],
        input="n\n",
    )
    assert result.exit_code == 1


def test_subscriptions_link_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions/sub-1/link").respond(
        200, json={**SAMPLE_SUB, "stripe_subscription_id": "sub_live_1"}
    )
    result = invoke(
        [
            "admin",
            "subscriptions",
            "link",
            "sub-1",
            "--sid",
            "sub_live_1",
            "--yes",
            "--json",
        ]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["stripe_subscription_id"] == "sub_live_1"


def test_subscriptions_unlink_with_yes(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/subscriptions/sub-1/unlink").respond(
        200, json={**SAMPLE_SUB, "stripe_subscription_id": None}
    )
    result = invoke(["admin", "subscriptions", "unlink", "sub-1", "--yes"])
    assert result.exit_code == 0
    assert "Unlinked" in result.output
    assert route.called


def test_subscriptions_unlink_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions/sub-1/unlink").respond(
        200, json={**SAMPLE_SUB, "stripe_subscription_id": None}
    )
    result = invoke(["admin", "subscriptions", "unlink", "sub-1", "--yes", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["stripe_subscription_id"] is None


def test_subscriptions_unlink_aborted(invoke, mock_api):
    result = invoke(["admin", "subscriptions", "unlink", "sub-1"], input="n\n")
    assert result.exit_code == 1


def test_subscriptions_worklists(invoke, mock_api):
    mock_api.get("/api/v1/admin/subscriptions/worklists").respond(
        200,
        json={
            "awaiting_activation": [
                {
                    "organization_name": "Acme",
                    "onboarding_status": "pending",
                    "subscription_status": "trial",
                    "card_last4": "4242",
                    "reason": None,
                }
            ],
            "stuck": [
                {
                    "organization_name": "Beta",
                    "onboarding_status": "active",
                    "subscription_status": "incomplete",
                    "card_last4": "1111",
                    "reason": "activation_stuck",
                }
            ],
            "overdue": [
                {
                    "organization_name": "Gamma",
                    "onboarding_status": "active",
                    "subscription_status": "past_due",
                    "card_last4": "0809",
                    "reason": "payment_overdue",
                }
            ],
        },
    )
    result = invoke(["admin", "subscriptions", "worklists"])
    assert result.exit_code == 0
    assert "Acme" in result.output
    assert "Awaiting activation" in result.output
    assert "Payment overdue" in result.output
    assert "Gamma" in result.output
    assert "past_due" in result.output


def test_subscriptions_worklists_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/subscriptions/worklists").respond(
        200, json={"awaiting_activation": [], "stuck": []}
    )
    result = invoke(["admin", "subscriptions", "worklists", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == {"awaiting_activation": [], "stuck": []}


def test_subscriptions_pause_with_yes(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions/sub-1/pause").respond(
        200, json={**SAMPLE_SUB, "status": "paused"}
    )
    result = invoke(["admin", "subscriptions", "pause", "sub-1", "--yes"])
    assert result.exit_code == 0
    assert "Paused" in result.output


def test_subscriptions_pause_aborted(invoke, mock_api):
    result = invoke(["admin", "subscriptions", "pause", "sub-1"], input="n\n")
    assert result.exit_code == 1


def test_subscriptions_resume_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions/sub-1/resume").respond(
        200, json={**SAMPLE_SUB, "status": "active"}
    )
    result = invoke(["admin", "subscriptions", "resume", "sub-1", "--yes", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "active"


def test_subscriptions_switch_comped_with_yes(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions/sub-1/switch-comped").respond(
        200, json={**SAMPLE_SUB, "status": "active", "billing_mode": "manual"}
    )
    result = invoke(["admin", "subscriptions", "switch-comped", "sub-1", "--yes"])
    assert result.exit_code == 0
    assert "comped" in result.output


def test_subscriptions_send_reminder_with_yes(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions/sub-1/payment-reminder").respond(
        200, json={**SAMPLE_SUB, "status": "past_due", "payment_reminder_count": 2}
    )
    result = invoke(["admin", "subscriptions", "send-reminder", "sub-1", "--yes"])
    assert result.exit_code == 0
    assert "Reminder sent" in result.output
    assert "2" in result.output


def test_subscriptions_send_reminder_error_maps_exit_code(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions/sub-1/payment-reminder").respond(
        422, json={"detail": "No hosted invoice link is available to send yet."}
    )
    result = invoke(["admin", "subscriptions", "send-reminder", "sub-1", "--yes", "--json"])
    assert result.exit_code == 2


def test_subscriptions_switch_comped_aborted(invoke, mock_api):
    result = invoke(["admin", "subscriptions", "switch-comped", "sub-1"], input="n\n")
    assert result.exit_code == 1


def test_subscriptions_send_reminder_aborted(invoke, mock_api):
    result = invoke(["admin", "subscriptions", "send-reminder", "sub-1"], input="n\n")
    assert result.exit_code == 1


def test_subscriptions_resume_aborted(invoke, mock_api):
    result = invoke(["admin", "subscriptions", "resume", "sub-1"], input="n\n")
    assert result.exit_code == 1


def test_subscriptions_resume_plain_output(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions/sub-1/resume").respond(
        200, json={**SAMPLE_SUB, "status": "active"}
    )
    result = invoke(["admin", "subscriptions", "resume", "sub-1", "--yes"])
    assert result.exit_code == 0
    assert "Resumed" in result.output


def test_subscriptions_pause_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions/sub-1/pause").respond(
        200, json={**SAMPLE_SUB, "status": "paused"}
    )
    result = invoke(["admin", "subscriptions", "pause", "sub-1", "--yes", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["status"] == "paused"


def test_subscriptions_switch_comped_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions/sub-1/switch-comped").respond(
        200, json={**SAMPLE_SUB, "status": "active", "billing_mode": "manual"}
    )
    result = invoke(["admin", "subscriptions", "switch-comped", "sub-1", "--yes", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["billing_mode"] == "manual"


def test_subscriptions_send_reminder_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions/sub-1/payment-reminder").respond(
        200, json={**SAMPLE_SUB, "status": "past_due", "payment_reminder_count": 1}
    )
    result = invoke(["admin", "subscriptions", "send-reminder", "sub-1", "--yes", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["payment_reminder_count"] == 1


def test_subscriptions_pause_error_maps_exit_code(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions/sub-1/pause").respond(
        422, json={"detail": "Cannot pause a trial subscription."}
    )
    result = invoke(["admin", "subscriptions", "pause", "sub-1", "--yes", "--json"])
    assert result.exit_code == 2


def test_subscriptions_resume_error_maps_exit_code(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions/sub-1/resume").respond(
        404, json={"detail": "Subscription not found"}
    )
    result = invoke(["admin", "subscriptions", "resume", "sub-1", "--yes", "--json"])
    assert result.exit_code == 3


def test_subscriptions_switch_comped_error_maps_exit_code(invoke, mock_api):
    mock_api.post("/api/v1/admin/subscriptions/sub-1/switch-comped").respond(
        403, json={"detail": "Forbidden"}
    )
    result = invoke(["admin", "subscriptions", "switch-comped", "sub-1", "--yes", "--json"])
    assert result.exit_code == 4
