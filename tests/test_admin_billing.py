"""Tests for admin billing commands."""

import json

import httpx

SAMPLE_STRIPE_SUBS = {
    "data": [
        {
            "id": "sub_live_1",
            "customer_id": "cus_1",
            "status": "active",
            "product_id": "prod_1",
            "amount": 5000,
            "currency": "gbp",
            "linked_local_subscription_id": "loc-1",
            "is_orphan": False,
        },
        {
            "id": "sub_live_2",
            "customer_id": "cus_2",
            "status": "canceled",
            "product_id": "prod_1",
            "amount": 5000,
            "currency": "gbp",
            "linked_local_subscription_id": None,
            "is_orphan": True,
        },
    ],
    "broken_links": [
        {
            "local_subscription_id": "loc-9",
            "organization_id": "org-9",
            "stripe_subscription_id": "sub_gone",
        }
    ],
    "total": 2,
}


def test_stripe_subscriptions_list(invoke, mock_api):
    mock_api.get("/api/v1/admin/billing/stripe-subscriptions").respond(200, json=SAMPLE_STRIPE_SUBS)
    result = invoke(["admin", "billing", "stripe-subscriptions"])
    assert result.exit_code == 0
    assert "sub_live_1" in result.output
    # The broken-links table is surfaced too.
    assert "sub_gone" in result.output


