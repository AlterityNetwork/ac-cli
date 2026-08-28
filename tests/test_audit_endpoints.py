"""The staleness check of the endpoint audit.

`--strict` fails on what this function reports, so a false positive breaks
every endpoint-touching PR and a false negative is the hole the check exists
to close.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import audit_endpoints as audit  # noqa: E402


@pytest.fixture
def scope(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replaces the real entry set, so a real edit never breaks these."""
    monkeypatch.setattr(
        audit,
        "OUT_OF_SCOPE",
        {
            ("GET", "/api/v1/crm/webhook"),
            ("GET", "/api/v1/absent/thing"),
            ("GET", "/api/inngest"),
        },
    )
    monkeypatch.setattr(audit, "NOT_IN_SPEC", {"/api/inngest"})


def test_an_entry_the_api_serves_is_not_stale(scope: None) -> None:
    api = {("GET", "/api/v1/crm/webhook"), ("GET", "/api/v1/crm/companies")}

    assert audit.stale_out_of_scope(api) == set()


def test_a_path_that_moved_one_segment_down_is_stale(scope: None) -> None:
    """The case the check exists for.

    A route from `/api/v1/crm/webhook` to `/api/v1/crm/nylas/webhook` keeps
    its first three segments, so a fixed depth test would exempt it.
    """
    api = {("GET", "/api/v1/crm/nylas/webhook"), ("GET", "/api/v1/crm/companies")}

    assert audit.stale_out_of_scope(api) == {("GET", "/api/v1/crm/webhook")}


def test_a_prefix_the_api_does_not_serve_is_never_judged(scope: None) -> None:
    """This audit runs against whatever host is up.

    A branch API serves routes staging does not, so naming the wrong host
    must not fail the gate.
    """
    api = {("GET", "/api/v1/crm/webhook"), ("GET", "/api/v1/crm/companies")}

    assert ("GET", "/api/v1/absent/thing") not in audit.stale_out_of_scope(api)


def test_a_path_no_spec_declares_is_exempt(scope: None) -> None:
    """The Inngest mount is raw ASGI, so its absence says nothing."""
    api = {("GET", "/api/v1/crm/companies")}

    assert ("GET", "/api/inngest") not in audit.stale_out_of_scope(api)


def test_a_path_served_under_another_method_is_stale(scope: None) -> None:
    """An entry is a method and a path, and it suppresses that pair alone."""
    api = {("POST", "/api/v1/crm/webhook"), ("GET", "/api/v1/crm/companies")}

    assert audit.stale_out_of_scope(api) == {("GET", "/api/v1/crm/webhook")}


def test_the_real_entry_set_holds_no_unknown_exemption() -> None:
    """Every NOT_IN_SPEC path names a real OUT_OF_SCOPE entry.

    An exemption for a path nobody lists is a path no check can watch, kept
    for a reason that no longer exists.

    ⚠️ **NOT_IN_SPEC is empty, so this assertion holds for want of a member.**
    It is the invariant an entry must meet, and it starts to test again with
    the first one added. `test_a_path_no_spec_declares_is_exempt` covers the
    mechanism meanwhile, on its own entry set.
    """
    listed = {path for _, path in audit.OUT_OF_SCOPE}

    assert audit.NOT_IN_SPEC <= listed


def test_the_prospect_prefix_is_registered_for_endpoint_discovery() -> None:
    assert audit.PATH_CONSTANTS["_PROSPECTS"] == "/api/v1/agentic/prospects"


def test_the_saved_search_prefix_is_registered_for_endpoint_discovery() -> None:
    assert audit.PATH_CONSTANTS["_SAVED_SEARCHES"] == "/api/v1/agentic/saved-searches"


def test_the_audit_finds_each_prospect_command() -> None:
    calls = audit.collect_cli_calls(audit.CLI_ROOT)

    assert {
        ("GET", "/api/v1/agentic/prospects"),
        ("GET", "/api/v1/agentic/prospects/{id}"),
        ("GET", "/api/v1/agentic/prospects/{id}/people"),
        ("GET", "/api/v1/agentic/prospects/{id}/signals"),
        ("POST", "/api/v1/agentic/prospects/{id}/watch"),
        ("POST", "/api/v1/agentic/prospects/{id}/dismiss"),
    } <= calls
