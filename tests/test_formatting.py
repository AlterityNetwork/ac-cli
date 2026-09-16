"""Tests for formatting helpers."""

import json

from ac_cli.formatting import print_detail, print_json, print_table


def test_print_table_renders_rows(capsys):
    data = [
        {"name": "Acme", "industry": "SaaS"},
        {"name": "Globex", "industry": "Manufacturing"},
    ]
    print_table(data, [("name", "Name"), ("industry", "Industry")], title="Companies")
    output = capsys.readouterr().out
    assert "Acme" in output
    assert "Globex" in output
    assert "Companies" in output


def test_print_table_empty(capsys):
    print_table([], [("name", "Name")], title="Empty")
    output = capsys.readouterr().out
    assert "Empty" in output


def test_print_detail_renders_fields(capsys):
    data = {"id": "abc", "name": "Acme", "website": "https://acme.com"}
    print_detail(data, [("id", "ID"), ("name", "Name"), ("website", "Website")])
    output = capsys.readouterr().out
    assert "abc" in output
    assert "Acme" in output
    assert "https://acme.com" in output


def test_print_json_outputs_valid_json(capsys):
    data = {"items": [1, 2, 3], "total": 3}
    print_json(data)
    output = capsys.readouterr().out
    parsed = json.loads(output)
    assert parsed == data


def test_print_detail_renders_a_zero_value(capsys):
    """A zero or False field prints its value, not an empty string."""
    data = {"chunk_count": 0, "active": False}
    print_detail(data, [("chunk_count", "Chunk Count"), ("active", "Active")])
    output = capsys.readouterr().out
    assert "Chunk Count: 0" in output
    assert "Active: False" in output


def test_print_detail_renders_a_null_value_as_empty(capsys):
    """A null field prints the label with no value."""
    data = {"description": None}
    print_detail(data, [("description", "Description")])
    output = capsys.readouterr().out
    assert "Description:" in output
    assert "None" not in output


def test_print_detail_missing_key(capsys):
    data = {"name": "Acme"}
    print_detail(data, [("name", "Name"), ("missing", "Missing Field")])
    output = capsys.readouterr().out
    assert "Acme" in output
    assert "Missing Field" in output
