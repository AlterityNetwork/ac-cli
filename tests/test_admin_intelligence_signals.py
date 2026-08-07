"""Tests for the admin intelligence signals + sources commands."""

import json

SAMPLE_SIGNAL = {
    "id": "sig-1",
    "subject_type": "company",
    "subject_id": "co-1",
    "signal_type": "funding_round",
    "description": "Acme raises $40M Series B",
    "subject_name": "Acme",
    "observed_at": "2026-06-01T09:00:00Z",
}

SAMPLE_SOURCE = {
    "id": "src-1",
    "provider": "exa",
    "kind": "signal",
    "ref": "techcrunch.com/acme",
    "cost_usd": 0.004,
    "fetched_at": "2026-06-01T10:00:00Z",
}

_LIST = {"total": 1, "limit": 50, "offset": 0, "has_more": False}


# --- signals ---------------------------------------------------------------


def test_signals_list(invoke, mock_api):
    mock_api.get("/api/v1/admin/intelligence/signals").respond(
        200, json={"data": [SAMPLE_SIGNAL], **_LIST}
    )
    result = invoke(["admin", "intelligence", "signals", "list"])
    assert result.exit_code == 0
    assert "funding_round" in result.output


def test_signals_list_filter_params(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/intelligence/signals").respond(
        200, json={"data": [], **_LIST, "total": 0}
    )
    result = invoke(
        [
            "admin",
            "intelligence",
            "signals",
            "list",
            "--subject-type",
            "person",
            "--signal-type",
            "job_change",
            "--json",
        ]
    )
    assert result.exit_code == 0
    url = str(route.calls.last.request.url)
    assert "subject_type=person" in url
    assert "signal_type=job_change" in url


def test_signals_get_shows_every_citing_source(invoke, mock_api):
    mock_api.get("/api/v1/admin/intelligence/signals/sig-1").respond(
        200,
        json={
            "signal": SAMPLE_SIGNAL,
            "sources": [
                {**SAMPLE_SOURCE, "is_primary": True},
                {**SAMPLE_SOURCE, "id": "src-2", "provider": "parallel", "is_primary": False},
            ],
            "subject": {"id": "co-1", "name": "Acme"},
            "related_company": None,
        },
    )
    result = invoke(["admin", "intelligence", "signals", "get", "sig-1"])
    assert result.exit_code == 0
    assert "exa" in result.output
    assert "parallel" in result.output


