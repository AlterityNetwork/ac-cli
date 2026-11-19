"""The response-key check of the endpoint audit (ENG-3053).

The payload check proves the CLI sends keys a route reads. This check proves
the CLI reads keys a route returns. A renamed response field makes
`data.get("old", "?")` print `?` with no error, so only the spec can catch it.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import audit_responses as responses  # noqa: E402

SPEC = {
    "paths": {
        "/api/v1/crm/imports/preview": {
            "post": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Preview"}}
                        }
                    }
                }
            }
        },
        "/api/v1/crm/lists": {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/List"},
                                }
                            }
                        }
                    }
                }
            }
        },
        "/api/v1/crm/page": {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Page"}}
                        }
                    }
                }
            }
        },
        "/api/v1/crm/loose": {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {"type": "object", "additionalProperties": True}
                            }
                        }
                    }
                }
            }
        },
    },
    "components": {
        "schemas": {
            "Preview": {
                "type": "object",
                "properties": {"preview_token": {"type": "string"}, "rows": {"type": "integer"}},
            },
            "List": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
            },
            "Page": {
                "type": "object",
                "properties": {
                    "data": {"type": "array", "items": {"$ref": "#/components/schemas/List"}},
                    "total": {"type": "integer"},
                },
            },
        }
    },
}


def _findings(root: Path, source: str) -> tuple[list, list]:
    commands = root / "src" / "ac_cli" / "commands"
    commands.mkdir(parents=True, exist_ok=True)
    (commands / "sample.py").write_text(textwrap.dedent(source))
    reads = responses.collect_response_reads(root)
    return responses.find_unknown_reads(reads, SPEC), reads


class TestDirectReads:
    def test_a_renamed_field_is_a_finding(self, tmp_path: Path) -> None:
        findings, _ = _findings(
            tmp_path,
            """
            def preview(path):
                resp = _api_request("post", f"{_CRM}/imports/preview", json={})
                data = resp.json()
                print(data.get("preview_id", "?"), data["rows"])
            """,
        )
        assert [(f.kind, f.keys) for f in findings] == [("RESP-KEY", ["preview_id"])]

    def test_known_fields_pass(self, tmp_path: Path) -> None:
        findings, _ = _findings(
            tmp_path,
            """
            def preview(path):
                data = _api_request("post", f"{_CRM}/imports/preview", json={}).json()
                print(data.get("preview_token"), data["rows"])
            """,
        )
        assert findings == []


class TestListsAndTables:
    def test_table_columns_are_checked_against_the_item_schema(self, tmp_path: Path) -> None:
        findings, _ = _findings(
            tmp_path,
            """
            def lists():
                resp = _api_request("get", f"{_CRM}/lists")
                data = resp.json()
                print_table(data, [("id", "ID"), ("member_type", "Type")], title="x")
            """,
        )
        assert [f.keys for f in findings] == [["member_type"]]

    def test_an_envelope_branch_and_a_loop_follow_the_path(self, tmp_path: Path) -> None:
        findings, _ = _findings(
            tmp_path,
            """
            def page():
                resp = _api_request("get", f"{_CRM}/page")
                data = resp.json()
                items = data if isinstance(data, list) else data.get("data", [])
                for item in items:
                    print(item.get("name"), item.get("colour"))
                print(data.get("total"))
            """,
        )
        assert [f.keys for f in findings] == [["colour"]]


class TestUnresolved:
    def test_a_free_form_schema_is_listed_and_never_fails(self, tmp_path: Path) -> None:
        findings, reads = _findings(
            tmp_path,
            """
            def loose():
                data = _api_request("get", f"{_CRM}/loose").json()
                print(data.get("anything"))
            """,
        )
        assert findings == []
        unresolved = responses.unresolved_reads(reads, SPEC)
        assert [(r.path, sorted(r.keys)) for r in unresolved] == [
            ("/api/v1/crm/loose", ["anything"])
        ]

    def test_an_allow_listed_read_is_not_a_finding(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(
            responses,
            "ALLOWED",
            {("POST", "/api/v1/crm/imports/preview", "preview_id"): "kept for old APIs"},
        )
        findings, _ = _findings(
            tmp_path,
            """
            def preview(path):
                data = _api_request("post", f"{_CRM}/imports/preview", json={}).json()
                print(data.get("preview_id"))
            """,
        )
        assert findings == []


def test_an_allow_list_entry_no_read_needs_is_stale(tmp_path: Path, monkeypatch) -> None:
    """A fixed read must leave the allow-list, or the list hides the next bug."""
    monkeypatch.setattr(
        responses,
        "ALLOWED",
        {
            ("POST", "/api/v1/crm/imports/preview", "preview_id"): "still read",
            ("POST", "/api/v1/crm/imports/preview", "gone"): "fixed since",
        },
    )
    _, reads = _findings(
        tmp_path,
        """
        def preview(path):
            data = _api_request("post", f"{_CRM}/imports/preview", json={}).json()
            print(data.get("preview_id"))
        """,
    )
    assert responses.stale_allowlist(reads, SPEC) == [
        ("POST", "/api/v1/crm/imports/preview", "gone")
    ]