def test_stripe_subscriptions_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/billing/stripe-subscriptions").respond(200, json=SAMPLE_STRIPE_SUBS)
    result = invoke(["admin", "billing", "stripe-subscriptions", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total"] == 2
    assert len(data["broken_links"]) == 1


def test_stripe_subscriptions_forwards_pagination(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/billing/stripe-subscriptions").respond(
        200, json=SAMPLE_STRIPE_SUBS
    )
    result = invoke(["admin", "billing", "stripe-subscriptions", "--limit", "10", "--offset", "20"])
    assert result.exit_code == 0
    url = str(route.calls.last.request.url)
    assert "limit=10" in url
    assert "offset=20" in url


SAMPLE_IMPORT = {
    "imported": 2,
    "updated": 1,
    "skipped": 0,
    "messages": ["Team: no annual price, set to 0"],
}


def test_import_stripe_products(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/billing/import-stripe-products").respond(
        200, json=SAMPLE_IMPORT
    )
    result = invoke(["admin", "billing", "import-stripe-products", "--yes"])
    assert result.exit_code == 0
    assert route.called
    # Counts + the per-product note are surfaced.
    assert "2" in result.output
    assert "no annual price" in result.output


def test_import_stripe_products_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/billing/import-stripe-products").respond(200, json=SAMPLE_IMPORT)
    result = invoke(["admin", "billing", "import-stripe-products", "--yes", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["imported"] == 2
    assert data["updated"] == 1


def test_import_stripe_products_aborts_without_confirmation(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/billing/import-stripe-products").respond(
        200, json=SAMPLE_IMPORT
    )
    result = invoke(["admin", "billing", "import-stripe-products"], input="n\n")
    assert result.exit_code == 1
    assert not route.called


def test_import_stripe_products_error_exit_code(invoke, mock_api):
    # 403 maps to the semantic auth exit code (4).
    mock_api.post("/api/v1/admin/billing/import-stripe-products").respond(403)
    result = invoke(["admin", "billing", "import-stripe-products", "--yes"])
    assert result.exit_code == 4


def test_import_stripe_products_error_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/billing/import-stripe-products").respond(
        403, json={"detail": "Forbidden"}
    )
    result = invoke(["admin", "billing", "import-stripe-products", "--yes", "--json"])
    assert result.exit_code == 4
    data = json.loads(result.output)
    assert data["error"] is True
    assert data["status_code"] == 403


def test_billing_refund_full(invoke, mock_api):
    mock_api.post("/api/v1/admin/billing/refunds").respond(
        200,
        json={
            "id": "re_1",
            "status": "succeeded",
            "amount": 30000,
            "currency": "gbp",
            "charge": "ch_1",
        },
    )
    result = invoke(["admin", "billing", "refund", "ch_1", "--yes"])
    assert result.exit_code == 0
    assert "re_1" in result.output


def test_billing_refund_partial_json(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/billing/refunds").respond(
        200,
        json={"id": "re_2", "status": "succeeded", "amount": 5000, "currency": "gbp"},
    )
    result = invoke(
        [
            "admin",
            "billing",
            "refund",
            "ch_1",
            "--amount-cents",
            "5000",
            "--reason",
            "duplicate",
            "--yes",
            "--json",
        ]
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["id"] == "re_2"

    body = json.loads(route.calls[0].request.content)
    assert body == {"charge_id": "ch_1", "amount_cents": 5000, "reason": "duplicate"}


def test_billing_refund_aborted(invoke, mock_api):
    result = invoke(["admin", "billing", "refund", "ch_1"], input="n\n")
    assert result.exit_code == 1


def test_billing_refund_validation_error_maps_exit_code(invoke, mock_api):
    mock_api.post("/api/v1/admin/billing/refunds").respond(
        422, json={"detail": "Refund amount exceeds the charge."}
    )
    result = invoke(["admin", "billing", "refund", "ch_1", "--yes", "--json"])
    assert result.exit_code == 2


def test_billing_refund_forbidden_maps_exit_code(invoke, mock_api):
    mock_api.post("/api/v1/admin/billing/refunds").respond(403, json={"detail": "Forbidden"})
    result = invoke(["admin", "billing", "refund", "ch_1", "--yes", "--json"])
    assert result.exit_code == 4


TOP_UP = {
    "invoice_id": "in_1",
    "status": "paid",
    "credits": 2500,
    "amount_pence": 2500,
    "total_pence": 3000,
    "currency": "gbp",
}
ORG = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"


def test_billing_top_up(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/billing/top-ups").respond(200, json=TOP_UP)
    result = invoke(["admin", "billing", "top-up", "--org-id", ORG, "--credits", "2500", "--yes"])
    assert result.exit_code == 0
    assert "in_1" in result.output
    assert "paid" in result.output
    body = json.loads(route.calls[0].request.content)
    assert body["organization_id"] == ORG
    assert body["credits"] == 2500
    assert len(body["request_id"]) == 36


def test_billing_top_up_keeps_a_given_request_id(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/billing/top-ups").respond(200, json=TOP_UP)
    request_id = "dddddddd-dddd-4ddd-dddd-dddddddddddd"
    result = invoke(
        [
            "admin",
            "billing",
            "top-up",
            "--org-id",
            ORG,
            "--credits",
            "2500",
            "--request-id",
            request_id,
            "--yes",
            "--json",
        ]
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout)["invoice_id"] == "in_1"
    assert json.loads(route.calls[0].request.content)["request_id"] == request_id


def test_billing_top_up_confirms_the_price(invoke, mock_api):
    result = invoke(
        ["admin", "billing", "top-up", "--org-id", ORG, "--credits", "2500"],
        input="n\n",
    )
    assert result.exit_code == 1
    assert "£25.00" in result.output


def test_billing_top_up_decline_maps_exit_code(invoke, mock_api):
    mock_api.post("/api/v1/admin/billing/top-ups").respond(
        402,
        json={
            "message": "The card on file was declined: Your card was declined.",
            "code": "top_up_payment_failed",
            "context": {"code": "top_up_payment_failed"},
        },
    )
    result = invoke(
        [
            "admin",
            "billing",
            "top-up",
            "--org-id",
            ORG,
            "--credits",
            "500",
            "--yes",
            "--json",
        ]
    )
    assert result.exit_code == 6
    assert json.loads(result.stdout)["context"]["code"] == "top_up_payment_failed"


USAGE = {
    "organizations": [
        {
            "organization_id": ORG,
            "organization_name": "Acme",
            "allowance": 10000,
            "top_ups": 0,
            "adjustments": 0,
            "spent": 8500,
            "balance": 1500,
            "used_percent": 85,
            "state": "warning",
            "enforced": True,
            "card_brand": "visa",
            "card_last4": "4242",
            "can_top_up": True,
        }
    ]
}


def test_billing_credit_usage(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/billing/credit-usage").respond(200, json=USAGE)
    result = invoke(["admin", "billing", "credit-usage"])
    assert result.exit_code == 0
    assert "Acme" in result.output
    assert "85%" in result.output
    assert route.calls[0].request.url.params["attention"] == "false"


def test_billing_credit_usage_attention_json(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/billing/credit-usage").respond(200, json=USAGE)
    result = invoke(["admin", "billing", "credit-usage", "--attention", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["organizations"][0]["state"] == "warning"
    assert route.calls[0].request.url.params["attention"] == "true"


def test_billing_top_up_prints_the_request_id_before_the_call(invoke, mock_api):
    mock_api.post("/api/v1/admin/billing/top-ups").mock(
        side_effect=httpx.ConnectError("network down")
    )
    request_id = "eeeeeeee-eeee-4eee-eeee-eeeeeeeeeeee"
    result = invoke(
        [
            "admin",
            "billing",
            "top-up",
            "--org-id",
            ORG,
            "--credits",
            "500",
            "--request-id",
            request_id,
            "--yes",
        ]
    )
    assert result.exit_code == 1
    assert f"--request-id {request_id}" in result.output


def test_billing_credit_usage_notes_unread_balances(invoke, mock_api):
    mock_api.get("/api/v1/admin/billing/credit-usage").respond(
        200, json={**USAGE, "unread_count": 2}
    )
    result = invoke(["admin", "billing", "credit-usage"])
    assert result.exit_code == 0
    assert "2 organization(s) did not load" in result.output
