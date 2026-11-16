"""The payload check of the endpoint audit.

The path check proves that a route exists. This check proves that the CLI
sends fields the route reads. FastAPI drops an unknown body field or query
parameter with no error, so a misspelt key is a silent no-op.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import audit_payloads as payloads  # noqa: E402


def _write(root: Path, source: str) -> Path:
    commands = root / "src" / "ac_cli" / "commands"
    commands.mkdir(parents=True, exist_ok=True)
    path = commands / "sample.py"
    path.write_text(textwrap.dedent(source))
    return root


def _call(root: Path, source: str) -> payloads.CliCall:
    calls = payloads.collect_cli_payloads(_write(root, source))
    assert len(calls) == 1
    return calls[0]


class TestKeyResolution:
    def test_build_body_keywords_are_the_keys(self, tmp_path: Path) -> None:
        call = _call(
            tmp_path,
            """
            def update(draft_id, subject, body):
                update_body = _build_body(subject=subject, body=body)
                _api_request("patch", f"{_SEQUENCES}/outbox/pending/{draft_id}", json=update_body)
            """,
        )
        assert call.method == "PATCH"
        assert call.path == "/api/v1/sequences/outbox/pending/{id}"
        assert call.body_keys == {"subject", "body"}
        assert call.unresolved == []

    def test_a_dict_literal_inline(self, tmp_path: Path) -> None:
        call = _call(
            tmp_path,
            """
            def go():
                _api_request("post", f"{_CRM}/companies", json={"name": "x", "domain": "y"})
            """,
        )
        assert call.body_keys == {"name", "domain"}

    def test_subscript_and_update_add_keys(self, tmp_path: Path) -> None:
        call = _call(
            tmp_path,
            """
            def go(limit, search):
                params: dict = {"limit": limit}
                if search:
                    params["search"] = search
                params.update({"offset": 0})
                params.update(order="asc")
                params.setdefault("sort", "name")
                _api_request("get", f"{_CRM}/companies", params=params)
            """,
        )
        assert call.query_keys == {"limit", "search", "offset", "order", "sort"}
        assert call.body_keys is None

    def test_a_spread_of_a_known_dict_is_followed(self, tmp_path: Path) -> None:
        call = _call(
            tmp_path,
            """
            def go(a):
                base = {"a": a}
                _api_request("post", f"{_CRM}/companies", json={**base, "b": 1})
            """,
        )
        assert call.body_keys == {"a", "b"}
        assert call.unresolved == []

    def test_a_conditional_value_takes_both_branches(self, tmp_path: Path) -> None:
        call = _call(
            tmp_path,
            """
            def go(flag):
                _api_request("post", f"{_CRM}/companies", json={"a": 1} if flag else None)
            """,
        )
        assert call.body_keys == {"a"}

    def test_a_parameter_or_helper_value_is_unresolved(self, tmp_path: Path) -> None:
        call = _call(
            tmp_path,
            """
            def go(payload):
                _api_request("post", f"{_CRM}/companies", json=payload, params=make())
            """,
        )
        assert call.unresolved == ["json=payload", "params=make()"]

    def test_a_computed_key_is_unresolved(self, tmp_path: Path) -> None:
        call = _call(
            tmp_path,
            """
            def go(field, value):
                body = {}
                body[field] = value
                _api_request("post", f"{_CRM}/companies", json=body)
            """,
        )
        assert call.unresolved == ["json=body"]

    def test_a_loop_over_constant_pairs_gives_its_keys(self, tmp_path: Path) -> None:
        call = _call(
            tmp_path,
            """
            def go(sequence, since):
                params = {"view": "all"}
                for key, value in (("sequence", sequence), ("since", since)):
                    if value:
                        params[key] = value
                _api_request("get", f"{_INBOX}/threads", params=params)
            """,
        )
        assert call.query_keys == {"view", "sequence", "since"}
        assert call.unresolved == []

    def test_a_helper_that_returns_a_dict_is_followed(self, tmp_path: Path) -> None:
        call = _call(
            tmp_path,
            """
            def _page_params(limit, cursor):
                params = {"limit": limit}
                if cursor:
                    params["cursor"] = cursor
                return params

            def go(limit, cursor):
                _api_request("get", f"{_CRM}/companies", params=_page_params(limit, cursor))
            """,
        )
        assert call.query_keys == {"limit", "cursor"}
        assert call.unresolved == []

    def test_a_helper_in_another_module_is_followed(self, tmp_path: Path) -> None:
        commands = tmp_path / "src" / "ac_cli" / "commands"
        commands.mkdir(parents=True)
        (commands / "_shared.py").write_text(
            "def _list_params(limit):\n    return _build_body(limit=limit, offset=0)\n"
        )
        (commands / "sample.py").write_text(
            "def go(limit):\n"
            "    params = _list_params(limit)\n"
            "    _api_request('get', f'{_CRM}/companies', params=params)\n"
        )
        [call] = payloads.collect_cli_payloads(tmp_path)
        assert call.query_keys == {"limit", "offset"}

    def test_a_helper_in_the_same_module_wins(self, tmp_path: Path) -> None:
        commands = tmp_path / "src" / "ac_cli" / "commands"
        commands.mkdir(parents=True)
        (commands / "other.py").write_text("def _page(n):\n    return {'size': n}\n")
        (commands / "sample.py").write_text(
            "def _page(n):\n    return {'limit': n}\n\n"
            "def go(n):\n"
            "    _api_request('get', f'{_CRM}/companies', params=_page(n))\n"
        )
        [call] = payloads.collect_cli_payloads(tmp_path)
        assert call.query_keys == {"limit"}

    def test_raw_client_calls_are_read(self, tmp_path: Path) -> None:
        calls = payloads.collect_cli_payloads(
            _write(
                tmp_path,
                """
                def go(client):
                    client.request("DELETE", f"{_CRM}/companies", json={"ids": []})
                    client.post(f"{_CRM}/companies", params={"dry_run": True})
                """,
            )
        )
        assert [(c.method, c.body_keys, c.query_keys) for c in calls] == [
            ("DELETE", {"ids"}, None),
            ("POST", None, {"dry_run"}),
        ]

    def test_each_call_reads_its_own_function(self, tmp_path: Path) -> None:
        calls = payloads.collect_cli_payloads(
            _write(
                tmp_path,
                """
                def one():
                    body = {"a": 1}
                    _api_request("post", f"{_CRM}/one", json=body)

                def two():
                    body = {"b": 1}
                    _api_request("post", f"{_CRM}/two", json=body)
                """,
            )
        )
        assert [c.body_keys for c in calls] == [{"a"}, {"b"}]


def _spec(request_schema: dict | None = None, query: list[str] | None = None) -> dict:
    operation: dict = {
        "parameters": [
            {"name": "draft_id", "in": "path", "required": True},
            *({"name": name, "in": "query"} for name in query or []),
        ]
    }
    if request_schema is not None:
        operation["requestBody"] = {"content": {"application/json": {"schema": request_schema}}}
    return {
        "paths": {"/api/v1/sequences/outbox/pending/{draft_id}": {"patch": operation}},
        "components": {
            "schemas": {
                "UpdateDraftRequest": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "body_text": {"type": "string"},
                    },
                    "required": ["subject"],
                },
                "Loose": {"type": "object", "additionalProperties": True},
            }
        },
    }


def _cli(
    body: set[str] | None = None,
    query: set[str] | None = None,
    unresolved: list[str] | None = None,
) -> payloads.CliCall:
    return payloads.CliCall(
        method="PATCH",
        path="/api/v1/sequences/outbox/pending/{id}",
        location="commands/sequences/outbox.py:132",
        body_keys=body,
        query_keys=query,
        unresolved=unresolved or [],
    )


_REF = {"$ref": "#/components/schemas/UpdateDraftRequest"}


class TestMismatches:
    def test_an_unknown_body_key_is_reported(self) -> None:
        findings = payloads.find_mismatches([_cli(body={"subject", "body"})], _spec(_REF))
        assert [(f.kind, f.keys) for f in findings] == [("BODY-KEY", ["body"])]

    def test_an_optional_body_is_unwrapped(self) -> None:
        schema = {"anyOf": [_REF, {"type": "null"}]}
        findings = payloads.find_mismatches([_cli(body={"subject", "body"})], _spec(schema))
        assert [(f.kind, f.keys) for f in findings] == [("BODY-KEY", ["body"])]

    def test_all_of_merges_properties(self) -> None:
        schema = {"allOf": [_REF, {"properties": {"body_html": {}}}]}
        findings = payloads.find_mismatches([_cli(body={"subject", "body_html"})], _spec(schema))
        assert findings == []

    def test_a_free_form_body_is_not_judged(self) -> None:
        schema = {"$ref": "#/components/schemas/Loose"}
        assert payloads.find_mismatches([_cli(body={"anything"})], _spec(schema)) == []

    def test_a_body_the_route_does_not_take_is_reported(self) -> None:
        findings = payloads.find_mismatches([_cli(body={"subject"})], _spec(None))
        assert [(f.kind, f.keys) for f in findings] == [("BODY-UNEXPECTED", ["subject"])]

    def test_a_required_key_the_cli_never_sends_is_reported(self) -> None:
        findings = payloads.find_mismatches([_cli(body={"body_text"})], _spec(_REF))
        assert [(f.kind, f.keys) for f in findings] == [("BODY-MISSING", ["subject"])]

    def test_missing_keys_are_not_judged_when_the_body_is_partly_unknown(self) -> None:
        call = _cli(body={"body_text"}, unresolved=["json=extra"])
        assert payloads.find_mismatches([call], _spec(_REF)) == []

    def test_an_unknown_query_key_is_reported(self) -> None:
        findings = payloads.find_mismatches(
            [_cli(query={"limit", "page"})], _spec(None, query=["limit"])
        )
        assert [(f.kind, f.keys) for f in findings] == [("QUERY-KEY", ["page"])]

    def test_a_call_to_a_deprecated_route_is_reported(self) -> None:
        spec = _spec(_REF)
        spec["paths"]["/api/v1/sequences/outbox/pending/{draft_id}"]["patch"]["deprecated"] = True
        findings = payloads.find_mismatches([_cli(body={"subject"})], spec)
        assert [f.kind for f in findings] == ["DEPRECATED"]

    def test_a_path_the_spec_lacks_is_left_to_the_path_check(self) -> None:
        call = payloads.CliCall(
            method="GET",
            path="/api/v1/absent",
            location="x.py:1",
            body_keys=None,
            query_keys={"a"},
            unresolved=[],
        )
        assert payloads.find_mismatches([call], _spec(None)) == []


@pytest.mark.parametrize(
    "kind", ["BODY-KEY", "BODY-UNEXPECTED", "BODY-MISSING", "QUERY-KEY", "DEPRECATED"]
)
def test_every_finding_kind_fails_strict(kind: str) -> None:
    assert kind in payloads.STRICT_KINDS