def test_signals_create_sends_the_identity_columns(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/intelligence/signals").respond(200, json=SAMPLE_SIGNAL)
    result = invoke(
        [
            "admin",
            "intelligence",
            "signals",
            "create",
            "--subject-type",
            "company",
            "--subject-id",
            "co-1",
            "--signal-type",
            "funding_round",
            "--observed-at",
            "2026-06-01T09:00:00Z",
            "--description",
            "Acme raises $40M Series B",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "subject_type": "company",
        "subject_id": "co-1",
        "signal_type": "funding_round",
        "observed_at": "2026-06-01T09:00:00Z",
        "description": "Acme raises $40M Series B",
    }


def test_signals_create_never_sends_a_dedup_key(invoke, mock_api):
    """dedup_key is server-derived; the CLI must not offer a way to forge one."""
    route = mock_api.post("/api/v1/admin/intelligence/signals").respond(200, json=SAMPLE_SIGNAL)
    invoke(
        [
            "admin",
            "intelligence",
            "signals",
            "create",
            "--subject-type",
            "company",
            "--subject-id",
            "co-1",
            "--signal-type",
            "funding_round",
            "--observed-at",
            "2026-06-01T09:00:00Z",
        ]
    )
    assert "dedup_key" not in json.loads(route.calls.last.request.content)


def test_signals_has_no_update_command(invoke):
    """Mirrors the missing PATCH — an extra CLI verb would fail the parity audit."""
    result = invoke(["admin", "intelligence", "signals", "update", "sig-1"])
    assert result.exit_code != 0


def test_signals_delete_requires_confirmation(invoke, mock_api):
    mock_api.delete("/api/v1/admin/intelligence/signals/sig-1").respond(200, json={"ok": True})
    result = invoke(["admin", "intelligence", "signals", "delete", "sig-1", "--yes"])
    assert result.exit_code == 0


def test_signals_bulk_delete(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/intelligence/signals/bulk-delete").respond(
        200, json={"deleted": 2, "requested": 2}
    )
    result = invoke(
        [
            "admin",
            "intelligence",
            "signals",
            "bulk-delete",
            "--id",
            "sig-1",
            "--id",
            "sig-2",
            "--yes",
        ]
    )
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {"ids": ["sig-1", "sig-2"]}


def test_signals_link_source(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/intelligence/signals/sig-1/sources").respond(
        200, json={"ok": True}
    )
    result = invoke(
        [
            "admin",
            "intelligence",
            "signals",
            "link-source",
            "sig-1",
            "--source-id",
            "src-2",
            "--primary",
        ]
    )
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {
        "source_id": "src-2",
        "is_primary": True,
    }


def test_signals_unlink_source(invoke, mock_api):
    mock_api.delete("/api/v1/admin/intelligence/signals/sig-1/sources/src-2").respond(
        200, json={"ok": True}
    )
    result = invoke(
        ["admin", "intelligence", "signals", "unlink-source", "sig-1", "--source-id", "src-2"]
    )
    assert result.exit_code == 0


def test_signals_list_not_found_exit_code(invoke, mock_api):
    mock_api.get("/api/v1/admin/intelligence/signals/nope").respond(404, json={"detail": "gone"})
    result = invoke(["admin", "intelligence", "signals", "get", "nope"])
    assert result.exit_code == 3


# --- sources ---------------------------------------------------------------


def test_sources_list(invoke, mock_api):
    mock_api.get("/api/v1/admin/intelligence/sources").respond(
        200, json={"data": [SAMPLE_SOURCE], **_LIST}
    )
    result = invoke(["admin", "intelligence", "sources", "list"])
    assert result.exit_code == 0
    assert "exa" in result.output


def test_sources_list_filter_params(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/intelligence/sources").respond(
        200, json={"data": [], **_LIST, "total": 0}
    )
    result = invoke(
        [
            "admin",
            "intelligence",
            "sources",
            "list",
            "--provider",
            "exa",
            "--kind",
            "signal",
            "--json",
        ]
    )
    assert result.exit_code == 0
    url = str(route.calls.last.request.url)
    assert "provider=exa" in url
    assert "kind=signal" in url


def test_sources_get_json_includes_the_payload(invoke, mock_api):
    mock_api.get("/api/v1/admin/intelligence/sources/src-1").respond(
        200, json={**SAMPLE_SOURCE, "payload": {"raw": "provider json"}}
    )
    result = invoke(["admin", "intelligence", "sources", "get", "src-1", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["payload"] == {"raw": "provider json"}


def test_sources_create(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/intelligence/sources").respond(200, json=SAMPLE_SOURCE)
    result = invoke(
        [
            "admin",
            "intelligence",
            "sources",
            "create",
            "--provider",
            "manual",
            "--kind",
            "signal",
            "--ref",
            "hand-entered",
        ]
    )
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {
        "provider": "manual",
        "kind": "signal",
        "ref": "hand-entered",
    }


def test_sources_update(invoke, mock_api):
    route = mock_api.patch("/api/v1/admin/intelligence/sources/src-1").respond(
        200, json=SAMPLE_SOURCE
    )
    result = invoke(["admin", "intelligence", "sources", "update", "src-1", "--cost-usd", "0.09"])
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {"cost_usd": 0.09}


def test_sources_update_with_no_fields_errors(invoke):
    result = invoke(["admin", "intelligence", "sources", "update", "src-1"])
    assert result.exit_code == 1


def test_sources_delete(invoke, mock_api):
    mock_api.delete("/api/v1/admin/intelligence/sources/src-1").respond(200, json={"ok": True})
    result = invoke(["admin", "intelligence", "sources", "delete", "src-1", "--yes"])
    assert result.exit_code == 0


def test_sources_bulk_delete(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/intelligence/sources/bulk-delete").respond(
        200, json={"deleted": 1, "requested": 1}
    )
    result = invoke(["admin", "intelligence", "sources", "bulk-delete", "--id", "src-1", "--yes"])
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {"ids": ["src-1"]}
