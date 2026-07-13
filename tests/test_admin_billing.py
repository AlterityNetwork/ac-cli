"""Tests for admin billing commands."""

import json

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
    assert '"id": "re_2"' in result.output
    import json as _json

    body = _json.loads(route.calls[0].request.content)
    assert body == {"charge_id": "ch_1", "amount_cents": 5000, "reason": "duplicate"}
